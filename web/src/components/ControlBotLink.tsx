import { useT } from "../i18n";

const BOT_URL = "tg://resolve?domain=hikkahost_bot";
const BOT_HANDLE = "@hikkahost_bot";
const CHAT_URL = "tg://resolve?domain=hikkahost_chat";
const CHAT_HANDLE = "@hikkahost_chat";

type Props = {
  className?: string;
  centered?: boolean;
};

export function ControlBotLink({ className = "", centered = false }: Props) {
  const { t } = useT();

  return (
    <div
      className={`text-sm text-theme-muted leading-relaxed flex flex-col gap-0.5 ${
        centered ? "items-center text-center max-w-sm" : ""
      } ${className}`}
    >
      <p>
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
      <p>
        {t("header.supportHint")}{" "}
        <a
          href={CHAT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="link-accent font-medium hover:underline"
        >
          {CHAT_HANDLE}
        </a>
      </p>
    </div>
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
