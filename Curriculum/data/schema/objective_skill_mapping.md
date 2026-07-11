# Objective-to-Skill Mapping Schema

Each mapping record connects one objective to one or more canonical supporting skills.

## Required Fields

- `objective_id`: Existing course objective ID
- `skills`: Nonempty list of skill relationships
- `skill_id`: Active canonical skill ID
- `relationship`: `prerequisite`, `required`, or `method-dependent`
- `progression`: `introduce`, `reinforce`, `deepen`, or `apply`

## Optional Fields

- `notes`: Clarifies scope, representation, or method
- `evidence`: Department source supporting the mapping
- `confidence`: `high`, `medium`, or `low`

## Interpretation

- **Prerequisite:** Expected before work on the objective begins
- **Required:** Inherent in successfully meeting the objective
- **Method-dependent:** Needed for one accepted approach but not every approach
- **Introduce:** First sustained instruction in the mapped course sequence
- **Reinforce:** Revisit at comparable depth
- **Deepen:** Increase abstraction, representation, independence, or complexity
- **Apply:** Use as a tool inside a different objective

## Derived Toolkit Availability

After a skill is introduced or designated as inherited, it is assumed to remain available in the student toolkit in later courses unless the curriculum explicitly retires or replaces it.

This carried-forward availability is derived from course sequence and is not stored as an objective-to-skill mapping. It does not mean that every later course explicitly teaches, assesses, or uses the skill in a named objective. Interfaces and reports must visually distinguish carried-forward availability from the four explicit progression values.

An objective may map to several skills. A broad classroom task should reference multiple precise skills rather than create a broad duplicate skill.
