import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useT } from "../../i18n";
import { HeroCard } from "../HeroCard";
import { suggestBotUsername } from "../../utils/suggestBot";

type Props = {
  userbot: string;
  displayName: string;
  tgId: number | null;
  botUsername: string;
  finishing?: boolean;
  onBotChange: (v: string) => void;
  onBack: () => void;
  onFinish: () => void;
};

export function BotStep({
  userbot,
  displayName,
  tgId,
  botUsername,
  finishing = false,
  onBotChange,
  onBack,
  onFinish,
}: Props) {
  const { t } = useT();
  const [suggested, setSuggested] = useState("");

  const refreshSuggestion = () => {
    setSuggested(suggestBotUsername(userbot));
  };

  useEffect(() => {
    refreshSuggestion();
  }, [userbot]);

  const applySuggestion = () => {
    onBotChange(suggested);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <HeroCard
        badge={t("bot.badge")}
        title={t("bot.title")}
        titleAccent={t("bot.titleAccent")}
        description={t("bot.description")}
      />

      {displayName && (
        <p className="text-sm text-theme-muted">
          {t("bot.loggedInAs")}{" "}
          <span
            className="text-theme font-medium"
            dangerouslySetInnerHTML={{ __html: displayName }}
          />
        </p>
      )}

      <input
        className="input"
        placeholder={t("bot.placeholder")}
        value={botUsername}
        onChange={(e) => onBotChange(e.target.value)}
        autoComplete="off"
      />

      <div className="rounded-xl border border-theme px-4 py-3 space-y-2">
        <p className="text-xs text-theme-muted">{t("bot.suggestLabel")}</p>
        <p className="font-mono text-sm text-theme">@{suggested}</p>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-ghost flex-1 text-sm"
            onClick={refreshSuggestion}
          >
            {t("bot.suggestAnother")}
          </button>
          <button
            type="button"
            className="btn-ghost flex-1 text-sm"
            onClick={applySuggestion}
          >
            {t("bot.suggestUse")}
          </button>
        </div>
      </div>

      <div className="btn-stack pt-2">
        <button
          type="button"
          className="btn-primary"
          onClick={onFinish}
          disabled={finishing || !botUsername.trim()}
        >
          {finishing ? t("bot.finishing") : t("bot.finish")}
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={onBack}
          disabled={finishing}
        >
          {t("common.back")}
        </button>
      </div>
    </motion.div>
  );
}
