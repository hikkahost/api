import { AppleEmoji } from "./AppleEmoji";
import { userbotBrand } from "../lib/userbots";

type Variant = "userbot" | "host";

type Props = {
  userbot: string;
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  className?: string;
};

export function UserbotBadge({ userbot, variant = "userbot", size = "md", className = "" }: Props) {
  if (variant === "host") {
    return <HikkaHostBadge size={size} className={className} />;
  }

  const brand = userbotBrand(userbot);
  const sizeClass =
    size === "lg"
      ? "badge-pill badge-pill-lg"
      : size === "sm"
        ? "badge-pill badge-pill-sm"
        : "badge-pill";

  return (
    <span className={`${sizeClass} badge-userbot ${className}`.trim()}>
      <span className="badge-inner">
        <span className="badge-emoji" aria-hidden>
          <AppleEmoji emoji={brand.emoji} size={size === "lg" ? 22 : size === "sm" ? 18 : 20} />
        </span>
        <span className="font-movement badge-label">{brand.label}</span>
      </span>
    </span>
  );
}

export function HikkaHostBadge({
  size = "md",
  className = "",
}: {
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizeClass =
    size === "lg"
      ? "badge-pill badge-pill-lg"
      : size === "sm"
        ? "badge-pill badge-pill-sm"
        : "badge-pill";

  return (
    <span className={`${sizeClass} badge-host ${className}`.trim()}>
      <span className="badge-inner">
        <span className="badge-emoji badge-emoji-ring" aria-hidden>
          <AppleEmoji emoji="🌘" size={size === "lg" ? 20 : size === "sm" ? 16 : 18} />
        </span>
        <span className="font-movement badge-label-host">HikkaHost</span>
      </span>
    </span>
  );
}
