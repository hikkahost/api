type Props = {
  badge: string;
  title: string;
  titleAccent: string;
  description: string;
};

export function HeroCard({ badge, title, titleAccent, description }: Props) {
  return (
    <div className="hero-card">
      <span className="text-[10px] uppercase tracking-widest text-theme-muted font-medium">
        {badge}
      </span>
      <h2 className="text-2xl sm:text-3xl font-semibold text-theme mt-2">
        {title} <span className="accent-text">{titleAccent}</span>
      </h2>
      <p className="text-sm text-theme-muted mt-2 leading-relaxed">{description}</p>
    </div>
  );
}
