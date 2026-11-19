"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, getDemoUsers, login } from "@/lib/api";
import type { DemoUser, User } from "@/lib/types";

interface LoginFormProps {
  onSuccess: (user: User) => void;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Could not reach the server. Check your connection and try again.";
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const demoUsers = useQuery({ queryKey: ["demo-users"], queryFn: getDemoUsers });
  const signIn = useMutation({
    mutationFn: () => login(email, password),
    onSuccess,
  });

  function fill(demo: DemoUser) {
    setEmail(demo.email);
    setPassword(demo.password ?? "");
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    signIn.mutate();
  }

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="quick-login" className="flex flex-col gap-3">
        <h2 id="quick-login" className="text-xs font-semibold uppercase tracking-wider text-muted">
          Quick login
        </h2>
        {demoUsers.isError ? (
          <p className="text-sm text-muted">Quick login is unavailable. Type your details below.</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-3">
            {(demoUsers.data ?? []).map((demo) => (
              <button
                key={demo.email}
                type="button"
                aria-label={`Log in as ${demo.name}, ${demo.role_label}`}
                onClick={() => fill(demo)}
                className="flex flex-col items-start gap-0.5 rounded-lg border border-line bg-panel px-3 py-2.5 text-left transition hover:border-accent hover:bg-accent-soft"
              >
                <span className="text-sm font-semibold">{demo.name}</span>
                <span className="text-xs text-muted">{demo.role_label}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Email
          <input
            id="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-line bg-panel px-3 py-2 font-normal outline-none focus:border-accent"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Password
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-line bg-panel px-3 py-2 font-normal outline-none focus:border-accent"
          />
        </label>
        {signIn.isError && (
          <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
            {errorMessage(signIn.error)}
          </p>
        )}
        <button
          type="submit"
          disabled={signIn.isPending}
          className="rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60"
        >
          {signIn.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
