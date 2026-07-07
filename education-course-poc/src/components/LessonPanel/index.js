export default function LessonPanel({
  eyebrow,
  title,
  children,
  tone = "default",
}) {
  return (
    <section className={`lesson-panel lesson-panel--${tone}`}>
      {eyebrow ? <div className="lesson-panel__eyebrow">{eyebrow}</div> : null}
      {title ? <h2 className="lesson-panel__title">{title}</h2> : null}
      <div className="lesson-panel__body">{children}</div>
    </section>
  );
}
