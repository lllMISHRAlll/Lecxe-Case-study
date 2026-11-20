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
    expect(onChoose).toHaveBeenCalledWith([choices.options[1]]);
  });

  describe("when several can be picked", () => {
    const items = {
      prompt: "Which items did you mean?",
      multiple: true,
      options: [
        { id: "item:1", label: "Shutter 6000" },
        { id: "item:2", label: "Brushed DC motor" },
        { id: "item:3", label: "Window" },
      ],
    };

    it("lets the user tick several options and submits them together", async () => {
      const onChoose = vi.fn();
      render(<ChoiceButtons choices={items} onChoose={onChoose} />);

      await userEvent.click(screen.getByRole("button", { name: "Shutter 6000" }));
      await userEvent.click(screen.getByRole("button", { name: "Window" }));
      expect(onChoose).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Shutter 6000" })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByRole("button", { name: "Brushed DC motor" })).toHaveAttribute("aria-pressed", "false");

      await userEvent.click(screen.getByRole("button", { name: /submit \(2\)/i }));
      expect(onChoose).toHaveBeenCalledWith([items.options[0], items.options[2]]);
    });

    it("keeps Submit disabled until something is ticked, and a tick can be undone", async () => {
      render(<ChoiceButtons choices={items} onChoose={vi.fn()} />);
      const submit = screen.getByRole("button", { name: /^submit/i });
      expect(submit).toBeDisabled();

      await userEvent.click(screen.getByRole("button", { name: "Window" }));
      expect(submit).toBeEnabled();
      await userEvent.click(screen.getByRole("button", { name: "Window" }));
      expect(submit).toBeDisabled();
    });

    it("can select every option at once", async () => {
      const onChoose = vi.fn();
      render(<ChoiceButtons choices={items} onChoose={onChoose} />);
      await userEvent.click(screen.getByRole("button", { name: /select all/i }));
      await userEvent.click(screen.getByRole("button", { name: /submit \(3\)/i }));
      expect(onChoose).toHaveBeenCalledWith(items.options);
    });

    it("disables everything while a reply is streaming", () => {
      render(<ChoiceButtons choices={items} onChoose={vi.fn()} disabled />);
      expect(screen.getByRole("button", { name: "Window" })).toBeDisabled();
      expect(screen.getByRole("button", { name: /^submit/i })).toBeDisabled();
    });
  });

  it("disables the options while a reply is streaming", () => {
    render(<ChoiceButtons choices={choices} onChoose={vi.fn()} disabled />);
    expect(screen.getByRole("button", { name: "Zenith Steels Pvt. Ltd." })).toBeDisabled();
  });
});
