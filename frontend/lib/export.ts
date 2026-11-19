/**
 * Turns a result table into a CSV or Excel file in the browser. The rows are the ones the user
 * already sees (masked and scoped to their role), so exporting reveals nothing new.
 */
import { strToU8, zipSync } from "fflate";
import type { RowsPayload } from "./types";

type Cell = RowsPayload["rows"][number][number];

export const XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
export const CSV_MIME = "text/csv;charset=utf-8";

// ------------------------------------------------------------------ CSV

/** Text a spreadsheet would run as a formula (OWASP "CSV injection"). */
const FORMULA_START = /^[=+\-@\t\r]/;

function csvCell(value: Cell): string {
  if (value === null || value === undefined) return "";
  if (typeof value !== "string") return String(value);
  const text = FORMULA_START.test(value) && !isNumeric(value) ? `'${value}` : value;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/** RFC 4180 CSV with a byte order mark, so Excel opens UTF-8 text (₹, accents) correctly. */
export function toCsv({ columns, rows }: RowsPayload): string {
  const lines = [columns.map((c) => csvCell(c.name)), ...rows.map((row) => row.map(csvCell))];
  return "﻿" + lines.map((cells) => cells.join(",")).join("\r\n");
}

// ------------------------------------------------------------------ XLSX

const NUMERIC = /^-?\d+(\.\d+)?$/;
const isNumeric = (value: string) => NUMERIC.test(value.trim());

// Characters XML 1.0 does not allow, even escaped.
const XML_INVALID = /[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g;

function xml(text: string): string {
  return text
    .replace(XML_INVALID, "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function columnLetter(index: number): string {
  let letters = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    letters = String.fromCharCode(65 + ((n - 1) % 26)) + letters;
  }
  return letters;
}

const textCell = (ref: string, text: string, style = "") =>
  `<c r="${ref}" t="inlineStr"${style}><is><t xml:space="preserve">${xml(text)}</t></is></c>`;

function xlsxCell(ref: string, value: Cell, numericColumn: boolean): string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "boolean") return `<c r="${ref}" t="b"><v>${value ? 1 : 0}</v></c>`;
  if (typeof value === "number") {
    return Number.isFinite(value) ? `<c r="${ref}"><v>${value}</v></c>` : "";
  }
  // Money arrives as exact decimal strings; keep them as numbers so sums work in Excel.
  if (numericColumn && isNumeric(value)) return `<c r="${ref}"><v>${value.trim()}</v></c>`;
  return textCell(ref, value);
}

/** Excel sheet names: at most 31 characters, none of : \ / ? * [ ]. */
function sheetName(title: string): string {
  const cleaned = title.replace(/[:\\/?*[\]]/g, " ").replace(/\s+/g, " ").trim().slice(0, 31).trim();
  return cleaned || "Results";
}

function columnWidths({ columns, rows }: RowsPayload): string {
  const widths = columns.map((column, i) => {
    const longest = rows.reduce(
      (max, row) => Math.max(max, row[i] === null ? 0 : String(row[i]).length),
      column.name.length,
    );
    return Math.min(Math.max(longest + 2, 8), 60);
  });
  return widths
    .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
    .join("");
}

const NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"';
const REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
const PKG_REL = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"';
const HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

const CONTENT_TYPES =
  `${HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
  '<Default Extension="xml" ContentType="application/xml"/>' +
  '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
  '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
  '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
  "</Types>";

const ROOT_RELS =
  `${HEAD}<Relationships ${PKG_REL}>` +
  `<Relationship Id="rId1" Type="${REL}/officeDocument" Target="xl/workbook.xml"/>` +
  "</Relationships>";

const WORKBOOK_RELS =
  `${HEAD}<Relationships ${PKG_REL}>` +
  `<Relationship Id="rId1" Type="${REL}/worksheet" Target="worksheets/sheet1.xml"/>` +
  `<Relationship Id="rId2" Type="${REL}/styles" Target="styles.xml"/>` +
  "</Relationships>";

// Style 0 is normal text, style 1 is the bold header.
const STYLES =
  `${HEAD}<styleSheet ${NS}>` +
  '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>' +
  '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>' +
  '<fills count="2"><fill><patternFill patternType="none"/></fill>' +
  '<fill><patternFill patternType="gray125"/></fill></fills>' +
  '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>' +
  '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
  '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
  '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>' +
  '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
  "</styleSheet>";

/** A minimal, valid .xlsx workbook: one sheet, bold frozen header, typed cells. */
export function toXlsx(payload: RowsPayload, title = "Results"): Uint8Array<ArrayBuffer> {
  const { columns, rows } = payload;
  const numeric = columns.map((c) => c.type === "number");
  const header = columns.map((c, i) => textCell(`${columnLetter(i)}1`, c.name, ' s="1"')).join("");
  const body = rows
    .map((row, r) => {
      const cells = row.map((v, i) => xlsxCell(`${columnLetter(i)}${r + 2}`, v, numeric[i]));
      return `<row r="${r + 2}">${cells.join("")}</row>`;
    })
    .join("");

  const sheet =
    `${HEAD}<worksheet ${NS}>` +
    '<sheetViews><sheetView workbookViewId="0">' +
    '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>' +
    "</sheetView></sheetViews>" +
    `<cols>${columnWidths(payload)}</cols>` +
    `<sheetData><row r="1">${header}</row>${body}</sheetData>` +
    "</worksheet>";

  const workbook =
    `${HEAD}<workbook ${NS} xmlns:r="${REL}">` +
    `<sheets><sheet name="${xml(sheetName(title))}" sheetId="1" r:id="rId1"/></sheets>` +
    "</workbook>";

  // Copied into a plain ArrayBuffer so it can go straight into a Blob.
  return new Uint8Array(zipSync({
    "[Content_Types].xml": strToU8(CONTENT_TYPES),
    "_rels/.rels": strToU8(ROOT_RELS),
    "xl/workbook.xml": strToU8(workbook),
    "xl/_rels/workbook.xml.rels": strToU8(WORKBOOK_RELS),
    "xl/styles.xml": strToU8(STYLES),
    "xl/worksheets/sheet1.xml": strToU8(sheet),
  }));
}

// ------------------------------------------------------------------ download

const pad = (n: number) => String(n).padStart(2, "0");

/** "Spend by vendor" -> "spend-by-vendor-20261119-0905.csv". */
export function exportFileName(title: string | null | undefined, ext: string, at = new Date()): string {
  const slug =
    (title ?? "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60)
      .replace(/-+$/, "") || "results";
  const stamp =
    `${at.getFullYear()}${pad(at.getMonth() + 1)}${pad(at.getDate())}` +
    `-${pad(at.getHours())}${pad(at.getMinutes())}`;
  return `${slug}-${stamp}.${ext}`;
}

export function downloadFile(content: BlobPart, type: string, fileName: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noopener";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
