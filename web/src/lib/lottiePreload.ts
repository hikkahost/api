import type { LottieComponentProps } from "lottie-react";

export type LottieData = LottieComponentProps["animationData"];
type LottieModule = typeof import("lottie-react");

const animationCache = new Map<string, Promise<LottieData>>();
let lottieModule: Promise<LottieModule> | null = null;

function loadAnimation(name: string): Promise<LottieData> {
  let pending = animationCache.get(name);
  if (!pending) {
    pending = fetch(`/lottie/${name}.json`)
      .then((r) => {
        if (!r.ok) throw new Error("lottie_load_failed");
        return r.json() as Promise<LottieData>;
      })
      .catch((err) => {
        animationCache.delete(name);
        throw err;
      });
    animationCache.set(name, pending);
  }
  return pending;
}

function loadLottieModule(): Promise<LottieModule> {
  if (!lottieModule) {
    lottieModule = import("lottie-react");
  }
  return lottieModule;
}

/** Start loading lottie-react + JSON (call when QR tab opens). */
export function preloadLottieSticker(name: string): void {
  void loadLottieModule();
  void loadAnimation(name);
}

/** Returns renderer + animation data (uses preload cache when ready). */
export function loadLottieSticker(name: string): Promise<{
  Lottie: LottieModule["default"];
  data: LottieData;
}> {
  return Promise.all([loadLottieModule(), loadAnimation(name)]).then(([mod, data]) => ({
    Lottie: mod.default,
    data,
  }));
}
