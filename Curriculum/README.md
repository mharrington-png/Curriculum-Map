# Middlesex Mathematics Curriculum

This repository is a curriculum publishing system. Faculty-approved curriculum data is maintained once, then used to build the teacher website, individual course PDFs, the combined curriculum PDF, progression views, and consistency audits.

The central model is:

`Course -> Unit -> Learning Objective -> Supporting Skill -> Resource`

Learning objectives and supporting skills are the durable curriculum. Textbooks, workbooks, exercises, and other resources are replaceable supports.

## Start Here: What Should I Edit?

| If you want to change... | Edit... |
|---|---|
| A course title, unit, priority, or learning objective | `data/courses/*.yaml` |
| Which skills support a learning objective | `data/mappings/*_objective_skills.yaml` |
| A canonical skill name or description | The appropriate `skills/*_SKILLS.md` file |
| Textbook or workbook section coverage | `mappings/openstax/*.md` or `mappings/workbook/*.md` |
| Website behavior, navigation, filters, or wording | `ui/app/page.tsx` |
| Website colors, spacing, typography, or responsive layout | `ui/app/globals.css` |
| Individual or at-a-glance PDF content and layout | `tools/generate_course_glance_pdfs.py` |
| The combined curriculum PDF structure | `tools/generate_full_curriculum_report.py` |
| The rules used to build skill progressions and audits | `tools/generate_skill_progressions.ps1` |

## Generated Files: Do Not Edit These Directly

Changes made directly to these locations will be overwritten the next time the project is rebuilt.

| Location | What it contains |
|---|---|
| `generated/` | Browser-ready progression data and teacher-readable progression exports |
| `data/audits/` | Automatically generated consistency checks |
| `ui/public/data/` | Website copy of the generated progression JSON |
| `ui/dist/` | Compiled website sent to GitHub Pages |
| `output/pdf/` | Generated course and combined curriculum PDFs |
| `ui/public/downloads/` | PDF copies offered by the website |
| `tmp/` | Temporary extraction and rendering files |
| `ui/node_modules/` | Installed website dependencies |

## Folder Map

| Folder | Role |
|---|---|
| `data/` | Authoritative course, unit, objective, and objective-to-skill records |
| `skills/` | Canonical definitions for reusable supporting skills |
| `mappings/` | Textbook, workbook, assessment, and other resource crosswalks |
| `source_documents/` | Original faculty documents and PDFs used as evidence or reference |
| `objectives/` and `courses/` | Faculty-readable review and reference material |
| `tools/` | Scripts that validate data and build website data and PDFs |
| `ui/` | The active Vite/React teacher website |
| `docs/` | Architecture, standards, conventions, requirements, and plans |
| `generated/`, `output/`, and `tmp/` | Derived products rather than curriculum sources |

## How Publishing Works

### Curriculum data and website

`tools/generate_skill_progressions.ps1` reads the course YAML, objective-to-skill YAML, and canonical skill library. It produces the progression JSON, its website copy, a readable progression document, and an audit.

The website then reads `ui/public/data/skill_progressions.json`. Vite compiles the active website files into `ui/dist/`, and the workflow in `.github/workflows/pages.yml` publishes that folder to GitHub Pages.

The active website is intentionally small:

- `ui/index.html` provides the browser shell.
- `ui/src/main.tsx` starts React.
- `ui/app/page.tsx` contains the interface and interactions.
- `ui/app/globals.css` contains the visual design.
- `ui/public/` contains the generated data and downloadable PDFs.

There is no runtime database, API server, Next.js application, or Cloudflare Worker. Teachers use a static site that loads a static JSON file.

### PDFs

`tools/generate_course_glance_pdfs.py` combines course data, progression data, and resource mappings to create the individual course and at-a-glance PDFs. It also refreshes the website download copies.

`tools/generate_full_curriculum_report.py` combines the individual course PDFs into the complete mathematics curriculum PDF with its title page, linked table of contents, and bookmarks.

PDFs are not currently rebuilt by the GitHub Pages workflow. Regenerate them before publishing when curriculum or resource coverage changes.

## Common Workflows

After changing course, objective, or skill mapping data:

```powershell
./tools/generate_skill_progressions.ps1
```

After changing curriculum content, resource mappings, or PDF formatting:

```powershell
python ./tools/generate_course_glance_pdfs.py
python ./tools/generate_full_curriculum_report.py
```

After changing the website:

```powershell
cd ui
npm run build
```

## Project Rules and Background

Recommended documentation order:

1. `docs/PROJECT_CHARTER.md`
2. `docs/ARCHITECTURE.md`
3. `docs/CURRICULUM_STANDARDS.md`
4. `docs/NAMING_CONVENTIONS.md`
5. `docs/TEACHER_INTERFACE_REQUIREMENTS.md`
6. `docs/AI_COLLABORATION.md`
7. `docs/ROADMAP.md`
