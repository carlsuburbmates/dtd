import Link from "@docusaurus/Link";
import ModuleBadge from "@site/src/components/ModuleBadge";

export default function CoursePathway({ modules = [] }) {
  return (
    <section className="course-pathway">
      {modules.map((module) => (
        <article key={module.href} className="course-pathway__card">
          <ModuleBadge
            number={module.number}
            total={7}
            title={module.title}
            context={`${module.lessonCount} sections`}
            compact
          />
          <h3 className="course-pathway__title">{module.title}</h3>
          {module.focus ? <p className="course-pathway__focus">{module.focus}</p> : null}
          <div className="course-pathway__meta">
            <span>{module.lessonCount} sections</span>
            <span>{module.tool}</span>
          </div>
          {module.lessonTitles?.length ? (
            <ol className="course-pathway__lesson-list">
              {module.lessonTitles.map((title) => (
                <li key={title} className="course-pathway__lesson-item">
                  {title}
                </li>
              ))}
            </ol>
          ) : null}
          <Link className="course-button course-button--ghost" to={module.href}>
            View guide
          </Link>
        </article>
      ))}
    </section>
  );
}
