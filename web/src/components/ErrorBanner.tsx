import { useT } from "../i18n";
import { mapApiError, shouldOfferPageRefresh } from "../i18n/errors";

type Props = {
  error: string;
};

export function ErrorBanner({ error }: Props) {
  const { t } = useT();
  const message = mapApiError(error, t);

  return (
    <div className="error-banner">
      <p className="text-sm">{message}</p>
      {shouldOfferPageRefresh(error) && (
        <button
          type="button"
          className="btn-ghost text-sm py-2"
          onClick={() => window.location.reload()}
        >
          {t("common.refresh")}
        </button>
      )}
    </div>
  );
}
