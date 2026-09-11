"""
Generate modern, standalone HTML editions of The First Leash education guides.
Produces:
  1. The Initial Starter Guide for new registrations: the-first-leash-guide-1-blueprint.html
  2. The Complete 7-Guide Master Edition: the-first-leash-complete-handbook.html
  3. Individual standalone guide files for each module (Guides 1 to 7)

Features:
  - Clean semantic HTML5 optimized for LLM readability, inspection, and re-styling
  - Organic Earthy Luxe visual theme with CSS custom properties
  - Embedded responsive CSS and high-fidelity @media print rules for 1-click A4 PDF export
  - High-res images, interactive checklist checkboxes, and visual callout blocks
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FILES_DIR = REPO_ROOT / "frontend" / "public" / "files"
DOCS_EDU_DIR = REPO_ROOT / "docs" / "education"

# Shared Modern CSS Stylesheet for all HTML Editions
CSS_STYLES = """
:root {
  --ink: #1A3A32;
  --ink-light: #4A615A;
  --moss: #5C6D59;
  --terracotta: #9B4F31;
  --cream: #F5F2EB;
  --surface: #FAFAF7;
  --border: #E5DFD3;
  --card-bg: #FFFFFF;
  --warn-bg: #FBF5F0;
  --decision-bg: #F0F4F2;
  --text: #2B3330;
  --font-serif: "Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-sans: "Outfit", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-sans);
  background-color: var(--cream);
  color: var(--text);
  line-height: 1.65;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}

.document-container {
  max-width: 860px;
  margin: 40px auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 10px 35px rgba(26, 58, 50, 0.06);
  overflow: hidden;
}

/* Header & Cover Banner */
.cover-banner {
  width: 100%;
  height: 320px;
  object-fit: cover;
  display: block;
  border-bottom: 3px solid var(--terracotta);
}

.cover-header {
  padding: 40px 48px 24px;
}

.badge-pill {
  display: inline-block;
  padding: 5px 14px;
  background: var(--ink);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: 999px;
  margin-bottom: 16px;
}

.badge-pill.terracotta {
  background: var(--terracotta);
}

.badge-pill.moss {
  background: var(--moss);
}

h1.doc-title {
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 800;
  color: var(--ink);
  line-height: 1.25;
  margin-bottom: 12px;
  letter-spacing: -0.01em;
}

p.doc-subtitle {
  font-size: 18px;
  color: var(--ink-light);
  line-height: 1.5;
  margin-bottom: 24px;
}

/* Meta Card */
.meta-card {
  background: var(--cream);
  border: 1px solid var(--border);
  border-left: 4px solid var(--moss);
  border-radius: 8px;
  padding: 16px 20px;
  font-size: 14px;
  color: var(--ink-light);
  margin-bottom: 32px;
}

.meta-card strong {
  color: var(--ink);
}

/* Content Area */
.content-body {
  padding: 0 48px 48px;
}

.guide-divider {
  height: 1px;
  background: var(--border);
  margin: 48px 0;
}

/* Module Section */
.guide-header {
  margin-bottom: 32px;
}

.guide-hero-img {
  width: 100%;
  height: 240px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 24px;
  border: 1px solid var(--border);
}

h2.guide-title {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 800;
  color: var(--ink);
  margin-bottom: 8px;
}

p.guide-strapline {
  font-size: 15px;
  font-style: italic;
  color: var(--terracotta);
  margin-bottom: 14px;
}

p.guide-intro {
  font-size: 15px;
  color: var(--text);
  line-height: 1.6;
}

/* Lesson Cards */
.lesson-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 32px;
  margin-bottom: 32px;
  box-shadow: 0 4px 12px rgba(26, 58, 50, 0.03);
}

.lesson-meta-strip {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--ink-light);
  font-weight: 600;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

h3.lesson-title {
  font-family: var(--font-serif);
  font-size: 21px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 18px;
  line-height: 1.35;
}

.subheading {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-light);
  margin-top: 18px;
  margin-bottom: 6px;
}

p.lesson-text {
  font-size: 15px;
  color: var(--text);
  margin-bottom: 14px;
}

/* Checklist Protocol */
.protocol-list {
  list-style: none;
  margin: 12px 0 20px;
}

.protocol-list li {
  position: relative;
  padding-left: 28px;
  margin-bottom: 10px;
  font-size: 14.5px;
  color: var(--text);
}

.protocol-list li::before {
  content: "•";
  position: absolute;
  left: 10px;
  color: var(--moss);
  font-size: 20px;
  line-height: 1;
}

.checkbox-list {
  list-style: none;
  margin: 12px 0 20px;
}

.checkbox-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 14.5px;
}

.checkbox-list input[type="checkbox"] {
  margin-top: 4px;
  accent-color: var(--terracotta);
  cursor: pointer;
}

/* Callout Boxes */
.callout-box {
  border-radius: 8px;
  padding: 16px 20px;
  margin: 18px 0;
  border-left: 4px solid;
}

.callout-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.callout-caution {
  background: var(--warn-bg);
  border-left-color: var(--terracotta);
}

.callout-caution .callout-title {
  color: var(--terracotta);
}

.callout-decision {
  background: var(--decision-bg);
  border-left-color: var(--ink);
}

.callout-decision .callout-title {
  color: var(--ink);
}

.callout-escalation {
  background: var(--cream);
  border-left-color: var(--moss);
}

.callout-escalation .callout-title {
  color: var(--moss);
}

/* Puppy Photo Break */
.puppy-break-img {
  width: 100%;
  height: 220px;
  object-fit: cover;
  border-radius: 8px;
  margin: 24px 0;
  border: 1px solid var(--border);
}

/* Footer */
.doc-footer {
  padding: 32px 48px;
  background: var(--cream);
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--ink-light);
}

.doc-footer a {
  color: var(--terracotta);
  text-decoration: none;
  font-weight: 600;
}

.doc-footer a:hover {
  text-decoration: underline;
}

/* Next Step CTA Banner */
.next-step-cta {
  background: var(--ink);
  color: #ffffff;
  border-radius: 8px;
  padding: 24px;
  margin-top: 36px;
  text-align: center;
}

.next-step-cta h4 {
  font-size: 18px;
  font-family: var(--font-serif);
  margin-bottom: 8px;
}

.next-step-cta p {
  font-size: 14px;
  opacity: 0.85;
  margin-bottom: 16px;
}

.cta-button {
  display: inline-block;
  background: var(--terracotta);
  color: #ffffff;
  padding: 10px 22px;
  border-radius: 6px;
  font-weight: 600;
  text-decoration: none;
  font-size: 14px;
  transition: opacity 0.2s;
}

.cta-button:hover {
  opacity: 0.9;
}

/* Print Styles for 1-Click PDF Generation */
@media print {
  body {
    background: #ffffff;
    font-size: 13px;
  }

  .document-container {
    max-width: 100%;
    margin: 0;
    border: none;
    box-shadow: none;
    border-radius: 0;
  }

  .cover-banner {
    height: 240px;
  }

  .guide-divider {
    break-after: page;
    height: 0;
    margin: 0;
    border: none;
  }

  .lesson-card {
    box-shadow: none;
    border: 1px solid #cccccc;
    break-inside: avoid;
    padding: 20px;
    margin-bottom: 24px;
  }

  .next-step-cta {
    display: none;
  }

  @page {
    size: A4;
    margin: 15mm;
  }
}
"""

# Re-use the canonical 7-guide curriculum data structure
from scripts.generate_education_pdfs import CURRICULUM


def generate_guide_html(guide_data, is_standalone=True, total_guides=7):
    """Generates the HTML markup for a single module guide."""
    mod_num = guide_data["number"]
    html = []

    html.append(f'<section class="guide-section" id="guide-{mod_num}">')

    # Guide Hero Image
    html.append(f'  <img src="../images/{guide_data["cover_img"]}" alt="{guide_data["title"]} Cover" class="guide-hero-img" />')

    # Guide Header
    html.append('  <div class="guide-header">')
    html.append(f'    <span class="badge-pill">GUIDE {mod_num} OF {total_guides}</span>')
    html.append(f'    <h2 class="guide-title">Guide {mod_num} — {guide_data["title"]}</h2>')
    html.append(f'    <p class="guide-strapline">{guide_data["strapline"]}</p>')
    html.append(f'    <p class="guide-intro">{guide_data["intro"]}</p>')
    html.append('  </div>')

    # Puppy Visual Break
    html.append(f'  <img src="../images/{guide_data["puppy_img"]}" alt="Guide {mod_num} Illustration" class="puppy-break-img" />')

    # Lessons
    for lesson in guide_data["lessons"]:
        html.append('  <article class="lesson-card">')
        html.append('    <div class="lesson-meta-strip">')
        html.append(f'      <span>SECTION {lesson["num"]}</span>')
        html.append(f'      <span>•</span>')
        html.append(f'      <span>FOCUS: {lesson["tag"]}</span>')
        html.append(f'      <span>•</span>')
        html.append(f'      <span>{lesson["time"]}</span>')
        html.append('    </div>')

        html.append(f'    <h3 class="lesson-title">{lesson["title"]}</h3>')

        html.append('    <div class="subheading">The Situation</div>')
        html.append(f'    <p class="lesson-text">{lesson["scenario"]}</p>')

        html.append('    <div class="subheading">The Science & Mechanics</div>')
        html.append(f'    <p class="lesson-text">{lesson["science"]}</p>')

        html.append('    <div class="subheading">Action Protocol</div>')
        html.append('    <ul class="protocol-list">')
        for step in lesson["protocol"]:
            html.append(f'      <li>{step}</li>')
        html.append('    </ul>')

        # Caution Callout
        html.append('    <aside class="callout-box callout-caution">')
        html.append('      <div class="callout-title">⚠️ Common Caution Trap</div>')
        html.append(f'      <p>{lesson["caution"]}</p>')
        html.append('    </aside>')

        # Decision Rule
        html.append('    <aside class="callout-box callout-decision">')
        html.append('      <div class="callout-title">⚖️ Immutable Decision Rule</div>')
        html.append(f'      <p><strong>{lesson["decision"]}</strong></p>')
        html.append('    </aside>')

        # Clinical Escalation
        html.append('    <aside class="callout-box callout-escalation">')
        html.append('      <div class="callout-title">🚩 Clinical Escalation Criteria</div>')
        html.append(f'      <p>{lesson["escalation"]}</p>')
        html.append('    </aside>')

        html.append('  </article>')

    # Next Step CTA for Standalone Guide
    if is_standalone:
        if mod_num < total_guides:
            next_mod = CURRICULUM[mod_num]
            html.append('  <div class="next-step-cta">')
            html.append(f'    <h4>Completed Guide {mod_num}?</h4>')
            html.append(f'    <p>Your foundation is active. Continue to <strong>Guide {next_mod["number"]}: {next_mod["title"]}</strong> ({next_mod["strapline"]})</p>')
            html.append(f'    <a href="the-first-leash-guide-{next_mod["number"]}.html" class="cta-button">Open Guide {next_mod["number"]} →</a>')
            html.append('  </div>')
        else:
            html.append('  <div class="next-step-cta">')
            html.append('    <h4>7-Guide Curriculum Complete!</h4>')
            html.append('    <p>Need specialized in-person support for reactivity, puppy training, or obedience in Melbourne?</p>')
            html.append('    <a href="https://dogtrainersdirectory.com.au/match" class="cta-button">Match with a Local Specialist →</a>')
            html.append('  </div>')

    html.append('</section>')
    return "\n".join(html)


def build_full_html_document(title, subtitle, badge_text, cover_image, body_content, is_initial_guide=False):
    """Builds a complete, valid HTML5 document string with embedded styles."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} • The First Leash</title>
  <meta name="description" content="{subtitle}" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
{CSS_STYLES}
  </style>
</head>
<body>

  <main class="document-container">
    <!-- Cover Banner -->
    <img src="../images/{cover_image}" alt="{title} Cover" class="cover-banner" />

    <header class="cover-header">
      <span class="badge-pill {'terracotta' if is_initial_guide else ''}">{badge_text}</span>
      <h1 class="doc-title">{title}</h1>
      <p class="doc-subtitle">{subtitle}</p>

      <div class="meta-card">
        <strong>Publisher:</strong> Dog Trainers Directory (Melbourne, Victoria)<br/>
        <strong>Curriculum:</strong> Evidence-Based Positive Reinforcement &amp; Clinical De-Escalation<br/>
        <strong>Access Level:</strong> 100% Free Public Guide • 
        <a href="https://dogtrainersdirectory.com.au" style="color: var(--terracotta); text-decoration: none; font-weight: 600;">
          dogtrainersdirectory.com.au
        </a>
      </div>
    </header>

    <div class="content-body">
{body_content}
    </div>

    <footer class="doc-footer">
      <div>
        <strong>The First Leash</strong> • Dog Trainers Directory
      </div>
      <div>
        <a href="https://dogtrainersdirectory.com.au/match">Find a Verified Melbourne Trainer →</a>
      </div>
    </footer>
  </main>

</body>
</html>
"""


def main():
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Generating Initial Starter Guide for New Registrations (Guide 1: The Blueprint)...")
    guide_1 = CURRICULUM[0]
    guide_1_content = generate_guide_html(guide_1, is_standalone=True)
    guide_1_html = build_full_html_document(
        title="The First Leash: Guide 1 — The Blueprint",
        subtitle="Home Architecture, Environmental Safety & Healthcare Foundations",
        badge_text="STARTER PACK • NEW REGISTRATION GUIDE",
        cover_image="first-leash.jpg",
        body_content=guide_1_content,
        is_initial_guide=True
    )
    
    # Save as the designated Initial Guide file
    starter_guide_path = FILES_DIR / "the-first-leash-guide-1-blueprint.html"
    starter_guide_path.write_text(guide_1_html, encoding="utf-8")
    print(f"  ✓ Created: {starter_guide_path} ({len(guide_1_html)} bytes)")

    print("\n2. Generating Individual Standalone HTML Guides (Guides 1 to 7)...")
    for mod in CURRICULUM:
        mod_num = mod["number"]
        content = generate_guide_html(mod, is_standalone=True)
        html_doc = build_full_html_document(
            title=f"The First Leash: Guide {mod_num} — {mod['title']}",
            subtitle=mod["strapline"],
            badge_text=f"GUIDE {mod_num} OF 7",
            cover_image=mod["cover_img"],
            body_content=content,
            is_initial_guide=(mod_num == 1)
        )
        out_path = FILES_DIR / f"the-first-leash-guide-{mod_num}.html"
        out_path.write_text(html_doc, encoding="utf-8")
        print(f"  ✓ Created: {out_path.name}")

    print("\n3. Generating The Complete 7-Guide Master Handbook Edition...")
    master_sections = []
    for i, mod in enumerate(CURRICULUM):
        master_sections.append(generate_guide_html(mod, is_standalone=False))
        if i < len(CURRICULUM) - 1:
            master_sections.append('      <div class="guide-divider"></div>')
    
    master_html = build_full_html_document(
        title="The First Leash: Complete Dog Owner Handbook",
        subtitle="A 7-Guide Practical System for Foundations, Stress Reading, and Urban Resilience",
        badge_text="COMPLETE 7-GUIDE MASTER EDITION",
        cover_image="first-leash.jpg",
        body_content="\n".join(master_sections),
        is_initial_guide=False
    )
    master_path = FILES_DIR / "the-first-leash-complete-handbook.html"
    master_path.write_text(master_html, encoding="utf-8")
    print(f"  ✓ Created: {master_path} ({len(master_html)} bytes)")

    # Also sync build/files if it exists
    build_files = REPO_ROOT / "frontend" / "build" / "files"
    if build_files.exists():
        for f in FILES_DIR.glob("*.html"):
            (build_files / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        print("\nSynced all HTML files to frontend/build/files/")

    print("\nAll HTML Editions successfully generated!")


if __name__ == "__main__":
    main()
