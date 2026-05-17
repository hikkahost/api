import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import en from "../locales/en.json";
import ru from "../locales/ru.json";
import uk from "../locales/uk.json";
import type { Messages } from "./types";
import {
  applyDocumentLang,
  detectLocale,
  saveLocale,
  type Locale,
} from "./locale";

const catalogs: Record<Locale, Messages> = { en, ru, uk };

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
  messages: Messages;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function getNested(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return path;
    cur = (cur as Record<string, unknown>)[p];
  }
  return typeof cur === "string" ? cur : path;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale);

  const setLocale = useCallback((next: Locale) => {
    saveLocale(next);
    applyDocumentLang(next);
    setLocaleState(next);
  }, []);

  const messages = catalogs[locale];

  const t = useCallback(
    (key: string) => getNested(messages as unknown as Record<string, unknown>, key),
    [messages]
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, messages }),
    [locale, setLocale, t, messages]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useT must be used within I18nProvider");
  return ctx;
}

export { detectLocale, applyDocumentLang, type Locale, type Messages };
