"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AppHeader } from "@/components/layout/AppHeader";
import { Workspace } from "@/components/workspace/Workspace";
import { ApiError, getMe } from "@/lib/api";
import { resetChatStore } from "@/stores/chatStore";

const isUnauthorised = (error: unknown) => error instanceof ApiError && error.status === 401;

export default function ChatPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });

  useEffect(() => {
    if (isUnauthorised(me.error)) router.replace("/login");
  }, [me.error, router]);

  function leave() {
    queryClient.clear();
    resetChatStore();
    router.replace("/login");
  }

  if (me.isError && !isUnauthorised(me.error)) {
    return (
      <main className="flex h-dvh flex-col items-center justify-center gap-3 px-4 text-center">
        <p className="text-sm">Couldn&apos;t load your session.</p>
        <button
          type="button"
          onClick={() => void me.refetch()}
          className="rounded-md border border-line px-3 py-1.5 text-sm font-medium hover:bg-sunken"
        >
          Try again
        </button>
      </main>
    );
  }

  if (!me.data) {
    return (
      <main className="flex h-dvh items-center justify-center">
        <p className="text-sm text-muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="flex h-dvh flex-col">
      <AppHeader user={me.data} onLoggedOut={leave} />
      <Workspace user={me.data} />
    </main>
  );
}
