# Curriculum Architecture

Course
→ Unit
→ Learning Objective
→ Supporting Skill
→ Resource

Resources include:
- OpenStax
- Workbooks
- Assessments
- Examples
- Definitions
- How Tos
- Try Its
- Exercises
- Desmos
- Videos
- Teacher Notes

Learning Objectives own resources.
Resources never own learning objectives.

Supporting Skills are reusable across courses. A skill is defined once in the canonical skills library, then referenced wherever it is introduced, reinforced, deepened, or applied.

The teacher interface must also support the reverse path:

Supporting Skill
→ Course Progression
→ Unit
→ Learning Objective

This reverse view allows a teacher to select one skill and see where it is introduced, reinforced, deepened, and applied across the course sequence. Detailed requirements are recorded in `TEACHER_INTERFACE_REQUIREMENTS.md`.

Skills persist forward as part of the student toolkit after introduction or inheritance. This availability is derived for display and planning; it does not create an explicit relationship to every later objective.
