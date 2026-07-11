# Structured Curriculum Data

This directory is the emerging source of truth for curriculum records and relationships. Markdown files remain the faculty-readable review and export layer.

## Directory Layout

- `courses/`: course, unit, and objective records
- `mappings/`: objective-to-skill relationships
- `schema/`: field definitions and validation rules
- `audits/`: unresolved cross-course assumptions and introduction gaps

## Current Migration Status

- Math 12: structured; mapping approved
- Math 21: structured; mapping approved
- Math 22: structured; mapping approved
- Math 31: structured; mapping approved
- Math 32: structured; mapping approved
- Math 49: structured; mapping approved

The six-course objective-to-skill migration is complete. Course mappings and generated cross-course audits should be regenerated whenever approved YAML records change.

## Generated Cross-Course Outputs

- `generated/skill_progressions.json`: UI-ready record for every skill and mapped occurrence
- `generated/SKILL_PROGRESSIONS.md`: teacher-readable individual-skill progression views
- `data/audits/SKILL_PROGRESSION_AUDIT.md`: automatic progression consistency audit

Regenerate all three with `tools/generate_skill_progressions.ps1`.
