import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SqlPanel } from "./SqlPanel";

describe("SqlPanel", () => {
  it("FE-11 shows the SQL with keywords highlighted", () => {
    const { container } = render(
      <SqlPanel sql={{ sql: "SELECT name FROM proc_vendors LIMIT 5", source: "generated", attempt: 1 }} />,
    );
    expect(screen.getByRole("heading", { name: /sql/i })).toBeInTheDocument();
    expect(container.querySelector("code")?.textContent).toBe(
      "SELECT name FROM proc_vendors LIMIT 5",
    );
    const keywords = Array.from(container.querySelectorAll(".sql-keyword")).map((k) => k.textContent);
    expect(keywords).toEqual(["SELECT", "FROM", "LIMIT"]);
  });

  it.each([
    ["button", 1, "Saved query"],
    ["generated", 1, "Written by the assistant"],
    ["fixed", 2, "Fixed by the assistant, attempt 2"],
  ] as const)("labels where %s SQL came from", (source, attempt, label) => {
    render(<SqlPanel sql={{ sql: "SELECT 1", source, attempt }} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
