export default function ChecklistBlock({
  title,
  subtitle,
  items = [],
  variant = "checklist",
}) {
  return (
    <section className={`checklist-block checklist-block--${variant}`}>
      {title || subtitle ? (
        <div className="checklist-block__header">
          {title ? <h2 className="checklist-block__title">{title}</h2> : null}
          {subtitle ? <p className="checklist-block__subtitle">{subtitle}</p> : null}
        </div>
      ) : null}
      <ul className="checklist-block__list">
        {items.map((item) => (
          <li key={item} className="checklist-block__item">
            <span className="checklist-block__marker" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
