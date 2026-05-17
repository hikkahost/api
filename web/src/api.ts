let csrfToken = "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const FETCH_OPTS: RequestInit = { credentials: "include" };

export async function initCsrf(): Promise<void> {
  const res = await fetch("/setup/csrf", FETCH_OPTS);
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await res.json().catch(() => ({}))
    : {};
  if (!res.ok || !data.csrf) {
    throw new ApiError(
      data.error || `Failed to initialize session (${res.status})`,
      data.error || "csrf_init_failed",
      res.status
    );
  }
  csrfToken = data.csrf;
}

function isCsrfError(status: number, code: string): boolean {
  return (
    status === 403 &&
    (code === "csrf_invalid" || code === "Forbidden")
  );
}

async function parseResponseBody(
  res: Response
): Promise<Record<string, unknown>> {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await res.json().catch(() => ({}))) as Record<string, unknown>;
  }
  const text = (await res.text().catch(() => "")).trim();
  if (text.includes("Internal error") || text.includes("internal")) {
    return { error: "internal_error" };
  }
  if (text) {
    return { error: "request_failed", detail: text.slice(0, 200) };
  }
  return {};
}

function errorCode(data: Record<string, unknown>, status: number): string {
  const code = String(data.error || "");
  if (code) return code;
  if (status >= 500) return "server_error";
  if (status === 429) return "Too many requests";
  return "request_failed";
}

async function api<T>(
  path: string,
  options: RequestInit = {},
  retried = false
): Promise<T> {
  const method = options.method || "GET";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (csrfToken && method !== "GET") {
    headers["X-CSRF-Token"] = csrfToken;
  }

  let res: Response;
  try {
    res = await fetch(path, {
      ...FETCH_OPTS,
      ...options,
      headers,
    });
  } catch {
    throw new ApiError("Network error", "network_error", 0);
  }

  const data = await parseResponseBody(res);
  const code = errorCode(data, res.status);

  if (!res.ok) {
    if (!retried && isCsrfError(res.status, code)) {
      await initCsrf();
      return api<T>(path, options, true);
    }
    throw new ApiError(
      code || `Request failed (${res.status})`,
      code,
      res.status
    );
  }
  return data as T;
}

export type Account = { tg_id: number; bot_username?: string | null };

export type AccountsResponse = {
  accounts: Account[];
  userbot: string;
  credentials: { api_id: number; api_hash_set: boolean };
};

export const setupApi = {
  accounts: () => api<AccountsResponse>("/setup/accounts"),
  deleteAccount: (tg_id: number) =>
    api<{ ok: boolean; tg_id: number }>("/setup/accounts/delete", {
      method: "POST",
      body: JSON.stringify({ tg_id }),
    }),
  credentials: (api_id: number, api_hash: string) =>
    api("/setup/credentials", {
      method: "PUT",
      body: JSON.stringify({ api_id, api_hash }),
    }),
  authMode: (mode: "phone" | "qr") =>
    api("/setup/auth/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  phoneSend: (phone: string) =>
    api("/setup/phone/send", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),
  phoneVerify: (code: string, password?: string) =>
    api<{
      tg_id?: number;
      needs_2fa?: boolean;
      display_name?: string;
      username?: string;
      first_name?: string;
    }>(
      "/setup/phone/verify",
      {
        method: "POST",
        body: JSON.stringify({ code, password }),
      }
    ),
  qrInit: () =>
    api<{ qr_image: string; qr_url: string; qr_logo_ratio?: number }>("/setup/qr/init", {
      method: "POST",
      body: "{}",
    }),
  qrPoll: () =>
    api<{
      status: string;
      tg_id?: number;
      display_name?: string;
      username?: string;
      first_name?: string;
    }>("/setup/qr/poll"),
  qr2fa: (password: string) =>
    api<{ tg_id: number; display_name?: string }>("/setup/qr/2fa", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  botCheck: (username: string, tgId?: number | null) =>
    api("/setup/bot/check", {
      method: "POST",
      body: JSON.stringify({
        username,
        ...(tgId != null ? { tg_id: tgId } : {}),
      }),
    }),
  finish: (bot_username: string) =>
    api<{ ok: boolean; tg_id: number }>("/setup/finish", {
      method: "POST",
      body: JSON.stringify({ bot_username }),
    }),
};

export const DEFAULT_API_ID = 2040;
export const DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627";

export function isDefaultCredentials(apiId: string, apiHash: string): boolean {
  const id = Number.parseInt(apiId.trim(), 10);
  return (
    id === DEFAULT_API_ID &&
    apiHash.trim().toLowerCase() === DEFAULT_API_HASH.toLowerCase()
  );
}
