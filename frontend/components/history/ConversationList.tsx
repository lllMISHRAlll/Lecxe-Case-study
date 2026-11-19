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
    return <p className="px-4 py-3 text-sm text-muted">Couldn&apos;t load your conversations.</p>;
  }
  if (list.data?.length === 0) {
    return <p className="px-4 py-3 text-sm text-muted">No conversations yet.</p>;
  }

  return (
    <ul aria-label="Past conversations" className="flex flex-col py-1">
      {(list.data ?? []).map((conversation) => {
        const active = conversation.id === activeId;
        return (
          <li key={conversation.id} className="group flex items-center gap-1 px-2">
            <button
              type="button"
              aria-label={`Open conversation ${conversation.title}`}
              aria-current={active ? "true" : undefined}
              onClick={() => onOpen(conversation.id)}
              className={`flex min-w-0 flex-1 items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-sunken ${
                active ? "bg-accent-soft font-medium" : ""
              }`}
            >
              <span className="truncate">{conversation.title}</span>
              <span className="shrink-0 text-xs text-muted">
                {dateFormat.format(new Date(conversation.updated_at))}
              </span>
            </button>
            <button
              type="button"
              aria-label={`Delete conversation ${conversation.title}`}
              onClick={() => remove.mutate(conversation.id)}
              className="rounded-md px-2 py-1 text-xs text-muted hover:bg-danger-soft hover:text-danger"
            >
              Delete
            </button>
          </li>
        );
      })}
    </ul>
  );
}
