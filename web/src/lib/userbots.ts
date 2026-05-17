export type UserbotKey = "hikka" | "heroku" | "legacy" | "geektg";

export type UserbotBrand = {
  key: UserbotKey;
  emoji: string;
  label: string;
  name: string;
};

const BRANDS: Record<UserbotKey, UserbotBrand> = {
  hikka: { key: "hikka", emoji: "🌘", label: "HIKKA", name: "Hikka" },
  heroku: { key: "heroku", emoji: "🪐", label: "HEROKU", name: "Heroku" },
  legacy: { key: "legacy", emoji: "🌙", label: "LEGACY", name: "Legacy" },
  geektg: { key: "geektg", emoji: "🤖", label: "GEEK TG", name: "Geek TG" },
};

export function userbotBrand(raw: string): UserbotBrand {
  const key = raw.toLowerCase().replace(/[^a-z]/g, "") as UserbotKey;
  if (key in BRANDS) return BRANDS[key as UserbotKey];
  if (raw.toLowerCase().includes("geek")) return BRANDS.geektg;
  if (raw.toLowerCase().includes("heroku")) return BRANDS.heroku;
  if (raw.toLowerCase().includes("legacy")) return BRANDS.legacy;
  return BRANDS.hikka;
}
