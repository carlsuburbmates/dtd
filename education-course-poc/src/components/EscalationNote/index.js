export default function EscalationNote({ title, children }) {
  return (
    <section className="escalation-note">
      <div className="escalation-note__eyebrow">Escalation note</div>
      {title ? <h2 className="escalation-note__title">{title}</h2> : null}
      <div className="escalation-note__body">{children}</div>
    </section>
  );
}
