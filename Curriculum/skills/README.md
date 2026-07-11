# Supporting Skills Library

This directory is the canonical supporting-skills library. Each active skill ID is defined exactly once in the domain file that owns it.

## Domain Ownership

| Canonical file | Primary scope | First major course source |
|---|---|---|
| `FOUNDATIONAL_ALGEBRA_SKILLS.md` | Numerical fluency, equations, inequalities, lines, basic functions, systems, basic polynomials | Math 12 |
| `INTERMEDIATE_ALGEBRA_SKILLS.md` | Function interpretation, factoring, rational expressions, radicals, quadratics, complex numbers | Math 21 |
| `GEOMETRY_SKILLS.md` | Diagram reading, proof, congruence, similarity, right triangles, quadrilaterals, circles | Math 22 |
| `ADVANCED_ALGEBRA_SKILLS.md` | Piecewise functions, transformations, composition, inverses, exponentials, logarithms, modeling | Math 31 |
| `TRIGONOMETRY_SKILLS.md` | Angles, unit circle, periodic graphs, trigonometric equations and identities, polar/vector/parametric skills | Math 32 |
| `PRECALCULUS_SKILLS.md` | Advanced function analysis, polynomial/rational behavior, limits, sequences, and series | Math 49 |

## Cross-Course Documents

- [`SKILL_ALIASES.md`](SKILL_ALIASES.md) records retired duplicate IDs and their canonical replacements.
- [`../mappings/SKILL_SPIRAL_MAP.md`](../mappings/SKILL_SPIRAL_MAP.md) shows how major skill families recur and deepen across courses.

## Rules

1. Define each skill ID in exactly one canonical domain file.
2. Later courses reuse earlier IDs rather than creating course-specific synonyms.
3. Create a new skill only when it names a distinct, observable supporting ability.
4. Keep skills smaller than learning objectives.
5. Record any retired or merged ID in `SKILL_ALIASES.md`.
