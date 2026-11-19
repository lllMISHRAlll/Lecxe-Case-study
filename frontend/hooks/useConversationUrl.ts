"use client";

import { useCallback, useEffect, useState } from "react";
import { getConversation } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";

const PARAM = "c";

function readConversationParam(): string | null {
  return new URLSearchParams(window.location.search).get(PARAM);
}

function writeConversationParam(id: string | null) {
  const url = new URL(window.location.href);
  if (id) url.searchParams.set(PARAM, id);
  else url.searchParams.delete(PARAM);
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

/**
 * Keeps the open conversation in the URL (`?c=<id>`), so a refresh restores it,
 * and opens conversations from history.
 */
export function useConversationUrl() {
  const conversationId = useChatStore((s) => s.conversationId);
  const [pendingId, setPendingId] = useState<string | null>(() => readConversationParam());
  const [openError, setOpenError] = useState<string | null>(null);
  // True while a conversation is being fetched (a reload with ?c=, or opening from history).
  const [loading, setLoading] = useState<boolean>(() => pendingId !== null);

  const open = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const detail = await getConversation(id);
      useChatStore.getState().loadConversation(detail);
      setOpenError(null);
    } catch {
      useChatStore.getState().newConversation();
      setOpenError("Couldn't open that conversation. Starting a new one.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Restore the conversation named in the URL once, on first load.
  useEffect(() => {
    if (!pendingId) return;
    void open(pendingId).finally(() => setPendingId(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Mirror the open conversation into the URL, once any restore has finished.
  useEffect(() => {
    if (pendingId) return;
    writeConversationParam(conversationId);
  }, [conversationId, pendingId]);

  return { open, loading, openError, dismissError: () => setOpenError(null) };
}
