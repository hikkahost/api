export type Locale = "en" | "ru" | "uk";

const STORAGE_KEY = "setup_locale";

export function detectLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "en" || saved === "ru" || saved === "uk") return saved;
  const langs = navigator.languages?.length
    ? navigator.languages
    : [navigator.language];
  for (const lang of langs) {
    const l = lang.toLowerCase();
    if (l.startsWith("uk") || l.startsWith("ua")) return "uk";
    if (l.startsWith("ru")) return "ru";
  }
  return "en";
}

export function saveLocale(locale: Locale): void {
  localStorage.setItem(STORAGE_KEY, locale);
}

export function applyDocumentLang(locale: Locale): void {
  document.documentElement.lang =
    locale === "uk" ? "uk" : locale === "ru" ? "ru" : "en";
}
