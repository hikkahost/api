import { useT } from "../i18n";
import { UserbotBadge, HikkaHostBadge } from "./UserbotBadge";
import { ControlBotLink } from "./ControlBotLink";

type Props = {
  userbot: string;
};

export function BrandFooter({ userbot }: Props) {
  const { t } = useT();

  return (
    <footer className="brand-footer">
      <div className="brand-footer-inner">
        <ControlBotLink centered />
        <div className="flex flex-col items-center gap-2.5 w-full">
          <UserbotBadge userbot={userbot} size="md" />
          <span className="brand-powered-label">{t("common.poweredByLabel")}</span>
          <HikkaHostBadge size="md" />
        </div>
      </div>
      <p className="brand-copyright">{t("common.copyright")}</p>
    </footer>
  );
}
