import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/render";
import { HistoryDrawer } from "./HistoryDrawer";

function renderDrawer(onClose = vi.fn()) {
  renderWithProviders(
    <HistoryDrawer open activeId={null} onClose={onClose} onOpen={vi.fn()} onDeleted={vi.fn()} />,
  );
  return onClose;
}

describe("HistoryDrawer", () => {
  it("is a modal dialog laid over the chat, not part of its flow", () => {
    renderDrawer();
    const dialog = screen.getByRole("dialog", { name: "Conversations" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog.closest("[data-overlay]")).toHaveClass("absolute");
  });

  it("moves focus to the close button", () => {
    renderDrawer();
    expect(screen.getByRole("button", { name: "Close history" })).toHaveFocus();
  });

  it("closes with the close button, Escape, or a click on the backdrop", async () => {
    const onClose = renderDrawer();
    await userEvent.click(screen.getByRole("button", { name: "Close history" }));
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByTestId("history-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("lists past conversations", async () => {
    renderDrawer();
    expect(await screen.findByRole("list", { name: "Past conversations" })).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    renderWithProviders(
      <HistoryDrawer open={false} activeId={null} onClose={vi.fn()} onOpen={vi.fn()} onDeleted={vi.fn()} />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
