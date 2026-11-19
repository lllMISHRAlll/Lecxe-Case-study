"use client";

import { useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage } from "@/stores/chatStore";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  /** Renders extra content under an assistant message. */
  renderExtras?: (message: ChatMessage) => ReactNode;
  /** What the assistant is doing, shown in the waiting bubble. */
  status?: string;
  /** Shown when the conversation is empty. */
  emptyState?: ReactNode;
}

/** Distance from the bottom (px) within which new content keeps the view pinned. */
const STICK_DISTANCE = 120;

export function MessageList({ messages, renderExtras, status, emptyState }: MessageListProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  const last = messages.at(-1);

  function onScroll() {
    const el = scrollerRef.current;
    if (!el) return;
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_DISTANCE;
  }

  useEffect(() => {
    pinnedRef.current = true; // a new message always brings the view to it
  }, [messages.length]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !pinnedRef.current) return;
    // Follow the reveal smoothly while the user stays near the bottom.
    const observer = typeof MutationObserver === "function"
      ? new MutationObserver(() => {
          if (pinnedRef.current) el.scrollTop = el.scrollHeight;
        })
      : null;
    observer?.observe(el, { childList: true, subtree: true, characterData: true });
    el.scrollTop = el.scrollHeight;
    return () => observer?.disconnect();
  }, [messages.length, last?.text, last?.streaming]);

  return (
    <div
      ref={scrollerRef}
      onScroll={onScroll}
      role="log"
      aria-label="Conversation"
      aria-live="polite"
      className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-5"
    >
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-1 flex-col gap-4">
      {messages.length === 0 &&
        (emptyState ?? (
          <div className="m-auto max-w-sm text-center text-sm text-muted">
            <p className="font-medium text-ink">Ask anything about purchasing and stock.</p>
            <p>For example: &ldquo;Which vendors have overdue deliveries?&rdquo;</p>
          </div>
        ))}
      {messages.map((message) => (
        <MessageBubble
          key={message.localId}
          message={message}
          status={message === last && message.streaming ? status : undefined}
        >
          {message.sender === "assistant" && renderExtras?.(message)}
        </MessageBubble>
      ))}
      </div>
    </div>
  );
}
