import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DataTable } from "./DataTable";

const columns = [
  { name: "vendor", type: "text" },
  { name: "spend_inr", type: "numeric" },
  { name: "active", type: "bool" },
];

describe("DataTable", () => {
  it("FE-12 renders the column headers and rows", () => {
    render(
      <DataTable
        rows={{
          columns,
          rows: [
            ["Zenith Steels", 12650.5, true],
            ["Anand Engineering", null, false],
          ],
          row_count: 2,
          truncated: false,
        }}
      />,
    );
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "vendor",
      "spend_inr",
      "active",
    ]);
    const cells = within(table).getAllByRole("row")[1].querySelectorAll("td");
    expect(Array.from(cells).map((c) => c.textContent)).toEqual(["Zenith Steels", "12,650.5", "Yes"]);
    expect(within(table).getAllByRole("row")[2].textContent).toContain("—");
    expect(screen.getByText("2 rows")).toBeInTheDocument();
    expect(screen.queryByText(/cut at/i)).not.toBeInTheDocument();
  });

  it("FE-12 flags truncated results", () => {
    render(
      <DataTable
        rows={{ columns: [columns[0]], rows: [["a"]], row_count: 500, truncated: true }}
      />,
    );
    expect(screen.getByText(/the result was cut at 500 rows/i)).toBeInTheDocument();
  });

  it("says so when no rows came back", () => {
    render(<DataTable rows={{ columns, rows: [], row_count: 0, truncated: false }} />);
    expect(screen.getByText(/no rows returned/i)).toBeInTheDocument();
  });

  it("uses singular wording for one row", () => {
    render(<DataTable rows={{ columns: [columns[0]], rows: [["a"]], row_count: 1, truncated: false }} />);
    expect(screen.getByText("1 row")).toBeInTheDocument();
  });
});

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blob);
  });
}

describe("DataTable export", () => {
  const payload = {
    columns: [
      { name: "vendor", type: "text" },
      { name: "spend_inr", type: "number" },
    ],
    rows: [["Zenith", 12650]],
    row_count: 1,
    truncated: false,
  };

  function captureDownloads() {
    const saved: { name: string; blob: Blob }[] = [];
    const created: Blob[] = [];
    URL.createObjectURL = vi.fn((blob: Blob) => {
      created.push(blob);
      return `blob:${created.length}`;
    });
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      saved.push({ name: this.download, blob: created[Number(this.href.split(":").at(-1)) - 1] });
    });
    return saved;
  }

  it("offers Excel and CSV from an Export menu", async () => {
    const user = userEvent.setup();
    render(<DataTable rows={payload} exportName="Spend by vendor" />);

    const trigger = screen.getByRole("button", { name: /export/i });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);

    const menu = screen.getByRole("menu");
    expect(within(menu).getAllByRole("menuitem").map((i) => i.textContent)).toEqual([
      expect.stringMatching(/excel/i),
      expect.stringMatching(/csv/i),
    ]);
  });

  it("downloads a CSV file named after the question", async () => {
    const saved = captureDownloads();
    const user = userEvent.setup();
    render(<DataTable rows={payload} exportName="Spend by vendor" />);

    await user.click(screen.getByRole("button", { name: /export/i }));
    await user.click(screen.getByRole("menuitem", { name: /csv/i }));

    expect(saved).toHaveLength(1);
    expect(saved[0].name).toMatch(/^spend-by-vendor-\d{8}-\d{4}\.csv$/);
    expect(await readBlob(saved[0].blob)).toContain("vendor,spend_inr\r\nZenith,12650");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("downloads an Excel workbook", async () => {
    const saved = captureDownloads();
    const user = userEvent.setup();
    render(<DataTable rows={payload} />);

    await user.click(screen.getByRole("button", { name: /export/i }));
    await user.click(screen.getByRole("menuitem", { name: /excel/i }));

    expect(saved[0].name).toMatch(/^results-\d{8}-\d{4}\.xlsx$/);
    expect(saved[0].blob.type).toBe(
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    );
  });

  it("closes the menu with Escape or a click outside", async () => {
    const user = userEvent.setup();
    render(<DataTable rows={payload} />);
    const trigger = screen.getByRole("button", { name: /export/i });

    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    await user.click(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("has nothing to export when no rows came back", () => {
    render(<DataTable rows={{ ...payload, rows: [], row_count: 0 }} />);
    expect(screen.queryByRole("button", { name: /export/i })).not.toBeInTheDocument();
  });
});
