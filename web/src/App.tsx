import { useCallback, useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { setupApi, ApiError, type Account } from "./api";
import { SetupLayout } from "./components/SetupLayout";
import { preloadLottieSticker } from "./lib/lottiePreload";
import { ErrorBanner } from "./components/ErrorBanner";
import type { WizardStep } from "./components/StepProgress";
import { maxStepReached } from "./components/StepProgress";
import { HomeStep } from "./components/steps/HomeStep";
import { CredentialsStep } from "./components/steps/CredentialsStep";
import { LoginStep } from "./components/steps/LoginStep";
import { BotStep } from "./components/steps/BotStep";
import { SuccessStep } from "./components/steps/SuccessStep";
import { useT } from "./i18n";

function parseError(e: unknown, t: (key: string) => string): string {
  if (e instanceof ApiError) return e.code;
  if (e instanceof Error) return e.message;
  return t("errors.generic");
}

export default function App() {
  const { t } = useT();
  const [step, setStep] = useState<WizardStep>("home");
  const [maxReached, setMaxReached] = useState<WizardStep>("home");
  const [userbot, setUserbot] = useState("hikka");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [credentialsSaving, setCredentialsSaving] = useState(false);
  const [defaults, setDefaults] = useState<{
    api_id: number;
    api_hash: string;
  } | null>(null);

  const [authTab, setAuthTab] = useState<"phone" | "qr">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password2fa, setPassword2fa] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);
  const [qrImage, setQrImage] = useState("");
  const [qrLogoRatio, setQrLogoRatio] = useState(0.26);
  const [qrLoading, setQrLoading] = useState(false);
  const [botUsername, setBotUsername] = useState("");
  const [tgId, setTgId] = useState<number | null>(null);
  const [userDisplay, setUserDisplay] = useState("");
  const [finishing, setFinishing] = useState(false);

  const applyAuthProfile = (res: {
    tg_id?: number;
    display_name?: string;
    first_name?: string;
    username?: string;
  }) => {
    if (res.tg_id) setTgId(res.tg_id);
    const name = res.first_name?.trim();
    const user = res.username?.trim();
    if (name && user) {
      setUserDisplay(`${name} (@${user})`);
    } else if (res.display_name) {
      setUserDisplay(res.display_name);
    } else if (name) {
      setUserDisplay(name);
    } else if (user) {
      setUserDisplay(`@${user}`);
    }
  };

  const goTo = useCallback((next: WizardStep) => {
    setStep(next);
    setMaxReached((prev) => maxStepReached(next, prev));
  }, []);

  const loadAccounts = useCallback(async () => {
    const data = await setupApi.accounts();
    setAccounts(data.accounts);
    setUserbot(data.userbot);
    setDefaults(data.defaults);
    if (data.credentials.api_hash_set && data.credentials.api_id) {
      setApiId(String(data.credentials.api_id));
    }
  }, []);

  const refresh = useCallback(
    async (opts?: { silent?: boolean; retries?: number }) => {
      const silent = opts?.silent ?? false;
      const retries = opts?.retries ?? 1;
      if (!silent) setLoading(true);
      if (!silent) setError("");

      let lastError: unknown;
      try {
        for (let attempt = 0; attempt < retries; attempt++) {
          try {
            await loadAccounts();
            return true;
          } catch (e) {
            lastError = e;
            if (attempt < retries - 1) {
              await new Promise((r) => setTimeout(r, 2000));
            }
          }
        }
        if (!silent && lastError) {
          setError(parseError(lastError, t));
        }
        return false;
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [loadAccounts, t]
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveCredentials = async (): Promise<boolean> => {
    setError("");
    const id = Number.parseInt(apiId.trim(), 10);
    if (!Number.isFinite(id) || !apiHash.trim()) {
      setError("credentials_empty");
      return false;
    }
    setCredentialsSaving(true);
    try {
      await setupApi.credentials(id, apiHash.trim());
      goTo("login");
      return true;
    } catch (e) {
      setError(parseError(e, t));
      return false;
    } finally {
      setCredentialsSaving(false);
    }
  };

  const loadQr = useCallback(async () => {
    setQrLoading(true);
    setError("");
    preloadLottieSticker("AnimatedMoon");
    try {
      await setupApi.authMode("qr");
      const qr = await setupApi.qrInit();
      setQrImage(qr.qr_image);
      setQrLogoRatio(qr.qr_logo_ratio ?? 0.26);
    } catch (e) {
      setQrImage("");
      setQrLogoRatio(0.26);
      setError(parseError(e, t));
    } finally {
      setQrLoading(false);
    }
  }, [t]);

  const switchTab = async (tab: "phone" | "qr") => {
    setAuthTab(tab);
    setError("");
    setNeeds2fa(false);
    if (tab === "phone") {
      setQrImage("");
      setQrLoading(false);
      try {
        await setupApi.authMode("phone");
      } catch (e) {
        setError(parseError(e, t));
      }
      return;
    }
    setQrImage("");
    setQrLoading(true);
    await loadQr();
  };

  useEffect(() => {
    if (step !== "login" || authTab !== "qr" || !qrImage) return;
    const id = setInterval(async () => {
      try {
        const res = await setupApi.qrPoll();
        if (res.status === "needs_2fa") {
          setNeeds2fa(true);
          return;
        }
        if (res.status === "authorized" && res.tg_id) {
          applyAuthProfile(res);
          goTo("bot");
        }
      } catch {
        /* polling */
      }
    }, 2000);
    return () => clearInterval(id);
  }, [step, authTab, qrImage, goTo]);

  const sendPhone = async (): Promise<boolean> => {
    setError("");
    try {
      await setupApi.phoneSend(phone);
      return true;
    } catch (e) {
      setError(parseError(e, t));
      return false;
    }
  };

  const verifyPhone = async () => {
    setError("");
    try {
      const res = await setupApi.phoneVerify(code, password2fa || undefined);
      if (res.needs_2fa) {
        setNeeds2fa(true);
        return;
      }
      if (res.tg_id) {
        applyAuthProfile(res);
        goTo("bot");
      }
    } catch (e) {
      setError(parseError(e, t));
    }
  };

  const submit2fa = async () => {
    setError("");
    try {
      const res =
        authTab === "qr"
          ? await setupApi.qr2fa(password2fa)
          : await setupApi.phoneVerify(code, password2fa);
      if (res.tg_id) {
        applyAuthProfile(res);
        goTo("bot");
      }
    } catch (e) {
      setError(parseError(e, t));
    }
  };

  const finish = async () => {
    setError("");
    setFinishing(true);
    try {
      await setupApi.botCheck(botUsername, tgId);
      await setupApi.finish(botUsername);
      setError("");
      await refresh({ silent: true, retries: 6 });
      goTo("success");
    } catch (e) {
      setError(parseError(e, t));
    } finally {
      setFinishing(false);
    }
  };

  const resetSession = () => {
    setStep("home");
    setTgId(null);
    setUserDisplay("");
    setBotUsername("");
    setCode("");
    setNeeds2fa(false);
    setQrImage("");
    setQrLoading(false);
    setMaxReached("home");
    void refresh({ silent: true, retries: 5 });
  };

  const navigate = (target: WizardStep) => {
    if (target === "success") return;
    goTo(target);
  };

  return (
    <SetupLayout
      userbot={userbot}
      step={step}
      maxReached={maxReached}
      onNavigate={navigate}
    >
      {error && step !== "success" && (
        <ErrorBanner error={error} />
      )}

      <AnimatePresence mode="wait">
        {step === "home" && (
          <HomeStep
            key="home"
            loading={loading}
            accounts={accounts}
            onAdd={() => goTo("credentials")}
            onChangeApi={() => goTo("credentials")}
            onDelete={async (tgId) => {
              setError("");
              try {
                await setupApi.deleteAccount(tgId);
                await refresh({ silent: true });
              } catch (e) {
                setError(parseError(e, t));
                throw e;
              }
            }}
          />
        )}
        {step === "credentials" && (
          <CredentialsStep
            key="credentials"
            apiId={apiId}
            apiHash={apiHash}
            defaults={defaults}
            onApiIdChange={setApiId}
            onApiHashChange={setApiHash}
            onBack={() => goTo("home")}
            saving={credentialsSaving}
            onContinue={saveCredentials}
          />
        )}
        {step === "login" && (
          <LoginStep
            key="login"
            authTab={authTab}
            phone={phone}
            code={code}
            password2fa={password2fa}
            needs2fa={needs2fa}
            qrImage={qrImage}
            qrLogoRatio={qrLogoRatio}
            qrLoading={qrLoading}
            onTabChange={switchTab}
            onPhoneChange={setPhone}
            onCodeChange={setCode}
            onPasswordChange={setPassword2fa}
            onBack={() => goTo("credentials")}
            onChangeApi={() => goTo("credentials")}
            onSendPhone={sendPhone}
            onVerifyPhone={verifyPhone}
            onSubmit2fa={submit2fa}
            onRefreshQr={() => switchTab("qr")}
          />
        )}
        {step === "bot" && (
          <BotStep
            key="bot"
            userbot={userbot}
            displayName={userDisplay}
            tgId={tgId}
            botUsername={botUsername}
            finishing={finishing}
            onBotChange={setBotUsername}
            onBack={() => goTo("login")}
            onFinish={finish}
          />
        )}
        {step === "success" && (
          <SuccessStep key="success" onBackHome={resetSession} />
        )}
      </AnimatePresence>
    </SetupLayout>
  );
}
