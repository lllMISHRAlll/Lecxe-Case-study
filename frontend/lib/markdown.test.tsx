import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RichText } from "./markdown";

describe("RichText", () => {
  it("renders **bold** as strong text", () => {
    const { container } = render(<RichText text="**Zenith** leads with ₹72,160." />);
    expect(container.querySelector("strong")).toHaveTextContent("Zenith");
    expect(container).toHaveTextContent("Zenith leads with ₹72,160.");
    expect(container.textContent).not.toContain("**");
  });

  it("keeps an unfinished bold marker as plain text while streaming", () => {
    const { container } = render(<RichText text="Spend is **72,1" />);
    expect(container).toHaveTextContent("Spend is **72,1");
  });

  it("turns '- ' lines into a list and keeps paragraphs", () => {
    const { container } = render(<RichText text={"Top vendors:\n- Zenith\n- Anand\n\nDone."} />);
    expect(container.querySelectorAll("li")).toHaveLength(2);
    expect(container.querySelectorAll("p")).toHaveLength(2);
  });
});
