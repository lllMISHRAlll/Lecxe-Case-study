import { ApiError, apiUrl, toApiError } from "./api";
import { createSSEParser, toStreamEvent, type RawSSE } from "./sse";
import type { ChatRequest, StreamEvent } from "./types";

/**
 * Posts a chat request and calls `onEvent` for every typed event as it arrives.
 * Resolves when the stream ends. Throws ApiError if the server refuses the request.
 */
export async function streamChat(
  request: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(apiUrl("/api/chat/stream"), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) throw await toApiError(response);
  if (!response.body) {
    throw new ApiError(response.status, "empty_stream", "The server sent an empty response.");
  }

  const parser = createSSEParser();
  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  const emit = (raws: RawSSE[]) => {
    for (const raw of raws) {
      const event = toStreamEvent(raw);
      if (event) onEvent(event);
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    emit(parser.push(decoder.decode(value, { stream: true })));
  }
  emit(parser.push(decoder.decode()));
  emit(parser.flush());
}
