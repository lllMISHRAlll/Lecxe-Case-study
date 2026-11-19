"use client";

import type { ReactNode } from "react";
import { useSmoothText } from "@/hooks/useSmoothText";
import { RichText } from "@/lib/markdown";
import type { ChatMessage } from "@/stores/chatStore";

interface MessageBubbleProps {
  message: ChatMessage;
  /** What the assistant is doing right now, shown while waiting for the first words. */
  status?: string;
  /** Extra content under an assistant message: choices, feedback and so on. */
  children?: ReactNode;
}

export function MessageBubble({ message, status, children }: MessageBubbleProps) {
  if (message.sender === "user") {
    return (
      <div className="flex animate-rise justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-sm leading-relaxed text-on-accent shadow-sm">
          {message.text}
        </p>
      </div>
    );
  }
  return <AssistantBubble message={message} status={status}>{children}</AssistantBubble>;
}

function AssistantBubble({ message, status, children }: MessageBubbleProps) {
  const streaming = Boolean(message.streaming);
  const text = useSmoothText(message.text, streaming);
  const waiting = streaming && message.text === "" && !message.error;
  const typing = streaming || text.length < message.text.length;

  return (
    <div className="flex animate-rise flex-col items-start gap-2">
      <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-line bg-raised px-3.5 py-2.5 text-sm text-ink shadow-sm">
        {waiting ? (
          <p role="status" className="flex items-center gap-2.5 text-muted">
            <span aria-hidden="true" className="typing-dots inline-flex gap-1">
              <span />
              <span />
              <span />
            </span>
            <span className="animate-fade" key={status}>
              {status ?? "Thinking"}…
            </span>
          </p>
        ) : (
          text && (
            <div className="space-y-2">
              <RichText text={text} />
            </div>
          )
        )}
        {!waiting && typing && text !== "" && <span aria-hidden="true" className="stream-caret" />}
        {message.poCreated && (
          <p className="mt-2 animate-fade rounded-lg bg-ok-soft px-3 py-2 text-sm font-medium text-ok">
            Purchase order {message.poCreated.po_number} created for {message.poCreated.currency}{" "}
            {message.poCreated.total_amount}.
          </p>
        )}
        {message.error && (
          <p role="alert" className="mt-2 animate-fade rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {message.error.message}
            {message.error.reference && (
              <span className="block text-xs opacity-80">Reference: {message.error.reference}</span>
            )}
          </p>
        )}
      </div>
      {!streaming && children}
    </div>
  );
}
