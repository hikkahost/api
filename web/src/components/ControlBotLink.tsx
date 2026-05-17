import { useT } from "../i18n";

const BOT_URL = "tg://resolve?domain=hikkahost_bot";
const BOT_HANDLE = "@hikkahost_bot";

type Props = {
  className?: string;
  centered?: boolean;
};

export function ControlBotLink({ className = "", centered = false }: Props) {
  const { t } = useT();

  return (
    <p
      className={`text-sm text-theme-muted leading-relaxed ${
        centered ? "text-center max-w-xs" : ""
      } ${className}`}
    >
      {t("header.controlBot")}{" "}
      <a
        href={BOT_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="link-accent font-medium hover:underline"
      >
        {BOT_HANDLE}
      </a>
    </p>
  );
}

export function BetaBadge() {
  const { t } = useT();

  return (
    <span className="badge-beta" title={t("header.betaHint")}>
      {t("header.beta")}
    </span>
  );
}
