import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("shows the current step while waiting for the first words", () => {
    render(
      <MessageBubble
        message={{ localId: "m1", sender: "assistant", text: "", streaming: true }}
        status="Writing a query"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Writing a query");
  });

  it("falls back to a generic waiting label", () => {
    render(<MessageBubble message={{ localId: "m1", sender: "assistant", text: "", streaming: true }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Thinking");
  });

  it("renders bold answer text without raw asterisks", () => {
    const { container } = render(
      <MessageBubble message={{ localId: "m1", sender: "assistant", text: "**26** are placed." }} />,
    );
    expect(container.querySelector("strong")).toHaveTextContent("26");
    expect(container.textContent).not.toContain("**");
  });

  it("keeps user text exactly as typed", () => {
    render(<MessageBubble message={{ localId: "m1", sender: "user", text: "show **raw**" }} />);
    expect(screen.getByText("show **raw**")).toBeInTheDocument();
  });
});
