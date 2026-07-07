export default function ModuleBadge({
  number,
  total,
  title,
  context,
  compact = false,
  label = "Guide",
}) {
  return (
    <div className={`module-badge${compact ? " module-badge--compact" : ""}`}>
      <div className="module-badge__pill">{`${label} ${number} of ${total}`}</div>
      {title ? <div className="module-badge__title">{title}</div> : null}
      {context ? <div className="module-badge__context">{context}</div> : null}
    </div>
  );
}
