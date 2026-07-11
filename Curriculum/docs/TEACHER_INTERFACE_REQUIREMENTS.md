# Teacher Interface Requirements

## Frequently Asked Skill Questions

When teachers consult the curriculum map, they frequently ask questions such as:

- Where is this skill first introduced?
- In which later courses is it reinforced, deepened, or applied?
- Which learning objectives use this skill?
- Is the skill required, a prerequisite, or method-dependent in each objective?
- Is the related course content required, review, or extension material?

These questions should be answerable directly from the interface without requiring teachers to search skill IDs or inspect source files.

## Individual Skill Progression View

Selecting any skill should open a clean, teacher-facing progression view containing:

1. The skill's plain-English description and permanent skill ID.
2. A left-to-right course sequence showing every mapped occurrence of the skill.
3. A visually distinct marker for each course role:
   - Introduce
   - Reinforce
   - Deepen
   - Apply
   - Carried forward / available in the student toolkit
4. The first introduction clearly identified.
5. Each occurrence linked to its course, unit, and learning objective.
6. Visible labels for:
   - Required, review, or extension content
   - Required, prerequisite, or method-dependent relationships
7. Filters that can hide or show review, extension, and method-dependent occurrences without removing them from the underlying map.

If a skill is used before any recorded introduction, the interface should flag the gap instead of implying that the sequence is complete. Skills inherited from middle school should be labeled accordingly.

## Persistent Student Toolkit

Once a skill is introduced—or identified as inherited—it generally remains available in the student's mathematical toolkit throughout later courses. The absence of an explicit objective-to-skill mapping in a later course does not mean the skill is obsolete, prohibited, or no longer expected.

The interface should therefore distinguish three states for each skill in each course:

- **Explicitly mapped:** The skill is directly connected to one or more objectives as Introduce, Reinforce, Deepen, or Apply.
- **Carried forward:** The skill was established earlier and remains part of the expected toolkit, but no objective in this course explicitly maps it.
- **Not yet established:** The skill has neither been introduced nor identified as inherited at this point in the sequence.

“Carried forward” is a derived interface state, not a new objective-mapping progression label. It must not create a false claim that the later course explicitly teaches, emphasizes, or assesses the skill.

For example, algebraic equivalence and rearranging equations remain available in Math 49 even when no Math 49 objective explicitly references those skills.

## Visual Direction

The default presentation should be a compact progression timeline or course pathway, not a raw table. Color may reinforce the four explicit progression roles, but every role must also have a text label or distinct symbol so the view remains accessible and printable.

Explicit mappings should use prominent markers. Carried-forward availability should use a lighter connecting line, background band, or outlined marker so it is visible without competing with actual curriculum events.

Selecting a course occurrence should reveal the associated learning objectives and relationship details. This lets the overview remain readable while preserving access to the full mapping.

## Example

For `SK-TRI-TRIG-SOLVE-SIDE`, a teacher should be able to see at a glance that the skill is introduced in Math 22 and later deepened and applied in Math 32, with links to the specific objectives responsible for each designation.
