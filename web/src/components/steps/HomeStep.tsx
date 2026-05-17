import { useState } from "react";
import { motion } from "framer-motion";
import type { Account } from "../../api";
import { useT } from "../../i18n";
import { HeroCard } from "../HeroCard";

type Props = {
  loading: boolean;
  accounts: Account[];
  onAdd: () => void;
  onChangeApi: () => void;
  onDelete: (tgId: number) => Promise<void>;
};

export function HomeStep({
  loading,
  accounts,
  onAdd,
  onChangeApi,
  onDelete,
}: Props) {
  const { t } = useT();
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleConfirmDelete = async (tgId: number) => {
    setDeletingId(tgId);
    try {
      await onDelete(tgId);
      setConfirmId(null);
    } catch {
      /* parent sets error banner */
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-6"
    >
      <HeroCard
        badge={t("home.badge")}
        title={t("home.title")}
        titleAccent={t("home.titleAccent")}
        description={t("home.description")}
      />

      {loading ? (
        <p className="text-theme-muted text-sm">{t("common.loading")}</p>
      ) : accounts.length === 0 ? (
        <p className="text-theme-muted text-sm">{t("home.empty")}</p>
      ) : (
        <ul className="space-y-3">
          {accounts.map((a) => {
            const confirming = confirmId === a.tg_id;
            const deleting = deletingId === a.tg_id;

            return (
              <li key={a.tg_id} className="card space-y-3">
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      a.bot_username ? "bg-emerald-500" : "bg-amber-500"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-theme font-medium">
                      {t("home.accountId")} {a.tg_id}
                    </p>
                    <p className="text-sm text-theme-muted">
                      @{a.bot_username || t("home.noBot")}
                    </p>
                  </div>
                  {!confirming && (
                    <button
                      type="button"
                      className="btn-danger shrink-0"
                      onClick={() => setConfirmId(a.tg_id)}
                      disabled={deletingId !== null}
                    >
                      {t("home.delete")}
                    </button>
                  )}
                </div>

                {confirming && (
                  <div className="warning-banner space-y-3">
                    <p className="text-sm font-medium text-theme">
                      {t("home.deleteConfirmTitle")}
                    </p>
                    <p className="text-sm leading-relaxed">
                      {t("home.deleteConfirmBody").replace("{id}", String(a.tg_id))}
                    </p>
                    <div className="confirm-actions">
                      <button
                        type="button"
                        className="btn-danger-solid"
                        onClick={() => void handleConfirmDelete(a.tg_id)}
                        disabled={deleting}
                      >
                        {deleting ? t("home.deleting") : t("home.deleteConfirm")}
                      </button>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setConfirmId(null)}
                        disabled={deleting}
                      >
                        {t("home.deleteCancel")}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <button type="button" className="btn-primary w-full" onClick={onAdd}>
        {t("home.addAccount")}
      </button>
      <button
        type="button"
        className="btn-ghost w-full text-sm"
        onClick={onChangeApi}
      >
        {t("home.changeApi")}
      </button>
    </motion.div>
  );
}
