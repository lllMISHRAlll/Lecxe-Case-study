import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
