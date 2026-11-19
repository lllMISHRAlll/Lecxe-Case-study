"use client";

import { useRouter } from "next/navigation";
import { LoginForm } from "@/components/auth/LoginForm";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export default function LoginPage() {
  const router = useRouter();

  return (
    <main className="relative flex min-h-full items-center justify-center px-4 py-10">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="flex w-full max-w-xl flex-col gap-8 rounded-2xl border border-line bg-panel p-6 shadow-sm sm:p-10">
        <header className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-accent">
            Purchasing &amp; warehouse
          </p>
          <h1 className="text-2xl font-semibold text-balance">Procurement Assistant</h1>
          <p className="text-sm text-muted">
            Ask questions about vendors, purchase orders and stock, and raise purchase orders by
            chatting. Pick a demo role to sign in.
          </p>
        </header>
        <LoginForm onSuccess={() => router.push("/chat")} />
      </div>
    </main>
  );
}
