import { http, HttpResponse } from "msw";

/**
 * A chat stream handler that sends each chunk separately, so tests see tokens arrive one by one.
 * `onRequest` receives the parsed request body, so tests can assert what was sent.
 */
export function streamHandler(chunks: string[], onRequest?: (body: unknown) => void) {
  return http.post("/api/chat/stream", async ({ request }) => {
    onRequest?.(await request.json());
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
          await new Promise((resolve) => setTimeout(resolve, 0));
        }
        controller.close();
      },
    });
    return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
  });
}

export function sse(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}
