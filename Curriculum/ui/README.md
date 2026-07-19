# Curriculum Map UI Prototype

This teacher-facing prototype begins with the course view and supports this navigation path:

Curriculum overview → Course → Objective → Skill progression

It also supports direct skill search and visually distinguishes explicit progression events from carried-forward toolkit availability.

## Active Application Files

- `index.html`: the browser shell and React mount point
- `src/main.tsx`: starts React and imports the interface and stylesheet
- `app/page.tsx`: interface behavior, search, filters, navigation, and views
- `app/globals.css`: visual design and responsive layout
- `public/data/skill_progressions.json`: generated browser-ready curriculum data
- `public/downloads/`: generated curriculum PDFs offered by the site
- `vite.config.ts`: Vite and GitHub Pages build settings

This is a static Vite/React site. It does not use Next.js, a runtime database, an API server, or a Cloudflare Worker.

## Curriculum Data

The prototype reads `public/data/skill_progressions.json`. Running `../tools/generate_skill_progressions.ps1` refreshes both the canonical generated dataset and the UI copy.

## Local Development

- Run `npm install`.
- Run `npm run dev` for a local development server.
- Run `npm run build` for production validation.
- Run `npm run preview` to inspect the production build locally.

## GitHub Pages

The repository workflow at `.github/workflows/pages.yml` regenerates curriculum data, builds this static site, and deploys `dist/` to GitHub Pages whenever `main` changes.

In the GitHub repository, choose **Settings → Pages → Source: GitHub Actions**. After the workflow succeeds, the site is available at:

`https://mharrington-png.github.io/Curriculum-Map/`

The deployment workflow regenerates progression data and builds the website. It does not regenerate the PDF downloads; refresh those with the PDF generator before publishing curriculum or resource changes.
