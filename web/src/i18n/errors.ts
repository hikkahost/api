import type { Messages } from "./types";

export function mapApiError(code: string, t: (key: string) => string): string {
  const map: Record<string, keyof Messages["errors"]> = {
    csrf_init_failed: "csrfInit",
    csrf_invalid: "csrfInvalid",
    Forbidden: "csrfInvalid",
    "Unknown container": "unknownContainer",
    unknown_container: "unknownContainer",
    "Container header mismatch": "containerMismatch",
    container_header_mismatch: "containerMismatch",
    "Too many requests": "tooManyRequests",
    credentials_empty: "credentials_empty",
    "Provision already in progress": "provisionInProgress",
    request_failed: "requestFailed",
    bot_username_taken: "botUsernameTaken",
    bot_username_invalid_chars: "botUsernameInvalidChars",
    "Bot username required": "botUsernameFormat",
    "Bot username must end with 'bot'": "botUsernameFormat",
    "Invalid bot username format": "botUsernameFormat",
    "Invalid code": "verifyFailed",
    "Invalid 2FA password": "twofaFailed",
    "Invalid phone number": "sendFailed",
    "Not authenticated": "authFailed",
    "No active phone login": "authFailed",
    "No active QR login": "authFailed",
    "Session expired": "authFailed",
    account_not_found: "accountNotFound",
    delete_failed: "deleteFailed",
    server_error: "serverError",
    network_error: "networkError",
    internal_error: "serverError",
    credentials_apply_failed: "credentialsApplyFailed",
    provision_failed: "provisionFailed",
    "Provision failed": "provisionFailed",
  };
  const key = map[code];
  if (key) return t(`errors.${key}`);
  if (code.startsWith("Flood wait")) return code;
  return code || t("errors.generic");
}

const PAGE_REFRESH_ERRORS = new Set([
  "csrf_init_failed",
  "csrf_invalid",
  "Forbidden",
  "request_failed",
  "server_error",
  "network_error",
  "internal_error",
  "Unknown container",
  "unknown_container",
  "Container header mismatch",
  "container_header_mismatch",
]);

const NO_PAGE_REFRESH_ERRORS = new Set([
  "bot_username_taken",
  "bot_username_invalid_chars",
  "Bot username required",
  "Bot username must end with 'bot'",
  "Invalid bot username format",
  "Invalid code",
  "Invalid 2FA password",
  "Invalid phone number",
  "Not authenticated",
  "No active phone login",
  "No active QR login",
  "Session expired",
  "Too many requests",
  "credentials_empty",
  "Provision already in progress",
  "account_not_found",
  "delete_failed",
  "credentials_apply_failed",
  "provision_failed",
  "Provision failed",
]);

export function shouldOfferPageRefresh(error: string): boolean {
  if (NO_PAGE_REFRESH_ERRORS.has(error)) return false;
  if (error.startsWith("Flood wait")) return false;
  return PAGE_REFRESH_ERRORS.has(error);
}
