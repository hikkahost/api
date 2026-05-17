import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useT } from "../../i18n";
import { LottieSticker } from "../LottieSticker";
import { HeroCard } from "../HeroCard";

const SEND_CODE_COOLDOWN_SEC = 30;

type Props = {
  authTab: "phone" | "qr";
  phone: string;
  code: string;
  password2fa: string;
  needs2fa: boolean;
  qrImage: string;
  qrLogoRatio: number;
  qrLoading: boolean;
  onTabChange: (tab: "phone" | "qr") => void;
  onPhoneChange: (v: string) => void;
  onCodeChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onBack: () => void;
  onChangeApi: () => void;
  onSendPhone: () => Promise<boolean>;
  onVerifyPhone: () => void;
  onSubmit2fa: () => void;
  onRefreshQr: () => void;
};

export function LoginStep({
  authTab,
  phone,
  code,
  password2fa,
  needs2fa,
  qrImage,
  qrLogoRatio,
  qrLoading,
  onTabChange,
  onPhoneChange,
  onCodeChange,
  onPasswordChange,
  onBack,
  onChangeApi,
  onSendPhone,
  onVerifyPhone,
  onSubmit2fa,
  onRefreshQr,
}: Props) {
  const { t } = useT();
  const [sendingCode, setSendingCode] = useState(false);
  const [codeCooldown, setCodeCooldown] = useState(0);
  const [codeSent, setCodeSent] = useState(false);

  useEffect(() => {
    if (codeCooldown <= 0) return;
    const id = window.setInterval(() => {
      setCodeCooldown((s) => (s <= 1 ? 0 : s - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [codeCooldown]);

  const sendCodeDisabled =
    sendingCode || codeCooldown > 0 || !phone.trim();

  const handleSendCode = async () => {
    if (sendCodeDisabled) return;
    setSendingCode(true);
    setCodeSent(false);
    try {
      const ok = await onSendPhone();
      if (ok) {
        setCodeCooldown(SEND_CODE_COOLDOWN_SEC);
        setCodeSent(true);
      }
    } finally {
      setSendingCode(false);
    }
  };

  const sendCodeLabel = () => {
    if (sendingCode) return t("login.sendCodeSending");
    if (codeCooldown > 0) return `${t("login.sendCodeWait")} ${codeCooldown} ${t("login.sendCodeSeconds")}`;
    if (codeSent) return t("login.sendCodeSent");
    return t("login.sendCode");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <HeroCard
        badge={t("login.badge")}
        title={t("login.title")}
        titleAccent={t("login.titleAccent")}
        description={t("login.description")}
      />

      <div className="flex gap-2">
        <button
          type="button"
          className={`flex-1 py-2.5 rounded-full text-sm font-medium transition ${
            authTab === "phone" ? "tab-active" : "tab-inactive"
          }`}
          onClick={() => onTabChange("phone")}
        >
          {t("login.phone")}
        </button>
        <button
          type="button"
          className={`flex-1 py-2.5 rounded-full text-sm font-medium transition ${
            authTab === "qr" ? "tab-active" : "tab-inactive"
          }`}
          onClick={() => onTabChange("qr")}
        >
          {t("login.qr")}
        </button>
      </div>

      <div className="flex gap-3 text-sm">
        <button
          type="button"
          className="text-theme-muted hover:opacity-80"
          onClick={onBack}
        >
          ← {t("common.back")}
        </button>
        <button
          type="button"
          className="text-theme-muted hover:opacity-80 underline"
          onClick={onChangeApi}
        >
          {t("login.changeApi")}
        </button>
      </div>

      {authTab === "phone" && !needs2fa && (
        <>
          <input
            className="input"
            placeholder={t("login.phonePlaceholder")}
            value={phone}
            onChange={(e) => onPhoneChange(e.target.value)}
          />
          <button
            type="button"
            className="btn-send-code"
            onClick={handleSendCode}
            disabled={sendCodeDisabled}
          >
            {sendCodeLabel()}
          </button>
          {codeSent && codeCooldown > 0 && (
            <p className="text-xs text-theme-muted text-center -mt-2">
              {t("login.sendCodeHint")}
            </p>
          )}
          <input
            className="input"
            placeholder={t("login.codePlaceholder")}
            value={code}
            onChange={(e) => onCodeChange(e.target.value)}
          />
          <button type="button" className="btn-primary w-full" onClick={onVerifyPhone}>
            {t("login.verify")}
          </button>
        </>
      )}

      {authTab === "qr" && !needs2fa && (
        <div className="card flex flex-col items-center gap-4">
          {qrLoading || qrImage ? (
            <motion.div
              className="qr-frame"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="qr-canvas">
                {qrImage ? (
                  <>
                    <img src={qrImage} alt="" className="qr-image" />
                    <div
                      className="qr-sticker-overlay"
                      style={{
                        width: `${qrLogoRatio * 100}%`,
                        height: `${qrLogoRatio * 100}%`,
                      }}
                    >
                      <div className="qr-sticker">
                        <LottieSticker name="AnimatedMoon" />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="qr-loading" aria-live="polite">
                    <span className="qr-loading-spinner" aria-hidden />
                    <span>{t("common.loading")}</span>
                  </div>
                )}
              </div>
            </motion.div>
          ) : null}
          <p className="text-sm text-theme-muted text-center">{t("login.qrHint")}</p>
          <button
            type="button"
            className="btn-ghost text-sm"
            onClick={onRefreshQr}
            disabled={qrLoading}
          >
            {t("login.refreshQr")}
          </button>
        </div>
      )}

      {needs2fa && (
        <>
          <p className="text-sm text-theme-muted">{t("login.password2fa")}</p>
          <input
            className="input"
            type="password"
            value={password2fa}
            onChange={(e) => onPasswordChange(e.target.value)}
          />
          <button type="button" className="btn-primary w-full" onClick={onSubmit2fa}>
            {t("login.submit2fa")}
          </button>
        </>
      )}
    </motion.div>
  );
}
