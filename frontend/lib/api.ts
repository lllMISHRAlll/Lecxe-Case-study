import type {
  ApiErrorBody,
  CannedQuery,
  ConversationDetail,
  ConversationSummary,
  DemoUser,
  User,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly reference?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const GENERIC_MESSAGE = "Something went wrong. Please try again.";
const RATE_LIMIT_MESSAGE = "Too many requests. Please wait a moment and try again.";

/** Resolves an API path against the current origin, so it works in the browser and in tests. */
export function apiUrl(path: string): string {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  return new URL(path, origin).toString();
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    body = undefined;
  }
  if (body?.error?.message) {
    return new ApiError(response.status, body.error.code, body.error.message, body.error.reference);
  }
  const message = response.status === 429 ? RATE_LIMIT_MESSAGE : GENERIC_MESSAGE;
  return new ApiError(response.status, "http_error", message);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    credentials: "same-origin",
    ...init,
    headers: init.body ? { "Content-Type": "application/json", ...init.headers } : init.headers,
  });
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const getDemoUsers = () => request<DemoUser[]>("/api/auth/demo-users");

export const login = async (email: string, password: string) =>
  (await post<{ user: User }>("/api/auth/login", { email, password })).user;

export const getMe = async () => (await request<{ user: User }>("/api/auth/me")).user;

export const logout = () => post<void>("/api/auth/logout");

export const getCanned = () => request<CannedQuery[]>("/api/canned");

export const listConversations = () => request<ConversationSummary[]>("/api/conversations");

export const getConversation = (id: string) =>
  request<ConversationDetail>(`/api/conversations/${encodeURIComponent(id)}`);

export const deleteConversation = (id: string) =>
  request<void>(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });

export const sendFeedback = (messageId: string, score: 1 | -1) =>
  post<void>("/api/feedback", { message_id: messageId, score });
