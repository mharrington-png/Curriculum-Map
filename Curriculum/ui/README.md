# Curriculum Map UI Prototype

This teacher-facing prototype begins with the course view and supports this navigation path:

Curriculum overview → Course → Objective → Skill progression

It also supports direct skill search and visually distinguishes explicit progression events from carried-forward toolkit availability.

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
