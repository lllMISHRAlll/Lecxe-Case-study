"use client";

import { useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage } from "@/stores/chatStore";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  /** Renders extra content under an assistant message. */
  renderExtras?: (message: ChatMessage) => ReactNode;
}

export function MessageList({ messages, renderExtras }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const last = messages.at(-1);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, last?.text]);

  return (
    <div
      role="log"
      aria-label="Conversation"
      aria-live="polite"
      className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4"
    >
      {messages.length === 0 && (
        <div className="m-auto max-w-sm text-center text-sm text-muted">
          <p className="font-medium text-ink">Ask anything about purchasing and stock.</p>
          <p>For example: &ldquo;Which vendors have overdue deliveries?&rdquo;</p>
        </div>
      )}
      {messages.map((message) => (
        <MessageBubble key={message.localId} message={message}>
          {message.sender === "assistant" && renderExtras?.(message)}
        </MessageBubble>
      ))}
      <div ref={endRef} />
    </div>
  );
}
