"use client";

import { CannedButtons } from "@/components/chat/CannedButtons";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChoiceButtons } from "@/components/chat/ChoiceButtons";
import { MessageList } from "@/components/chat/MessageList";
import { OutputPane } from "@/components/output/OutputPane";
import { POCard } from "@/components/po/POCard";
import { useChatStream } from "@/hooks/useChatStream";
import type { User } from "@/lib/types";
import { useChatStore, type ChatMessage } from "@/stores/chatStore";

interface WorkspaceProps {
  user: User;
}

/** The split screen: chat on the left, streamed results on the right. */
export function Workspace({ user }: WorkspaceProps) {
  const { send } = useChatStream();
  const messages = useChatStore((s) => s.messages);
  const output = useChatStore((s) => s.output);
  const streaming = useChatStore((s) => s.streaming);
  const title = useChatStore((s) => s.title);
  const editRequests = useChatStore((s) => s.editRequests);
  const newConversation = useChatStore((s) => s.newConversation);
  const requestEdit = useChatStore((s) => s.requestEdit);

  const draft = output.poDraft;
  const draftOpen = draft?.status === "open";

  const renderExtras = (message: ChatMessage) =>
    message.choices && (
      <ChoiceButtons
        choices={message.choices}
        disabled={streaming}
        onChoose={(option) => send({ po_action: { type: "choose", choice: option.id } }, option.label)}
      />
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
          <button
            type="button"
            onClick={newConversation}
            disabled={streaming}
            className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-accent hover:bg-accent-soft disabled:opacity-50"
          >
            New chat
          </button>
        </div>
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
