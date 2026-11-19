import { act, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StepTracker } from "./StepTracker";

const steps = [
  { node: "guard_input", label: "Safety checks passed" },
  { node: "validate_sql", label: "Query needs a fix", status: "warn" as const },
  { node: "execute_sql", label: "The query failed", status: "error" as const },
];

describe("StepTracker", () => {
  afterEach(() => vi.useRealTimers());

  it("FE-10 lists finished steps in order", () => {
    render(<StepTracker steps={steps.slice(0, 1)} running={false} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual(["Safety checks passed"]);
  });

  it("reveals steps one after another while the answer is running", () => {
    vi.useFakeTimers();
    render(<StepTracker steps={steps} running />);
    expect(screen.getByText("Safety checks passed")).toBeInTheDocument();
    expect(screen.queryByText("The query failed")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(200));
    expect(screen.getByText("Query needs a fix")).toBeInTheDocument();
    expect(screen.queryByText("The query failed")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(200));
    expect(screen.getByText("The query failed")).toBeInTheDocument();
  });

  it("shows the step in progress while running and a summary when finished", () => {
    const { rerender } = render(<StepTracker steps={steps.slice(0, 1)} running />);
    expect(screen.getByText(/working/i)).toBeInTheDocument();
    rerender(<StepTracker steps={steps.slice(0, 1)} running={false} />);
    expect(screen.queryByText(/working/i)).not.toBeInTheDocument();
    expect(screen.getByText("1 step")).toBeInTheDocument();
  });

  it("marks retried and failed steps", () => {
    render(<StepTracker steps={steps} running={false} />);
    expect(screen.getByText("Query needs a fix").closest("li")).toHaveAttribute("data-status", "warn");
    expect(screen.getByText("The query failed").closest("li")).toHaveAttribute("data-status", "error");
    expect(screen.getByText("Safety checks passed").closest("li")).toHaveAttribute("data-status", "done");
    expect(screen.getByText("3 steps")).toBeInTheDocument();
  });

  it("renders nothing when there are no steps and nothing is running", () => {
    const { container } = render(<StepTracker steps={[]} running={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
