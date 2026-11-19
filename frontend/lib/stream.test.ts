import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/tests/msw/server";
import { sse, streamHandler } from "@/tests/msw/stream";
import { ApiError } from "./api";
import { streamChat } from "./stream";
import type { StreamEvent } from "./types";

describe("streamChat", () => {
  it("posts the request and emits typed events in order, across chunk splits", async () => {
    let body: unknown;
    const full = sse("step", { node: "a", label: "A" }) + sse("token", { text: "Hi" });
    server.use(
      streamHandler(
        [full.slice(0, 10), full.slice(10, 40), full.slice(40), sse("done", { message_id: "m" })],
        (b) => (body = b),
      ),
    );
    const events: StreamEvent[] = [];

    await streamChat({ message: "hello" }, (e) => events.push(e));

    expect(body).toEqual({ message: "hello" });
    expect(events.map((e) => e.event)).toEqual(["step", "token", "done"]);
  });

  it("skips unknown or malformed events", async () => {
    server.use(
      streamHandler(["event: mystery\ndata: {}\n\n", "event: token\ndata: oops\n\n", sse("done", { message_id: "m" })]),
    );
    const events: StreamEvent[] = [];
    await streamChat({ message: "x" }, (e) => events.push(e));
    expect(events.map((e) => e.event)).toEqual(["done"]);
  });

  it("emits a final event that lacks its trailing blank line", async () => {
    server.use(streamHandler(['event: done\ndata: {"message_id":"m"}']));
    const events: StreamEvent[] = [];
    await streamChat({ message: "x" }, (e) => events.push(e));
    expect(events).toEqual([{ event: "done", data: { message_id: "m" } }]);
  });

  it("throws an ApiError when the server refuses the request", async () => {
    server.use(http.post("/api/chat/stream", () => new HttpResponse(null, { status: 429 })));
    const error = await streamChat({ message: "x" }, () => {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(429);
  });

  it("throws when the response has no body", async () => {
    server.use(http.post("/api/chat/stream", () => new HttpResponse(null, { status: 200 })));
    const error = await streamChat({ message: "x" }, () => {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
  });
});
