"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  placeholder?: string;
  /** Changing this number moves focus to the input. */
  focusSignal?: number;
}

export function ChatInput({ onSend, disabled, placeholder, focusSignal = 0 }: ChatInputProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const trimmed = text.trim();

  useEffect(() => {
    if (focusSignal > 0) inputRef.current?.focus();
  }, [focusSignal]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2">
      <label htmlFor="chat-message" className="sr-only">
        Message
      </label>
      <textarea
        id="chat-message"
        ref={inputRef}
        rows={2}
        value={text}
        disabled={disabled}
        placeholder={placeholder ?? "Ask about vendors, POs or stock…"}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        className="min-h-[2.75rem] flex-1 resize-none rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-accent disabled:bg-sunken"
      />
      <button
        type="submit"
        disabled={disabled || !trimmed}
        className="rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
      >
        Send
      </button>
    </form>
  );
}
