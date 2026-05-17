import { useT } from "../i18n";

export type WizardStep = "home" | "credentials" | "login" | "bot" | "success";

const ORDER: WizardStep[] = [
  "home",
  "credentials",
  "login",
  "bot",
  "success",
];

const STEP_KEYS: Record<WizardStep, string> = {
  home: "steps.accounts",
  credentials: "steps.api",
  login: "steps.login",
  bot: "steps.bot",
  success: "steps.done",
};

type Props = {
  current: WizardStep;
  maxReached: WizardStep;
  onNavigate: (step: WizardStep) => void;
};

function stepIndex(step: WizardStep): number {
  return ORDER.indexOf(step);
}

export function StepProgress({ current, maxReached, onNavigate }: Props) {
  const { t } = useT();
  const maxIdx = stepIndex(maxReached);

  return (
    <nav className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
      {ORDER.map((id, idx) => {
        const active = id === current;
        const done = idx < stepIndex(current);
        const reachable = idx <= maxIdx && id !== "success";
        const isSuccess = id === "success";

        return (
          <button
            key={id}
            type="button"
            disabled={!reachable || isSuccess || active}
            onClick={() => reachable && onNavigate(id)}
            className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition border ${
              active
                ? "step-pill-active border-theme"
                : done
                  ? "text-theme-muted hover:text-theme border-transparent"
                  : reachable
                    ? "step-pill-idle border-transparent hover:border-theme"
                    : "step-pill-idle border-transparent cursor-default opacity-50"
            }`}
          >
            <span className="mr-1 opacity-50">{idx + 1}.</span>
            {t(STEP_KEYS[id])}
          </button>
        );
      })}
    </nav>
  );
}

export function maxStepReached(
  current: WizardStep,
  prev: WizardStep
): WizardStep {
  return stepIndex(current) > stepIndex(prev) ? current : prev;
}
