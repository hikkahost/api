import { useEffect, useState } from "react";
import { AppleEmoji } from "./AppleEmoji";
import { loadLottieSticker, type LottieData } from "../lib/lottiePreload";

type LottieComponent = typeof import("lottie-react")["default"];

type Props = {
  name: string;
  size?: number;
  className?: string;
  fallbackEmoji?: string;
};

export { preloadLottieSticker } from "../lib/lottiePreload";

export function LottieSticker({
  name,
  size = 52,
  className = "",
  fallbackEmoji = "🌘",
}: Props) {
  const [Lottie, setLottie] = useState<LottieComponent | null>(null);
  const [data, setData] = useState<LottieData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadLottieSticker(name)
      .then(({ Lottie: LottieComp, data: json }) => {
        if (cancelled) return;
        setLottie(() => LottieComp);
        setData(json);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (failed) {
    return <AppleEmoji emoji={fallbackEmoji} size={size} className={className} />;
  }

  const dim =
    size != null
      ? { width: size, height: size }
      : { width: "100%", height: "100%" };

  if (!Lottie || !data) {
    return (
      <span
        className={`lottie-sticker-placeholder ${className}`.trim()}
        style={dim}
        aria-hidden
      />
    );
  }

  return (
    <Lottie
      className={`lottie-sticker ${className}`.trim()}
      animationData={data}
      loop
      autoplay
      style={dim}
      rendererSettings={{ preserveAspectRatio: "xMidYMid meet" }}
    />
  );
}
