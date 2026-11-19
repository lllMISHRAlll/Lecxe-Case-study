import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChoiceButtons } from "./ChoiceButtons";

const choices = {
  prompt: "Which vendor did you mean?",
  options: [
    { id: "v1", label: "Zenith Steels Pvt. Ltd." },
    { id: "v2", label: "Granite Steels Pvt. Ltd." },
  ],
};

describe("ChoiceButtons", () => {
  it("shows the prompt and sends the chosen option", async () => {
    const onChoose = vi.fn();
    render(<ChoiceButtons choices={choices} onChoose={onChoose} />);

    expect(screen.getByText("Which vendor did you mean?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Granite Steels Pvt. Ltd." }));
    expect(onChoose).toHaveBeenCalledWith(choices.options[1]);
  });

  it("disables the options while a reply is streaming", () => {
    render(<ChoiceButtons choices={choices} onChoose={vi.fn()} disabled />);
    expect(screen.getByRole("button", { name: "Zenith Steels Pvt. Ltd." })).toBeDisabled();
  });
});
