import { strFromU8, unzipSync } from "fflate";
import { describe, expect, it } from "vitest";
import type { RowsPayload } from "./types";
import { exportFileName, toCsv, toXlsx } from "./export";

const rows: RowsPayload = {
  columns: [
    { name: "vendor", type: "text" },
    { name: "spend_inr", type: "number" },
    { name: "active", type: "boolean" },
    { name: "order_date", type: "date" },
  ],
  rows: [
    ["Zenith, Steels", "12650.50", true, "2026-11-02"],
    ['Anand "AE" Eng', 300, false, null],
    ["=HYPERLINK(\"x\")", -5, null, "2026-11-03"],
  ],
  row_count: 3,
  truncated: false,
};

describe("toCsv", () => {
  it("writes a header, quotes commas and quotes, and leaves nulls empty", () => {
    const lines = toCsv(rows).replace(/^﻿/, "").split("\r\n");
    expect(lines[0]).toBe("vendor,spend_inr,active,order_date");
    expect(lines[1]).toBe('"Zenith, Steels",12650.50,true,2026-11-02');
    expect(lines[2]).toBe('"Anand ""AE"" Eng",300,false,');
  });

  it("starts with a byte order mark so Excel reads ₹ and other UTF-8 text", () => {
    expect(toCsv(rows).startsWith("﻿")).toBe(true);
  });

  it("defuses text that a spreadsheet would run as a formula, but keeps negative numbers", () => {
    const lines = toCsv(rows).split("\r\n");
    expect(lines[3]).toBe(`"'=HYPERLINK(""x"")",-5,,2026-11-03`);
  });
});

describe("toXlsx", () => {
  const files = unzipSync(toXlsx(rows, "Spend"));
  const sheet = strFromU8(files["xl/worksheets/sheet1.xml"]);

  it("builds a workbook with the parts Excel needs", () => {
    expect(Object.keys(files).sort()).toEqual([
      "[Content_Types].xml",
      "_rels/.rels",
      "xl/_rels/workbook.xml.rels",
      "xl/styles.xml",
      "xl/workbook.xml",
      "xl/worksheets/sheet1.xml",
    ]);
    expect(strFromU8(files["xl/workbook.xml"])).toContain('<sheet name="Spend" sheetId="1" r:id="rId1"/>');
  });

  it("writes a bold, frozen header row", () => {
    expect(sheet).toContain('state="frozen"');
    expect(sheet).toContain('<c r="A1" t="inlineStr" s="1"><is><t xml:space="preserve">vendor</t></is></c>');
  });

  it("stores numbers (including exact decimal strings) as numbers and booleans as booleans", () => {
    expect(sheet).toContain('<c r="B2"><v>12650.50</v></c>');
    expect(sheet).toContain('<c r="B4"><v>-5</v></c>');
    expect(sheet).toContain('<c r="C2" t="b"><v>1</v></c>');
  });

  it("escapes XML and skips empty cells", () => {
    expect(sheet).toContain("Anand &quot;AE&quot; Eng");
    expect(sheet).not.toContain('r="D3"');
  });

  it("keeps formula-like text as plain text", () => {
    expect(sheet).toContain('<c r="A4" t="inlineStr"><is><t xml:space="preserve">=HYPERLINK(&quot;x&quot;)</t></is></c>');
    expect(sheet).not.toContain("<f>");
  });

  it("cleans sheet names Excel would reject", () => {
    const named = unzipSync(toXlsx(rows, "Spend / vendor: [Q3]?* and a very long tail"));
    const name = strFromU8(named["xl/workbook.xml"]).match(/sheet name="([^"]*)"/)![1];
    expect(name).toBe("Spend vendor Q3 and a very long");
    expect(name.length).toBeLessThanOrEqual(31);
  });
});

describe("exportFileName", () => {
  it("slugs the title and stamps the date and time", () => {
    const at = new Date(2026, 10, 19, 9, 5);
    expect(exportFileName("Spend by vendor (this year)", "csv", at)).toBe(
      "spend-by-vendor-this-year-20261119-0905.csv",
    );
  });

  it("falls back to a default name", () => {
    expect(exportFileName(null, "xlsx", new Date(2026, 0, 2, 3, 4))).toBe("results-20260102-0304.xlsx");
  });
});
