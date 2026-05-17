import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { ApiError, initCsrf } from "./api";
import { I18nProvider, useT } from "./i18n";
import { mapApiError } from "./i18n/errors";
import { applyDocumentLang, detectLocale } from "./i18n/locale";
import { ThemeProvider } from "./theme/ThemeProvider";

applyDocumentLang(detectLocale());

function Bootstrap() {
  const { t } = useT();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setError("");
    initCsrf()
      .then(() => setReady(true))
      .catch((e) => {
        setReady(false);
        const code = e instanceof ApiError ? e.code : "csrf_init_failed";
        setError(
          e instanceof ApiError ? mapApiError(code, t) : t("errors.csrfInit")
        );
      });
  };

  useEffect(() => {
    load();
  }, []);

  if (!ready) {
    return (
      <div className="app-shell flex items-center justify-center">
        <div className="text-center space-y-4 px-6">
          {error ? (
            <>
              <p className="text-sm max-w-sm" style={{ color: "rgb(var(--error-text))" }}>
                {error}
              </p>
              <button type="button" className="btn-primary" onClick={load}>
                {t("common.refresh")}
              </button>
            </>
          ) : (
            <p className="text-theme-muted text-sm">{t("common.loading")}</p>
          )}
        </div>
      </div>
    );
  }

  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <I18nProvider>
        <Bootstrap />
      </I18nProvider>
    </ThemeProvider>
  </React.StrictMode>
);
