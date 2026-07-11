# Curriculum Map UI Prototype

This teacher-facing prototype begins with the course view and supports this navigation path:

Curriculum overview → Course → Objective → Skill progression

It also supports direct skill search and visually distinguishes explicit progression events from carried-forward toolkit availability.

## Curriculum Data

The prototype reads `public/data/skill_progressions.json`. Running `../tools/generate_skill_progressions.ps1` refreshes both the canonical generated dataset and the UI copy.

## Local Development

- Install dependencies with the package manager appropriate to the development environment.
- Run `npm run dev` or `pnpm dev`.
- Run `npm run build` or `pnpm build` for production validation.

The Sites starter includes a Cloudflare `workerd` dependency. Its pinned version does not provide a Windows ARM64 binary, so production build validation must run on a supported platform or CI environment.
