import Link from "@docusaurus/Link";

export default function NextAction({ href, label, meta, copy }) {
  return (
    <Link className="next-action" to={href}>
      <div className="next-action__meta">{meta}</div>
      <div className="next-action__label">{label}</div>
      <div className="next-action__copy">{copy}</div>
    </Link>
  );
}
