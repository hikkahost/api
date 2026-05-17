/** Bundled Apple-style emoji PNGs (served from /emoji/apple/, CSP-safe). */
const APPLE_EMOJI_BASE = "/emoji/apple";

export function appleEmojiUrl(code: string): string {
  return `${APPLE_EMOJI_BASE}/${code}.png`;
}

/** Map a grapheme cluster to hyphenated codepoint filename (e.g. "1f318", "1f468-200d-1f469"). */
export function emojiToCodepoints(emoji: string): string {
  const parts: string[] = [];
  for (const ch of emoji) {
    const cp = ch.codePointAt(0)!;
    if (cp === 0xfe0f) continue;
    parts.push(cp.toString(16));
  }
  return parts.join("-");
}

export function emojiToAppleUrl(emoji: string): string {
  return appleEmojiUrl(emojiToCodepoints(emoji));
}
