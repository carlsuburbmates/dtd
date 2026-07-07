from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services import education_catalog  # noqa: E402


DOCUSAURUS_ROOT = REPO_ROOT / "education-course-poc"
DOCS_ROOT = DOCUSAURUS_ROOT / "docs"
SIDEBAR_PATH = DOCUSAURUS_ROOT / "sidebars.js"


CAPABILITY_LIST = [
    "Safe home setup",
    "Early routine control",
    "Dog-reading basics",
    "Fear response",
    "Reward timing",
    "Public handling",
    "Freedom boundaries",
    "Trainer readiness",
]


def safe_text(value: str) -> str:
    return str(value or "").strip()


def yaml_quote(value: str) -> str:
    text = safe_text(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def js_string(value: str) -> str:
    return json.dumps(safe_text(value), ensure_ascii=False)


def js_array(items: list[str]) -> str:
    return "[" + ", ".join(js_string(item) for item in items if safe_text(item)) + "]"


def jsx_expr(value: str) -> str:
    return "{" + value + "}"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def clear_generated_docs() -> None:
    if DOCS_ROOT.exists():
        shutil.rmtree(DOCS_ROOT)


def current_catalog() -> dict:
    return education_catalog.get_catalog()


def current_modules() -> list[dict]:
    return current_catalog()["modules"]


def current_course() -> dict:
    return current_catalog().get("course", {})


def raw_module(module_slug: str) -> dict:
    module = education_catalog.get_module(module_slug)
    if not module:
        raise ValueError(f"Missing module: {module_slug}")
    return module


def tool_refs(module: dict) -> list[dict]:
    return [item for item in module.get("tool_refs", []) if isinstance(item, dict)]


def module_dir(module: dict) -> str:
    return f"{int(module['number']):02d}-{module['slug']}"


def module_route(module: dict) -> str:
    return f"/modules/{module_dir(module)}/"


def module_overview_id(module_number: int) -> str:
    return f"module-{module_number}-overview"


def lesson_id(module_number: int, lesson_number: int) -> str:
    return f"module-{module_number}-lesson-{lesson_number}"


def tools_id(module_number: int) -> str:
    return f"module-{module_number}-tools"


def sidebar_doc_id(module_slug: str, doc_id: str) -> str:
    return f"modules/{module_slug}/{doc_id}"


def lesson_route(module: dict, lesson_number: int) -> str:
    return f"{module_route(module)}lesson-{lesson_number}"


def tools_route(module: dict) -> str:
    return f"{module_route(module)}tools"


def component_imports(*names: str) -> str:
    lines = [f"import {name} from '@site/src/components/{name}';" for name in names]
    return "\n".join(lines)


def flush_block(text: str) -> str:
    out = []
    for line in dedent(text).splitlines():
        if line.startswith("        "):
            out.append(line[8:])
        else:
            out.append(line)
    return "\n".join(out).lstrip("\n")


def pathway_module_meta(modules: list[dict]) -> str:
    rows = []
    for module in modules:
        raw = raw_module(module["slug"])
        rows.append(
            {
                "number": int(module["number"]),
                "title": safe_text(module["title"]),
                "href": module_route(module),
                "focus": safe_text(module.get("strapline") or module.get("objective")),
                "lessonCount": len(raw.get("lessons", [])),
                "lessonTitles": [safe_text(lesson["title"]) for lesson in raw.get("lessons", [])],
                "tool": safe_text((tool_refs(raw) or [{}])[0].get("title") or "Module tools"),
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2)


def course_home_page(modules: list[dict]) -> str:
    pathway = pathway_module_meta(modules)
    capabilities = json.dumps(CAPABILITY_LIST, ensure_ascii=False)
    course = current_course()
    return flush_block(
        f"""\
        ---
        id: start-here
        title: {yaml_quote(safe_text(course.get("title") or "The First Leash"))}
        slug: /
        sidebar_label: Start Here
        ---

        {component_imports("CourseHero", "CoursePathway", "ChecklistBlock", "LessonPanel", "NextAction")}

        <CourseHero
          eyebrow={js_string(safe_text(course.get("eyebrow") or "Free starter guide"))}
          title={js_string(safe_text(course.get("title") or "The First Leash"))}
          body={js_string(" ".join(part for part in [safe_text(course.get("subtitle")), safe_text(course.get("support_line"))] if part))}
          primaryHref={js_string(module_route(modules[0]))}
          primaryLabel={js_string(safe_text(course.get("primary_cta") or "Start the guide"))}
          secondaryHref="#guide-outline"
          secondaryLabel="View guide outline"
        />

        ## Guide outline

        <p>{safe_text(course.get("list_intro") or "From first setup to everyday confidence.")}</p>

        <CoursePathway modules={jsx_expr(pathway)} />

        ## What it covers

        <ChecklistBlock title="Guide highlights" items={jsx_expr(capabilities)} variant="worksheet" />

        <NextAction
          href={js_string(module_route(modules[0]))}
          label={js_string(safe_text(course.get("primary_cta") or "Start the guide"))}
          meta="Start here"
          copy="Open The Blueprint and follow the guide in order."
        />
        """
    )


def module_overview_page(module: dict, next_module: dict | None) -> str:
    raw = raw_module(module["slug"])
    module_number = int(module["number"])
    lesson_rows = []
    for lesson_number, lesson in enumerate(raw.get("lessons", []), start=1):
        lesson_rows.append(
            f"""
            <LessonPanel eyebrow={js_string(f"Lesson {lesson_number} • {int(lesson.get('estimated_minutes') or 0)} min")} title={js_string(safe_text(lesson['title']))}>
              {safe_text(lesson.get("scenario"))}
            </LessonPanel>
            """
        )
    primary_tool = (tool_refs(raw) or [{}])[0]
    tool_titles = [safe_text(tool.get("title")) for tool in tool_refs(raw)]

    return flush_block(
        f"""\
        ---
        id: {module_overview_id(module_number)}
        title: {yaml_quote(f"Guide {module_number} — {safe_text(module['title'])}")}
        slug: {yaml_quote(module_route(module))}
        sidebar_label: Overview
        ---

        {component_imports("ModuleBadge", "LessonPanel", "ChecklistBlock", "NextAction")}

        <ModuleBadge number={{{module_number}}} total={{7}} title={js_string(module['title'])} context="Overview" label="Guide" />

        # {safe_text(module['title'])}

        <LessonPanel eyebrow="Guide aim" title="What this guide covers">
          {safe_text(raw.get("intro"))}
        </LessonPanel>

        ## Sections in this guide

        {chr(10).join(item.strip() for item in lesson_rows)}

        ## Checklists

        <LessonPanel eyebrow="Included in this guide" title={js_string(safe_text(primary_tool.get("title") or "Guide checklists"))} tone="soft">
          {safe_text(primary_tool.get("summary") or "Use the worksheet tools alongside the lessons.")}
        </LessonPanel>

        <ChecklistBlock title="Checklist set" items={jsx_expr(js_array(tool_titles))} variant="worksheet" />

        ## Completion check

        <ChecklistBlock title={js_string(safe_text(raw.get("checkpoint_title") or "Before you move on"))} items={jsx_expr(js_array(raw.get("checkpoint_items") or []))} variant="checklist" />

        <NextAction
          href={js_string(lesson_route(module, 1))}
          label="Start the guide"
          meta={js_string(f"Guide {module_number}")}
          copy={js_string(f"Start with {safe_text(raw.get('lessons', [])[0]['title'])}.")}
        />
        """
    )


def lesson_page(module: dict, lesson: dict, *, lesson_number: int, total_lessons: int) -> str:
    module_number = int(module["number"])
    is_final_lesson = lesson_number == total_lessons
    next_href = tools_route(module) if is_final_lesson else lesson_route(module, lesson_number + 1)
    next_label = "Open checklist" if is_final_lesson else "Continue guide"
    next_copy = (
        "Use the guide checklists and completion check before moving on."
        if is_final_lesson
        else f"{safe_text(raw_module(module['slug']).get('lessons', [])[lesson_number]['title'])}"
    )
    return flush_block(
        f"""\
        ---
        id: {lesson_id(module_number, lesson_number)}
        title: {yaml_quote(f"Section {lesson_number} — {safe_text(lesson['title'])}")}
        slug: {yaml_quote(lesson_route(module, lesson_number))}
        sidebar_label: {yaml_quote(f"Section {lesson_number} — {safe_text(lesson['title'])}")}
        ---

        {component_imports("ModuleBadge", "LessonPanel", "DecisionRule", "ChecklistBlock", "EscalationNote", "TrainerReadiness", "NextAction")}

        <ModuleBadge number={{{module_number}}} total={{7}} title={js_string(module['title'])} context={js_string(f"Section {lesson_number} of {total_lessons}")} label="Guide" />

        # {safe_text(lesson['title'])}

        ## Situation

        <LessonPanel eyebrow="Lesson context">
          {safe_text(lesson.get("scenario"))}
        </LessonPanel>

        ## What to notice

        <ChecklistBlock items={jsx_expr(js_array(lesson.get("notice") or []))} variant="checklist" />

        ## Common mistake

        <LessonPanel eyebrow="What often makes this worse" tone="caution">
          {safe_text(lesson.get("common_mistake"))}
        </LessonPanel>

        ## Decision rule

        <DecisionRule label="Rule for this lesson">{safe_text(lesson.get("decision_rule"))}</DecisionRule>

        ## What to do now

        <ChecklistBlock items={jsx_expr(js_array(lesson.get("do_now") or []))} variant="worksheet" />

        ## What to watch

        <ChecklistBlock items={jsx_expr(js_array(lesson.get("watch_for") or []))} variant="checklist" />

        ## When to get help

        <EscalationNote>
          {safe_text(lesson.get("when_to_seek_help"))}
        </EscalationNote>

        ## What to record

        <TrainerReadiness>
          {safe_text(lesson.get("trainer_readiness_note"))}
        </TrainerReadiness>

        <NextAction
          href={js_string(next_href)}
          label={js_string(next_label)}
          meta={js_string(f"Guide {module_number}")}
          copy={js_string(next_copy)}
        />
        """
    )


def render_tool_block(tool: dict) -> str:
    body = []
    items = tool.get("items") or tool.get("prompts") or []
    body.append(
        f"<ChecklistBlock title={js_string(safe_text(tool['title']))} subtitle={js_string(safe_text(tool.get('summary')))} items={jsx_expr(js_array(items))} variant=\"worksheet\" />"
    )
    return "\n\n".join(body)


def tools_page(module: dict, next_module: dict | None) -> str:
    raw = raw_module(module["slug"])
    module_number = int(module["number"])
    tools_blocks = "\n\n".join(render_tool_block(tool) for tool in tool_refs(raw))
    next_href = module_route(next_module) if next_module else "/"
    next_label = "Continue guide" if next_module else "Return to guide home"
    next_copy = (
        f"Move on to {safe_text(next_module['title'])} once this guide feels usable in real life."
        if next_module
        else "You have reached the end of The First Leash."
    )

    return flush_block(
        f"""\
        ---
        id: {tools_id(module_number)}
        title: {yaml_quote(f"Checklists — {safe_text(module['title'])}")}
        slug: {yaml_quote(tools_route(module))}
        sidebar_label: Tools
        ---

        {component_imports("ModuleBadge", "LessonPanel", "ChecklistBlock", "NextAction")}

        <ModuleBadge number={{{module_number}}} total={{7}} title={js_string(module['title'])} context="Checklists" label="Guide" />

        # Guide {module_number} Checklists

        <LessonPanel eyebrow="Use with this guide" title="Work through the guide in practice">
          Use these checklists alongside the lessons or immediately after them to turn the guide into day-to-day action.
        </LessonPanel>

        ## Included checklists

        {tools_blocks}

        <NextAction
          href={js_string(module_route(module))}
          label="View guide"
          meta={js_string(f"Guide {module_number} overview")}
          copy="Review the guide purpose, completion check, and section order."
        />

        <NextAction
          href={js_string(next_href)}
          label={js_string(next_label)}
          meta="Next guide"
          copy={js_string(next_copy)}
        />
        """
    )


def write_explicit_sidebar(modules: list[dict]) -> None:
    lines = [
        "// @ts-check",
        "",
        "/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */",
        "const sidebars = {",
        "  courseSidebar: [",
        "    {",
        "      type: 'doc',",
        "      id: 'start-here',",
        "      label: 'Start Here',",
        "    },",
    ]

    for module in modules:
        module_number = int(module["number"])
        raw = raw_module(module["slug"])
        lines.extend(
            [
                "    {",
                "      type: 'category',",
                f"      label: {js_string(f'Guide {module_number} — {safe_text(module['title'])}')},",
                "      collapsed: false,",
                "      items: [",
                f"        {{ type: 'doc', id: '{sidebar_doc_id(module['slug'], module_overview_id(module_number))}', label: 'Overview' }},",
            ]
        )
        for lesson_number, lesson in enumerate(raw.get("lessons", []), start=1):
            lines.append(
                f"        {{ type: 'doc', id: '{sidebar_doc_id(module['slug'], lesson_id(module_number, lesson_number))}', label: {js_string(f'Section {lesson_number} — {safe_text(lesson['title'])}')} }},"
            )
        lines.append(f"        {{ type: 'doc', id: '{sidebar_doc_id(module['slug'], tools_id(module_number))}', label: 'Checklists' }},")
        lines.extend(["      ],", "    },"])

    lines.extend(["  ],", "};", "", "export default sidebars;"])
    write(SIDEBAR_PATH, "\n".join(lines))


def build_docusaurus_docs() -> None:
    modules = current_modules()
    clear_generated_docs()

    write(DOCS_ROOT / "intro.mdx", course_home_page(modules))

    for index, module in enumerate(modules):
        next_module = modules[index + 1] if index < len(modules) - 1 else None
        raw = raw_module(module["slug"])
        base = DOCS_ROOT / "modules" / module_dir(module)
        write(base / "index.mdx", module_overview_page(module, next_module))

        for lesson_number, lesson in enumerate(raw.get("lessons", []), start=1):
            write(
                base / f"lesson-{lesson_number}.mdx",
                lesson_page(module, lesson, lesson_number=lesson_number, total_lessons=len(raw.get("lessons", []))),
            )

        write(base / "tools.mdx", tools_page(module, next_module))

    write_explicit_sidebar(modules)


def main() -> None:
    build_docusaurus_docs()
    print(f"Generated Docusaurus course docs in {DOCS_ROOT}")
    print(f"Updated explicit sidebar at {SIDEBAR_PATH}")


if __name__ == "__main__":
    main()
