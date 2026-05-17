import { useState } from "react";
import { emojiToAppleUrl } from "../lib/appleEmoji";

type Props = {
  emoji: string;
  size?: number;
  className?: string;
  alt?: string;
};

export function AppleEmoji({ emoji, size = 20, className = "", alt = "" }: Props) {
  const [failed, setFailed] = useState(false);
  const src = emojiToAppleUrl(emoji);

  if (failed) {
    return (
      <span
        className={`apple-emoji-fallback ${className}`.trim()}
        style={{ fontSize: size, lineHeight: 1 }}
        aria-hidden={!alt}
      >
        {emoji}
      </span>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      className={`apple-emoji-img ${className}`.trim()}
      draggable={false}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}
