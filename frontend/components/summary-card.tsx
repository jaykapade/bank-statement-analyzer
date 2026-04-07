export function SummaryCard({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string | number;
  valueClassName?: string;
}) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong
        className={`block max-w-full break-words text-[clamp(1.8rem,3vw,2.35rem)] leading-tight ${
          valueClassName ?? ""
        }`}
      >
        {value}
      </strong>
    </div>
  );
}
