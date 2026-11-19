import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/tests/msw/server";
import { FeedbackButtons } from "./FeedbackButtons";

describe("FeedbackButtons", () => {
  it.each([
    ["Helpful", 1],
    ["Not helpful", -1],
  ] as const)("FE-20 sends %s feedback for the message", async (name, score) => {
    let body: unknown;
    server.use(
      http.post("/api/feedback", async ({ request }) => {
        body = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const onSaved = vi.fn();
    render(<FeedbackButtons messageId="m42" onSaved={onSaved} />);

    await userEvent.click(screen.getByRole("button", { name }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(score));
    expect(body).toEqual({ message_id: "m42", score });
  });

  it("shows the saved choice as pressed", () => {
    render(<FeedbackButtons messageId="m1" value={1} onSaved={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Helpful" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Not helpful" })).toHaveAttribute("aria-pressed", "false");
  });

  it("says so when feedback cannot be saved", async () => {
    server.use(http.post("/api/feedback", () => new HttpResponse(null, { status: 500 })));
    const onSaved = vi.fn();
    render(<FeedbackButtons messageId="m1" onSaved={onSaved} />);

    await userEvent.click(screen.getByRole("button", { name: "Helpful" }));

    expect(await screen.findByText(/couldn't save feedback/i)).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });
});
