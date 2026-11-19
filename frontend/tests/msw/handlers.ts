import { http, HttpResponse } from "msw";
import type { Role } from "@/lib/types";
import {
  cannedByRole,
  conversationDetails,
  conversations,
  demoUsers,
  sseBody,
  userFor,
} from "./fixtures";

/** Mutable state the default handlers read, so tests can switch the signed-in role. */
export const mockState: { role: Role } = { role: "procurement_manager" };

export const handlers = [
  http.get("/api/auth/demo-users", () => HttpResponse.json(demoUsers)),

  http.post("/api/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    const demo = demoUsers.find((u) => u.email === body.email);
    if (!demo || body.password !== "1234567890") {
      return HttpResponse.json(
        {
          error: {
            code: "invalid_credentials",
            message: "Email or password is incorrect.",
            reference: "ref-1",
          },
        },
        { status: 401 },
      );
    }
    mockState.role = demo.role;
    return HttpResponse.json({ user: userFor(demo.role) });
  }),

  http.get("/api/auth/me", () => HttpResponse.json({ user: userFor(mockState.role) })),

  http.post("/api/auth/logout", () => new HttpResponse(null, { status: 204 })),

  http.get("/api/canned", () => HttpResponse.json(cannedByRole[mockState.role])),

  http.get("/api/conversations", () => HttpResponse.json(conversations)),

  http.get("/api/conversations/:id", ({ params }) => {
    const detail = conversationDetails[params.id as string];
    return detail
      ? HttpResponse.json(detail)
      : HttpResponse.json(
          { error: { code: "not_found", message: "Conversation not found." } },
          { status: 404 },
        );
  }),

  http.delete("/api/conversations/:id", () => new HttpResponse(null, { status: 204 })),

  http.post("/api/feedback", () => new HttpResponse(null, { status: 204 })),

  http.post(
    "/api/chat/stream",
    () =>
      new HttpResponse(
        sseBody([
          ["conversation", { conversation_id: "conv-new", title: "New" }],
          ["token", { text: "Hello" }],
          ["done", { message_id: "msg-new" }],
        ]),
        { headers: { "Content-Type": "text/event-stream" } },
      ),
  ),
];
