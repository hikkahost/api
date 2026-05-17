import { useState } from "react";
import { motion } from "framer-motion";
import {
  DEFAULT_API_HASH,
  DEFAULT_API_ID,
  isDefaultCredentials,
} from "../../api";
import { useT } from "../../i18n";
import { HeroCard } from "../HeroCard";

type Props = {
  apiId: string;
  apiHash: string;
  onApiIdChange: (v: string) => void;
  onApiHashChange: (v: string) => void;
  onBack: () => void;
  saving?: boolean;
  onContinue: () => Promise<boolean>;
};

export function CredentialsStep({
  apiId,
  apiHash,
  onApiIdChange,
  onApiHashChange,
  onBack,
  saving = false,
  onContinue,
}: Props) {
  const { t } = useT();
  const [showHelp, setShowHelp] = useState(false);
  const [showDefaultsConfirm, setShowDefaultsConfirm] = useState(false);
  const [confirmContinue, setConfirmContinue] = useState(false);
  const [defaultsAccepted, setDefaultsAccepted] = useState(false);
  const [localError, setLocalError] = useState("");

  const usingDefaults = isDefaultCredentials(apiId, apiHash);

  const applyDefaults = () => {
    onApiIdChange(String(DEFAULT_API_ID));
    onApiHashChange(DEFAULT_API_HASH);
    setShowDefaultsConfirm(false);
    setLocalError("");
  };

  const handleContinue = () => {
    setLocalError("");
    if (!apiId.trim() || !apiHash.trim()) {
      setLocalError(t("credentials.emptyError"));
      return;
    }
    if (usingDefaults && !defaultsAccepted) {
      setConfirmContinue(true);
      return;
    }
    void onContinue();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <HeroCard
        badge={t("credentials.badge")}
        title={t("credentials.title")}
        titleAccent={t("credentials.titleAccent")}
        description={t("credentials.description")}
      />

      <button
        type="button"
        className="text-sm link-accent underline"
        onClick={() => setShowHelp(!showHelp)}
      >
        {t("credentials.whatIsThis")}
      </button>
      {showHelp && (
        <p className="text-sm text-theme-muted card py-3 px-4">
          {t("credentials.whatIsThisBody")}
        </p>
      )}

      <a
        href="https://my.telegram.org"
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-theme-muted hover:opacity-80 block transition"
      >
        my.telegram.org →
      </a>

      {usingDefaults && !defaultsAccepted && !showDefaultsConfirm && !confirmContinue && (
        <p className="warning-banner text-sm">{t("credentials.defaultsWarning")}</p>
      )}

      {localError && <p className="text-sm" style={{ color: "rgb(var(--error-text))" }}>{localError}</p>}

      <label className="block text-sm text-theme-muted">{t("credentials.apiId")}</label>
      <input
        className="input"
        value={apiId}
        onChange={(e) => {
          onApiIdChange(e.target.value);
          setLocalError("");
          setConfirmContinue(false);
          setDefaultsAccepted(false);
        }}
        placeholder={t("credentials.apiIdPlaceholder")}
        inputMode="numeric"
        autoComplete="off"
      />
      <label className="block text-sm text-theme-muted">{t("credentials.apiHash")}</label>
      <input
        className="input font-mono text-sm"
        value={apiHash}
        onChange={(e) => {
          onApiHashChange(e.target.value);
          setLocalError("");
          setConfirmContinue(false);
          setDefaultsAccepted(false);
        }}
        placeholder={t("credentials.apiHashPlaceholder")}
        autoComplete="off"
      />

      {(showDefaultsConfirm || confirmContinue) && (
        <div className="warning-banner space-y-3">
          <p className="text-sm font-medium text-theme">
            {confirmContinue
              ? t("credentials.defaultsContinueTitle")
              : t("credentials.defaultsConfirmTitle")}
          </p>
          <p className="text-sm leading-relaxed">{t("credentials.defaultsConfirmBody")}</p>
          <div className="confirm-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                if (confirmContinue) {
                  setDefaultsAccepted(true);
                  setConfirmContinue(false);
                  void onContinue();
                } else {
                  applyDefaults();
                }
              }}
            >
              {confirmContinue
                ? t("credentials.defaultsAcceptContinue")
                : t("credentials.defaultsAccept")}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setShowDefaultsConfirm(false);
                setConfirmContinue(false);
                setDefaultsAccepted(false);
              }}
            >
              {t("credentials.defaultsCancel")}
            </button>
          </div>
        </div>
      )}

      <div className="pt-3 space-y-2">
        <div className="flex gap-2">
          <button type="button" className="btn-ghost flex-1 min-w-0 text-sm" onClick={onBack}>
            {t("common.back")}
          </button>
          <button
            type="button"
            className="btn-ghost flex-1 min-w-0 text-sm"
            onClick={() => setShowDefaultsConfirm(true)}
          >
            {t("credentials.useDefaults")}
          </button>
        </div>
        <button
          type="button"
          className="btn-primary w-full"
          onClick={handleContinue}
          disabled={saving}
        >
          {saving ? t("credentials.saving") : t("credentials.continue")}
        </button>
      </div>
    </motion.div>
  );
}
