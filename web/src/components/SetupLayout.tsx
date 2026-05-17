import type { ReactNode } from "react";
import { useT, type Locale } from "../i18n";
import { useTheme } from "../theme/ThemeProvider";
import type { WizardStep } from "./StepProgress";
import { StepProgress } from "./StepProgress";
import { UserbotBadge } from "./UserbotBadge";
import { BrandFooter } from "./BrandFooter";
import { BetaBadge, ControlBotLink } from "./ControlBotLink";

type Props = {
  userbot: string;
  step: WizardStep;
  maxReached: WizardStep;
  onNavigate: (step: WizardStep) => void;
  children: ReactNode;
};

const LOCALES: Locale[] = ["en", "ru", "uk"];

function LangSwitcher({
  locale,
  setLocale,
}: {
  locale: Locale;
  setLocale: (l: Locale) => void;
}) {
  return (
    <div className="flex rounded-full border border-theme overflow-hidden text-[10px] font-medium shrink-0">
      {LOCALES.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLocale(l)}
          className={`px-2 py-1 uppercase transition ${
            locale === l ? "step-pill-active" : "step-pill-idle"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useT();
  const label = theme === "dark" ? t("common.themeLight") : t("common.themeDark");

  return (
    <button
      type="button"
      className="btn-icon"
      onClick={toggleTheme}
      title={label}
      aria-label={label}
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.75" />
          <path
            d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}

export function SetupLayout({
  userbot,
  step,
  maxReached,
  onNavigate,
  children,
}: Props) {
  const { t, locale, setLocale } = useT();

  return (
    <div className="app-shell">
      <header className="border-b border-theme px-4 sm:px-6 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <span className="text-[10px] uppercase tracking-widest text-theme-muted">
              {t("header.brand")}
            </span>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-base sm:text-lg font-semibold text-theme">
                {t("header.setup")}
              </h1>
              <UserbotBadge userbot={userbot} size="sm" />
              <BetaBadge />
            </div>
            <ControlBotLink className="mt-1 max-w-md" />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <ThemeToggle />
            <LangSwitcher locale={locale} setLocale={setLocale} />
          </div>
        </div>
      </header>

      {step !== "success" && (
        <div className="px-4 sm:px-6 py-3 border-b border-theme">
          <StepProgress
            current={step}
            maxReached={maxReached}
            onNavigate={onNavigate}
          />
        </div>
      )}

      <main className="flex-1 max-w-lg mx-auto w-full px-4 sm:px-6 py-8">
        {children}
      </main>

      <BrandFooter userbot={userbot} />
    </div>
  );
}
