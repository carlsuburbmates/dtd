export default function TrainerReadiness({ title, children }) {
  return (
    <section className="trainer-readiness">
      <div className="trainer-readiness__eyebrow">Trainer-readiness</div>
      {title ? <h2 className="trainer-readiness__title">{title}</h2> : null}
      <div className="trainer-readiness__body">{children}</div>
    </section>
  );
}
