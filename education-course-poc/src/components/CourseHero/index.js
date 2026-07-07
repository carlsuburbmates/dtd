import Link from "@docusaurus/Link";

export default function CourseHero({
  eyebrow,
  title,
  body,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
}) {
  return (
    <section className="course-hero">
      <div className="course-hero__eyebrow">{eyebrow}</div>
      <h1 className="course-hero__title">{title}</h1>
      <p className="course-hero__body">{body}</p>
      <div className="course-hero__actions">
        <Link className="course-button course-button--primary" to={primaryHref}>
          {primaryLabel}
        </Link>
        {secondaryHref ? (
          <Link className="course-button course-button--ghost" to={secondaryHref}>
            {secondaryLabel}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
