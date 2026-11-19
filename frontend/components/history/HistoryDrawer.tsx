"use client";

import { useEffect, useRef } from "react";
import { ConversationList } from "./ConversationList";

interface HistoryDrawerProps {
  open: boolean;
  activeId: string | null;
  onClose: () => void;
  onOpen: (id: string) => void;
  onDeleted: (id: string) => void;
}

/** Past conversations in a drawer laid over the chat pane. The chat underneath never moves. */
export function HistoryDrawer({ open, activeId, onClose, onOpen, onDeleted }: HistoryDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const returnFocus = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      returnFocus?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div data-overlay className="absolute inset-0 z-30 flex">
      <div
        data-testid="history-backdrop"
        aria-hidden="true"
        onClick={onClose}
        className="absolute inset-0 animate-fade bg-scrim backdrop-blur-[2px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-title"
        className="relative z-10 flex h-full w-80 max-w-[88%] animate-slide-in flex-col border-r border-line bg-panel shadow-2xl"
      >
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
          <div>
            <h2 id="history-title" className="text-sm font-semibold">
              Conversations
            </h2>
            <p className="text-xs text-muted">Your past chats, newest first</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            aria-label="Close history"
            onClick={onClose}
            className="grid size-8 place-items-center rounded-lg text-muted transition hover:bg-sunken hover:text-ink"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ConversationList activeId={activeId} onOpen={onOpen} onDeleted={onDeleted} />
        </div>
      </div>
    </div>
  );
}
