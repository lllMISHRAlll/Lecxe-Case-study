"use client";

import { useState } from "react";
import { CannedButtons } from "@/components/chat/CannedButtons";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChoiceButtons } from "@/components/chat/ChoiceButtons";
import { FeedbackButtons } from "@/components/chat/FeedbackButtons";
import { MessageList } from "@/components/chat/MessageList";
import { ConversationList } from "@/components/history/ConversationList";
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
  const { open, openError, dismissError } = useConversationUrl();
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
        className="flex min-h-0 min-w-0 flex-col border-b border-line bg-canvas lg:border-r lg:border-b-0"
      >
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
          <h2 className="truncate text-sm font-semibold">{title ?? "New conversation"}</h2>
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              aria-expanded={historyOpen}
              aria-controls="history-panel"
              onClick={() => setHistoryOpen((v) => !v)}
              className="rounded-md px-2 py-1 text-xs font-medium text-ink hover:bg-sunken"
            >
              History
            </button>
            <button
              type="button"
              onClick={startNew}
              disabled={streaming}
              className="rounded-md px-2 py-1 text-xs font-medium text-accent hover:bg-accent-soft disabled:opacity-50"
            >
              New chat
            </button>
          </div>
        </div>
        {historyOpen && (
          <div id="history-panel" className="max-h-64 overflow-y-auto border-b border-line bg-panel">
            <ConversationList
              activeId={conversationId}
              onOpen={openFromHistory}
              onDeleted={(id) => {
                if (id === useChatStore.getState().conversationId) startNew();
              }}
            />
          </div>
        )}
        {openError && (
          <p className="border-b border-line bg-warn-soft px-4 py-2 text-xs text-warn">{openError}</p>
        )}
        <MessageList messages={messages} renderExtras={renderExtras} />
        <div className="flex flex-col gap-3 border-t border-line bg-panel px-4 py-3">
          <CannedButtons
            disabled={streaming}
            onRun={(query) => send({ button_id: query.id }, query.label)}
          />
          <ChatInput
            disabled={streaming}
            focusSignal={editRequests}
            onSend={(text) => send({ message: text }, text)}
            placeholder={
              draftOpen
                ? "Describe a change, e.g. change price to 115"
                : `Ask a question, ${user.name.split(" ")[0]}…`
            }
          />
        </div>
      </section>
      <OutputPane output={output} running={streaming} poSlot={poSlot} />
    </div>
  );
}
