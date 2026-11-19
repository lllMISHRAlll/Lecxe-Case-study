import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StepTracker } from "./StepTracker";

describe("StepTracker", () => {
  it("FE-10 lists finished steps in order", () => {
    render(
      <StepTracker
        steps={[
          { node: "guard_input", label: "Checked the question" },
          { node: "execute_sql", label: "Ran the query" },
        ]}
        running={false}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual(["Checked the question", "Ran the query"]);
  });

  it("shows a working indicator while the run is still going", () => {
    render(<StepTracker steps={[{ node: "a", label: "Step A" }]} running />);
    expect(screen.getByText(/working/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no steps and nothing is running", () => {
    const { container } = render(<StepTracker steps={[]} running={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
