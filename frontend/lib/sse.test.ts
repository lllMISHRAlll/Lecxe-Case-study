import { describe, expect, it } from "vitest";
import { createSSEParser, toStreamEvent } from "./sse";

describe("FE-08 SSE parser", () => {
  it("parses a single complete event", () => {
    const parser = createSSEParser();
    expect(parser.push('event: token\ndata: {"text":"Hi"}\n\n')).toEqual([
      { event: "token", data: '{"text":"Hi"}' },
    ]);
  });

  it("joins an event split across chunks, even mid-line", () => {
    const parser = createSSEParser();
    expect(parser.push("event: tok")).toEqual([]);
    expect(parser.push('en\ndata: {"te')).toEqual([]);
    expect(parser.push('xt":"Hi"}\n')).toEqual([]);
    expect(parser.push("\n")).toEqual([{ event: "token", data: '{"text":"Hi"}' }]);
  });

  it("returns several events from one chunk in order", () => {
    const parser = createSSEParser();
    const events = parser.push('event: step\ndata: {"a":1}\n\nevent: sql\ndata: {"b":2}\n\n');
    expect(events.map((e) => e.event)).toEqual(["step", "sql"]);
  });

  it("accepts CRLF line endings", () => {
    const parser = createSSEParser();
    expect(parser.push('event: done\r\ndata: {"message_id":"m"}\r\n\r\n')).toEqual([
      { event: "done", data: '{"message_id":"m"}' },
    ]);
  });

  it("joins multi-line data with newlines", () => {
    const parser = createSSEParser();
    expect(parser.push("event: token\ndata: line1\ndata: line2\n\n")).toEqual([
      { event: "token", data: "line1\nline2" },
    ]);
  });

  it("ignores comments, keep-alives and other fields", () => {
    const parser = createSSEParser();
    expect(parser.push(": keep-alive\n\nid: 7\nretry: 1000\nevent: done\ndata: {}\n\n")).toEqual([
      { event: "done", data: "{}" },
    ]);
  });

  it("defaults the event name to message", () => {
    const parser = createSSEParser();
    expect(parser.push("data: x\n\n")).toEqual([{ event: "message", data: "x" }]);
  });

  it("accepts a field without a space after the colon", () => {
    const parser = createSSEParser();
    expect(parser.push("event:token\ndata:abc\n\n")).toEqual([{ event: "token", data: "abc" }]);
  });

  it("treats a field line without a colon as an empty value", () => {
    const parser = createSSEParser();
    expect(parser.push("event: token\ndata\ndata: x\n\n")).toEqual([
      { event: "token", data: "\nx" },
    ]);
  });

  it("drops an event that has no data", () => {
    const parser = createSSEParser();
    expect(parser.push("event: token\n\n")).toEqual([]);
  });

  it("flush returns a trailing event that never got its blank line", () => {
    const parser = createSSEParser();
    expect(parser.push('event: done\ndata: {"message_id":"m"}')).toEqual([]);
    expect(parser.flush()).toEqual([{ event: "done", data: '{"message_id":"m"}' }]);
    expect(parser.flush()).toEqual([]);
  });
});

describe("toStreamEvent", () => {
  it("turns a known event with JSON data into a typed event", () => {
    expect(toStreamEvent({ event: "token", data: '{"text":"Hi"}' })).toEqual({
      event: "token",
      data: { text: "Hi" },
    });
  });

  it("returns null for an unknown event name", () => {
    expect(toStreamEvent({ event: "mystery", data: "{}" })).toBeNull();
  });

  it("returns null for data that is not JSON", () => {
    expect(toStreamEvent({ event: "token", data: "not json" })).toBeNull();
  });
});
