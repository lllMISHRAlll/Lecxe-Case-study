"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteConversation, listConversations } from "@/lib/api";

interface ConversationListProps {
  activeId: string | null;
  onOpen: (id: string) => void;
  onDeleted: (id: string) => void;
}

const dateFormat = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" });

export function ConversationList({ activeId, onOpen, onDeleted }: ConversationListProps) {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ["conversations"], queryFn: listConversations });
  const remove = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, id) => {
      onDeleted(id);
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  if (list.isError) {
    return <p className="px-4 py-6 text-center text-sm text-muted">Couldn&apos;t load your conversations.</p>;
  }
  if (list.isPending) {
    return (
      <ul aria-hidden="true" className="flex flex-col gap-2 p-3">
        {[0, 1, 2].map((i) => (
          <li key={i} className="h-11 animate-pulse rounded-lg bg-sunken" />
        ))}
      </ul>
    );
  }
  if (list.data?.length === 0) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted">
        No conversations yet. Your chats will show up here.
      </p>
    );
  }

  return (
    <ul aria-label="Past conversations" className="flex flex-col gap-0.5 p-2">
      {(list.data ?? []).map((conversation) => {
        const active = conversation.id === activeId;
        return (
          <li key={conversation.id} className="group relative flex items-center">
            <button
              type="button"
              aria-label={`Open conversation ${conversation.title}`}
              aria-current={active ? "true" : undefined}
              onClick={() => onOpen(conversation.id)}
              className={`flex min-w-0 flex-1 flex-col gap-0.5 rounded-lg py-2 pr-10 pl-3 text-left transition hover:bg-sunken ${
                active ? "bg-accent-soft text-accent-strong" : ""
              }`}
            >
              <span className={`truncate text-sm ${active ? "font-semibold" : "font-medium"}`}>
                {conversation.title}
              </span>
              <span className="text-xs text-muted">
                {dateFormat.format(new Date(conversation.updated_at))}
              </span>
            </button>
            <button
              type="button"
              aria-label={`Delete conversation ${conversation.title}`}
              onClick={() => remove.mutate(conversation.id)}
              className="absolute right-1.5 grid size-7 place-items-center rounded-md text-muted opacity-0 transition group-hover:opacity-100 hover:bg-danger-soft hover:text-danger focus-visible:opacity-100"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" />
              </svg>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
