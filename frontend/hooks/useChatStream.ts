"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { ApiError } from "@/lib/api";
import { streamChat } from "@/lib/stream";
import type { ChatRequest } from "@/lib/types";
import { useChatStore } from "@/stores/chatStore";

type Outgoing = Omit<ChatRequest, "conversation_id">;

/** Sends a chat request and feeds the streamed events into the chat store. */
export function useChatStream() {
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(
    async (request: Outgoing, userText?: string) => {
      const store = useChatStore.getState();
      if (store.streaming) return;
      const controller = new AbortController();
      abortRef.current = controller;
      store.startTurn(userText);
      const conversationId = store.conversationId ?? undefined;
      try {
        await streamChat(
          { conversation_id: conversationId, ...request },
          (event) => useChatStore.getState().applyEvent(event),
          controller.signal,
        );
      } catch (error) {
        if (controller.signal.aborted) return;
        const data =
          error instanceof ApiError
            ? { message: error.message, reference: error.reference }
            : { message: "Could not reach the server. Check your connection and try again." };
        useChatStore.getState().applyEvent({ event: "error", data });
      } finally {
        useChatStore.getState().finishTurn();
        void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      }
    },
    [queryClient],
  );

  return { send };
}
