const ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789";

export function suggestBotUsername(userbotPrefix = "hikka"): string {
  const safe = userbotPrefix.toLowerCase().replace(/[^a-z0-9]/g, "") || "hikka";
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  const suffix = Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join("");
  return `${safe}_${suffix}_bot`;
}
