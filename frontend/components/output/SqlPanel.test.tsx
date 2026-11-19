import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SqlPanel } from "./SqlPanel";

const QUERY = "SELECT name FROM proc_vendors LIMIT 5";

describe("SqlPanel", () => {
  it("FE-11 shows the SQL with keywords highlighted", () => {
    const { container } = render(<SqlPanel sql={{ sql: QUERY, source: "generated", attempt: 1 }} />);
    expect(screen.getByRole("heading", { name: /sql/i })).toBeInTheDocument();
    expect(container.querySelector("code")?.textContent).toBe(QUERY);
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

  it("copies the SQL to the clipboard and confirms it", async () => {
    const user = userEvent.setup();
    render(<SqlPanel sql={{ sql: QUERY, source: "generated", attempt: 1 }} />);

    await user.click(screen.getByRole("button", { name: /copy sql/i }));

    expect(await navigator.clipboard.readText()).toBe(QUERY);
    expect(screen.getByRole("button", { name: /copied/i })).toBeInTheDocument();
  });

  it("says so when the clipboard is not available", async () => {
    const user = userEvent.setup();
    render(<SqlPanel sql={{ sql: QUERY, source: "generated", attempt: 1 }} />);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    document.execCommand = vi.fn().mockReturnValue(false);

    await user.click(screen.getByRole("button", { name: /copy sql/i }));

    expect(await screen.findByRole("button", { name: /couldn't copy/i })).toBeInTheDocument();
  });

  it("falls back to the selection copy command when the clipboard API refuses", async () => {
    const user = userEvent.setup();
    render(<SqlPanel sql={{ sql: QUERY, source: "generated", attempt: 1 }} />);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    document.execCommand = vi.fn().mockReturnValue(true);

    await user.click(screen.getByRole("button", { name: /copy sql/i }));

    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(await screen.findByRole("button", { name: /copied/i })).toBeInTheDocument();
  });
});
