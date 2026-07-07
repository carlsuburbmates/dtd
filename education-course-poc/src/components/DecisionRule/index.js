export default function DecisionRule({ children, label = "Decision rule" }) {
  return (
    <section className="decision-rule">
      {label ? <div className="decision-rule__eyebrow">{label}</div> : null}
      <div className="decision-rule__body">{children}</div>
    </section>
  );
}
