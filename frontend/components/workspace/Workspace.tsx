"use client";

import { useCallback, useState } from "react";
import { CannedButtons } from "@/components/chat/CannedButtons";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChoiceButtons } from "@/components/chat/ChoiceButtons";
import { FeedbackButtons } from "@/components/chat/FeedbackButtons";
import { MessageList } from "@/components/chat/MessageList";
import { HistoryDrawer } from "@/components/history/HistoryDrawer";
import { ChatSkeleton } from "@/components/layout/Skeletons";
import { OutputPane } from "@/components/output/OutputPane";
import { POCard } from "@/components/po/POCard";
import { useChatStream } from "@/hooks/useChatStream";
import { useConversationUrl } from "@/hooks/useConversationUrl";
import type { User } from "@/lib/types";
import { useChatStore, type ChatMessage } from "@/stores/chatStore";

interface WorkspaceProps {
  user: User;
}

/** The split screen: chat on the left, streamed results on the right. */
export function Workspace({ user }: WorkspaceProps) {
  const { send } = useChatStream();
  const { open, loading, openError, dismissError } = useConversationUrl();
  const [historyOpen, setHistoryOpen] = useState(false);

  const messages = useChatStore((s) => s.messages);
  const output = useChatStore((s) => s.output);
  const streaming = useChatStore((s) => s.streaming);
  const title = useChatStore((s) => s.title);
  const conversationId = useChatStore((s) => s.conversationId);
  const editRequests = useChatStore((s) => s.editRequests);
  const newConversation = useChatStore((s) => s.newConversation);
  const requestEdit = useChatStore((s) => s.requestEdit);
  const setFeedback = useChatStore((s) => s.setFeedback);

  const draft = output.poDraft;
  const draftOpen = draft?.status === "open";

  function startNew() {
    dismissError();
    newConversation();
  }

  function openFromHistory(id: string) {
    setHistoryOpen(false);
    void open(id);
  }

  const closeHistory = useCallback(() => setHistoryOpen(false), []);
  const status = streaming ? output.steps.at(-1)?.label : undefined;
  const firstName = user.name.split(" ")[0];
  const run = (query: { id: string; label: string }) =>
    send({ button_id: query.id }, query.label);

  const emptyState = (
    <div className="m-auto flex w-full max-w-xl animate-fade flex-col items-center gap-5 py-6">
      <div className="text-center">
        <p className="text-lg font-semibold text-ink">What would you like to know, {firstName}?</p>
        <p className="mt-1 text-sm text-muted">
          Pick a suggested question or ask your own about vendors, POs, payments or stock.
        </p>
      </div>
      <CannedButtons variant="grid" disabled={streaming} onRun={run} />
    </div>
  );

  const renderExtras = (message: ChatMessage) => (
    <>
      {message.choices && (
        <ChoiceButtons
          choices={message.choices}
          disabled={streaming}
          onChoose={(option) =>
            send({ po_action: { type: "choose", choice: option.id } }, option.label)
          }
        />
      )}
      {message.id && !message.streaming && (
        <FeedbackButtons
          messageId={message.id}
          value={message.feedback}
          onSaved={(score) => setFeedback(message.id!, score)}
        />
      )}
    </>
  );

  const poSlot = draft && (
    <POCard
      key={`${draft.idempotency_key}-${draft.status}`}
      draft={draft}
      busy={streaming}
      onConfirm={(key) => send({ po_action: { type: "confirm", idempotency_key: key } })}
      onCancel={() => send({ po_action: { type: "cancel" } })}
      onEdit={requestEdit}
    />
  );

  return (
    <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_minmax(0,1fr)] lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:grid-rows-1">
      <section
        aria-label="Chat"
        className="relative flex min-h-0 min-w-0 flex-col border-b border-line bg-canvas lg:border-r lg:border-b-0"
      >
        <div className="flex items-center justify-between gap-2 border-b border-line bg-panel/60 px-4 py-2.5 backdrop-blur">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              aria-haspopup="dialog"
              aria-expanded={historyOpen}
              onClick={() => setHistoryOpen(true)}
              className="flex shrink-0 items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-ink transition hover:bg-sunken"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5M12 7v5l3 2" />
              </svg>
              History
            </button>
            {loading ? (
              <div className="h-4 w-40 animate-pulse rounded-md bg-skeleton" />
            ) : (
              <h2 className="truncate text-sm font-semibold">{title ?? "New conversation"}</h2>
            )}
          </div>
          <button
            type="button"
            onClick={startNew}
            disabled={streaming}
            className="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent-soft disabled:opacity-50"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New chat
          </button>
        </div>
        {openError && (
          <p className="border-b border-line bg-warn-soft px-4 py-2 text-xs text-warn">{openError}</p>
        )}
        {loading ? (
          <ChatSkeleton />
        ) : (
          <MessageList
            messages={messages}
            renderExtras={renderExtras}
            status={status}
            emptyState={emptyState}
          />
        )}
        <div className="flex flex-col gap-2.5 border-t border-line bg-panel px-4 py-3">
          {!loading && messages.length > 0 && <CannedButtons disabled={streaming} onRun={run} />}
          <ChatInput
            disabled={streaming || loading}
            focusSignal={editRequests}
            onSend={(text) => send({ message: text }, text)}
            placeholder={
              draftOpen
                ? "Describe a change, e.g. change price to 115"
                : `Ask a question, ${firstName}…`
            }
          />
        </div>
        {/* Laid over the chat pane (absolute), so nothing above moves when it opens. */}
        <HistoryDrawer
          open={historyOpen}
          activeId={conversationId}
          onClose={closeHistory}
          onOpen={openFromHistory}
          onDeleted={(id) => {
            if (id === useChatStore.getState().conversationId) startNew();
          }}
        />
      </section>
      <OutputPane output={output} running={streaming} loading={loading} poSlot={poSlot} />
    </div>
  );
}
