import type { ReactNode } from "react";
import type { ChatMessage } from "@/stores/chatStore";

interface MessageBubbleProps {
  message: ChatMessage;
  /** Extra content under an assistant message: choices, feedback and so on. */
  children?: ReactNode;
}

export function MessageBubble({ message, children }: MessageBubbleProps) {
  if (message.sender === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-accent px-3.5 py-2 text-sm text-white">
          {message.text}
        </p>
      </div>
    );
  }

  const waiting = message.streaming && message.text === "" && !message.error;

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="max-w-[90%] rounded-2xl rounded-bl-sm border border-line bg-panel px-3.5 py-2 text-sm shadow-xs">
        {waiting ? (
          <span className="text-muted">Thinking…</span>
        ) : (
          message.text && <p className="whitespace-pre-wrap">{message.text}</p>
        )}
        {message.streaming && message.text !== "" && (
          <span aria-hidden="true" className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-accent align-middle" />
        )}
        {message.poCreated && (
          <p className="mt-2 rounded-md bg-ok-soft px-3 py-2 text-sm font-medium text-ok">
            Purchase order {message.poCreated.po_number} created for {message.poCreated.currency}{" "}
            {message.poCreated.total_amount}.
          </p>
        )}
        {message.error && (
          <p role="alert" className="mt-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
            {message.error.message}
            {message.error.reference && (
              <span className="block text-xs opacity-80">Reference: {message.error.reference}</span>
            )}
          </p>
        )}
      </div>
      {children}
    </div>
  );
}
