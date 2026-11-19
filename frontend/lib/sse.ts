import type { StreamEvent } from "./types";

/** One raw Server-Sent Event: its name and its (possibly multi-line) data. */
export interface RawSSE {
  event: string;
  data: string;
}

export interface SSEParser {
  /** Feeds a chunk of text and returns every event completed by it. */
  push(chunk: string): RawSSE[];
  /** Returns a final event left without its terminating blank line, if any. */
  flush(): RawSSE[];
}

const KNOWN_EVENTS = new Set<StreamEvent["event"]>([
  "conversation",
  "step",
  "sql",
  "rows",
  "chart",
  "token",
  "answer_replace",
  "choices",
  "po_draft",
  "po_created",
  "error",
  "done",
]);

/**
 * Incremental SSE parser following the HTML spec's line rules:
 * events end at a blank line, `data:` lines are joined with "\n", lines starting with ":" are
 * comments, and unknown fields are ignored. Chunks may split anywhere, even inside a line.
 */
export function createSSEParser(): SSEParser {
  let buffer = "";
  let eventName = "";
  let dataLines: string[] = [];

  function dispatch(out: RawSSE[]) {
    if (dataLines.length > 0) {
      out.push({ event: eventName || "message", data: dataLines.join("\n") });
    }
    eventName = "";
    dataLines = [];
  }

  function handleLine(line: string, out: RawSSE[]) {
    if (line === "") {
      dispatch(out);
      return;
    }
    if (line.startsWith(":")) return;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") eventName = value;
    else if (field === "data") dataLines.push(value);
  }

  return {
    push(chunk) {
      buffer += chunk;
      const out: RawSSE[] = [];
      const lines = buffer.split(/\r\n|\n|\r/);
      buffer = lines.pop() ?? "";
      for (const line of lines) handleLine(line, out);
      return out;
    },
    flush() {
      const out: RawSSE[] = [];
      if (buffer !== "") {
        handleLine(buffer, out);
        buffer = "";
      }
      dispatch(out);
      return out;
    },
  };
}

/** Parses a raw event into a typed stream event, or null if it is unknown or malformed. */
export function toStreamEvent(raw: RawSSE): StreamEvent | null {
  if (!KNOWN_EVENTS.has(raw.event as StreamEvent["event"])) return null;
  try {
    return { event: raw.event, data: JSON.parse(raw.data) } as StreamEvent;
  } catch {
    return null;
  }
}
