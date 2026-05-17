import { motion } from "framer-motion";
import { useT } from "../../i18n";

type Props = {
  onBackHome: () => void;
};

export function SuccessStep({ onBackHome }: Props) {
  const { t } = useT();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="card success-card text-center space-y-4"
    >
      <div
        className="success-icon mx-auto"
        aria-hidden
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path
            d="M20 6L9 17l-5-5"
            stroke="currentColor"
            strokeWidth="2.25"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-semibold text-theme">{t("success.title")}</h2>
      <p className="text-theme-muted text-sm">{t("success.description")}</p>
      <button type="button" className="btn-primary w-full" onClick={onBackHome}>
        {t("success.backHome")}
      </button>
    </motion.div>
  );
}
