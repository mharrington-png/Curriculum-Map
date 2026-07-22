from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "data" / "courses"
AUDIT_DIR = ROOT / "data" / "audits"
REPORT_PATH = AUDIT_DIR / "BLOOM_ACTION_VERB_AUDIT.md"
CSV_PATH = AUDIT_DIR / "BLOOM_ACTION_VERB_AUDIT.csv"
REFERENCE_PATH = ROOT / "source_documents" / "revised-blooms-taxonomy-action-verbs.pdf"

LEVELS = {
    1: "Remembering",
    2: "Understanding",
    3: "Applying",
    4: "Analyzing",
    5: "Evaluating",
    6: "Creating",
}

# Transcribed from the visually verified one-page PDF in source_documents.
# The handout contains a few nouns and question words; they are retained here
# because this lookup represents the source literally rather than an edited list.
REFERENCE_VERBS = {
    1: {
        "choose", "define", "find", "how", "label", "list", "match", "name",
        "omit", "recall", "relate", "select", "show", "spell", "tell", "what",
        "when", "where", "which", "who", "why",
    },
    2: {
        "classify", "compare", "contrast", "demonstrate", "explain", "extend",
        "illustrate", "infer", "interpret", "outline", "relate", "rephrase",
        "show", "summarize", "translate",
    },
    3: {
        "apply", "build", "choose", "construct", "develop", "experiment with",
        "identify", "interview", "make use of", "model", "organize", "plan",
        "select", "solve", "utilize",
    },
    4: {
        "analyze", "assume", "categorize", "classify", "compare", "conclusion",
        "contrast", "discover", "dissect", "distinguish", "divide", "examine",
        "function", "inference", "inspect", "list", "motive", "relationships",
        "simplify", "survey", "take part in", "test for", "theme",
    },
    5: {
        "agree", "appraise", "assess", "award", "choose", "compare", "conclude",
        "criteria", "criticize", "decide", "deduct", "defend", "determine",
        "disprove", "estimate", "evaluate", "explain", "importance", "influence",
        "interpret", "judge", "justify", "mark", "measure", "opinion", "perceive",
        "prioritize", "prove", "rate", "recommend", "rule on", "select", "support",
        "value",
    },
    6: {
        "adapt", "build", "change", "choose", "combine", "compile", "compose",
        "construct", "create", "delete", "design", "develop", "discuss", "elaborate",
        "estimate", "formulate", "happen", "imagine", "improve", "invent", "make up",
        "maximize", "minimize", "modify", "original", "originate", "plan", "predict",
        "propose", "solution", "solve", "suppose", "test", "theory",
    },
}


def parse_course(path: Path) -> list[dict[str, str]]:
    """Read the repository's constrained one-line objective YAML records."""
    text = path.read_text(encoding="utf-8")
    course_match = re.search(r"^  id: (M\d+)$", text, re.MULTILINE)
    if not course_match:
        raise ValueError(f"Course ID not found in {path}")
    course = course_match.group(1)
    unit = ""
    records: list[dict[str, str]] = []
    for line in text.splitlines():
        unit_match = re.match(r"  - id: (M\d+-[A-Z0-9]+)$", line)
        if unit_match:
            unit = unit_match.group(1)
            continue
        objective_match = re.match(
            r'\s+- \{id: ([^,]+), statement: "(.*)"\}', line
        )
        if objective_match:
            objective_id, statement = objective_match.groups()
            body = re.sub(r"^I can\s+", "", statement, flags=re.IGNORECASE)
            lead_match = re.match(r"([A-Za-z-]+)", body)
            if not lead_match:
                raise ValueError(f"Lead verb not found for {objective_id}")
            records.append(
                {
                    "course": course,
                    "unit": unit,
                    "objective_id": objective_id,
                    "statement": statement,
                    "body": body,
                    "lead_verb": lead_match.group(1).lower(),
                }
            )
    return records


def reference_levels(verb: str) -> list[int]:
    return [level for level, verbs in REFERENCE_VERBS.items() if verb in verbs]


def classify(record: dict[str, str]) -> tuple[int, str]:
    """Assign intended demand using the whole LO, not the lead verb in isolation."""
    verb = record["lead_verb"]
    body = record["body"].lower()

    if verb == "read" and any(
        phrase in body for phrase in ("distinguish", "identify the role")
    ):
        return 2, "interprets notation well enough to distinguish meanings or identify structural roles"

    if verb in {"recall", "read"}:
        return 1, "retrieves terminology, symbol meanings, or notation conventions from memory"

    if verb == "name":
        return 1, "retrieves and supplies established names or labels"

    # Evaluation means judgment against criteria here, not routine calculation.
    if verb == "evaluate":
        if any(term in body for term in ("model", "game", "risk", "decision", "fit")):
            return 5, "judges quality or consequences using evidence or criteria"
        return 3, "uses evaluate in the mathematical sense of compute or substitute"

    if verb in {"justify", "prove"}:
        return 5, "defends a conclusion with accepted criteria, definitions, or theorems"

    if verb == "compare":
        if any(term in body for term in ("model", "appropriate")):
            return 5, "compares alternatives to select or defend a model"
        return 4, "examines relationships, features, or long-run behavior"

    if verb in {"analyze", "decompose", "distinguish", "linearize", "organize"}:
        return 4, "breaks a structure into parts or examines relationships"

    if verb in {"choose", "select"}:
        if "model" in body:
            return 5, "selects a model using contextual or empirical criteria"
        return 4, "selects a method by analyzing the givens and target"

    if verb == "determine" and any(
        phrase in body
        for phrase in (
            "whether", "number of possible", "minimum possible degree", "where a combination",
        )
    ):
        return 4, "examines conditions or structure before reaching a conclusion"

    if verb == "estimate":
        return 4, "infers a value or structural feature from graphical or numerical evidence"

    if verb in {"connect", "verify", "resolve", "sketch"}:
        return 4, "examines or verifies relationships among representations and features"

    if verb == "construct":
        if any(
            term in body
            for term in (
                "function", "model", "argument", "from specified", "from two data points",
            )
        ):
            return 6, "produces a new function, model, or argument from constraints"
        return 3, "carries out a known construction or display procedure"

    if verb == "build":
        return 6, "produces and refines a mathematical model"

    if verb == "create":
        return 6, "produces a model or representation for a stated situation"

    if verb == "predict":
        return 4, "infers behavior from algebraic structure rather than inventing a product"

    if verb == "write" and any(
        term in body for term in ("parametric equations for motion",)
    ):
        return 6, "produces a model for a contextual situation"

    if verb in {
        "classify", "describe", "explain", "identify", "interpret", "match",
        "recognize", "relate", "represent", "state", "translate",
    }:
        return 2, "demonstrates meaning, classification, or relationships among representations"

    if verb == "express":
        return 3, "converts or records a mathematical result in a required form"

    if verb in {
        "add", "apply", "calculate", "convert", "determine", "divide", "eliminate",
        "evaluate", "expand", "factor", "find", "fit", "graph", "multiply", "perform",
        "plot", "rearrange", "rewrite", "simplify", "solve", "substitute", "use", "write",
    }:
        return 3, "carries out a mathematical procedure in a stated type of situation"

    raise ValueError(f"Unclassified lead verb {verb!r} in {record['objective_id']}")


def compound_action(record: dict[str, str]) -> bool:
    body = record["body"].lower()
    # Flag coordinated assessment demands, while avoiding conjunctions inside noun lists.
    action_words = {
        "analyze", "apply", "approximate", "build", "calculate", "check", "classify", "compare",
        "construct", "create", "describe", "determine", "distinguish", "evaluate",
        "decide", "divide", "explain", "express", "factor", "find", "fit", "graph", "identify",
        "interpret", "justify", "match", "measure", "model", "multiply", "name", "optimize",
        "plot", "predict", "present", "prove", "reject", "relate", "represent", "select",
        "simplify", "solve", "state", "subtract", "translate", "use", "verify", "write",
    }
    return any(re.search(rf"\band\s+{re.escape(word)}\b", body) for word in action_words)


def source_status(levels: list[int]) -> str:
    if not levels:
        return "not listed"
    if len(levels) == 1:
        return "unique"
    return "ambiguous"


def alignment_status(assigned: int, levels: list[int]) -> str:
    if not levels:
        return "context-inferred"
    if assigned in levels:
        return "source-consistent"
    return "context-adjusted"


def pct(part: int, whole: int) -> str:
    return f"{(100 * part / whole):.1f}%" if whole else "0.0%"


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return out


def build_report(records: list[dict[str, str]]) -> str:
    total = len(records)
    source_counts = Counter(record["reference_status"] for record in records)
    alignment_counts = Counter(record["alignment"] for record in records)
    compound_count = sum(record["compound_action"] == "yes" for record in records)
    level_counts = Counter(int(record["assigned_level"]) for record in records)

    lines = [
        "# Bloom Action-Verb Audit",
        "",
        f"Audit of the {total} learning objectives in the seven structured course files against "
        "`source_documents/revised-blooms-taxonomy-action-verbs.pdf`.",
        "",
        "## Executive Summary",
        "",
        f"- Objectives audited: {total}",
        f"- Lead verbs that have one literal level in the reference: {source_counts['unique']} "
        f"({pct(source_counts['unique'], total)})",
        f"- Lead verbs that the reference places in multiple levels: {source_counts['ambiguous']} "
        f"({pct(source_counts['ambiguous'], total)})",
        f"- Lead verbs absent from the reference: {source_counts['not listed']} "
        f"({pct(source_counts['not listed'], total)})",
        f"- Objectives whose contextual classification is consistent with at least one listed "
        f"level: {alignment_counts['source-consistent']} ({pct(alignment_counts['source-consistent'], total)})",
        f"- Objectives needing a context adjustment despite a literal reference match: "
        f"{alignment_counts['context-adjusted']} ({pct(alignment_counts['context-adjusted'], total)})",
        f"- Objectives with coordinated assessment actions: {compound_count} ({pct(compound_count, total)})",
        "",
        "**Overall finding.** The objectives are generally observable and assessable, but the handout "
        "does not function as a one-verb/one-level dictionary. Mathematics changes the meaning of several "
        "verbs: *evaluate* usually means calculate, and *determine* usually means carry out a procedure, "
        "even though the handout lists both only under Evaluating. The strongest improvement opportunity is "
        "to clarify broad verbs such as *use* and to split objectives that bundle several independently "
        "assessable actions.",
        "",
        "## Context-Aware Bloom Distribution",
        "",
    ]
    distribution_rows = [
        [f"{level}. {LEVELS[level]}", str(level_counts[level]), pct(level_counts[level], total)]
        for level in LEVELS
    ]
    lines.extend(markdown_table(["Bloom level", "Objectives", "Share"], distribution_rows))
    lines.extend(["", "### By course", ""])
    course_rows: list[list[str]] = []
    for course in sorted({record["course"] for record in records}, key=lambda item: int(item[1:])):
        course_records = [record for record in records if record["course"] == course]
        counts = Counter(int(record["assigned_level"]) for record in course_records)
        course_rows.append(
            [course, str(len(course_records))]
            + [f"{counts[level]} ({pct(counts[level], len(course_records))})" for level in LEVELS]
        )
    lines.extend(
        markdown_table(
            ["Course", "LOs", "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"],
            course_rows,
        )
    )
    higher_by_course: dict[str, tuple[int, int]] = {}
    for course in sorted({record["course"] for record in records}, key=lambda item: int(item[1:])):
        course_records = [record for record in records if record["course"] == course]
        higher = sum(int(record["assigned_level"]) >= 4 for record in course_records)
        higher_by_course[course] = (higher, len(course_records))
    lines.extend(
        [
            "",
            "### Interpretation",
            "",
            f"- Applying is the center of gravity: {level_counts[3]} objectives ({pct(level_counts[3], total)}). "
            "That is appropriate for performance-oriented mathematics objectives, but it means task design must "
            "carry much of the differentiation in complexity.",
            f"- Remembering is explicit in {level_counts[1]} objectives ({pct(level_counts[1], total)}), primarily "
            "through terminology and notation outcomes. These establish the language base for later performance "
            "objectives without treating recall as a quota.",
            f"- The share at Analyzing or above rises from {pct(higher_by_course['M12'][0], higher_by_course['M12'][1])} "
            f"in M12 to {pct(higher_by_course['M49'][0], higher_by_course['M49'][1])} in M49, so the overall sequence "
            "does show increasing cognitive demand.",
            f"- Evaluating is explicit in only {level_counts[5]} objectives ({pct(level_counts[5], total)}). If model "
            "critique, proof evaluation, or comparison against criteria is a program goal, this is the clearest "
            "area for intentional expansion.",
        ]
    )

    lines.extend(
        [
            "",
            "## Reference-Lookup Findings",
            "",
            "The literal lookup is reported separately from the contextual assignment. This prevents the "
            "handout's overlaps from being mistaken for errors and makes mathematical uses visible.",
            "",
        ]
    )
    verb_records: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        verb_records[record["lead_verb"]].append(record)
    inventory_rows: list[list[str]] = []
    for verb, matches in sorted(verb_records.items(), key=lambda item: (-len(item[1]), item[0])):
        levels = reference_levels(verb)
        assigned = Counter(int(match["assigned_level"]) for match in matches)
        assigned_text = ", ".join(f"{LEVELS[level]} {count}" for level, count in sorted(assigned.items()))
        reference_text = ", ".join(LEVELS[level] for level in levels) if levels else "Not listed"
        inventory_rows.append([verb, str(len(matches)), reference_text, assigned_text])
    lines.extend(markdown_table(["Lead verb", "Count", "Reference level(s)", "Context assignment(s)"], inventory_rows))

    false_friends = [
        record for record in records
        if record["alignment"] == "context-adjusted"
    ]
    lines.extend(
        [
            "",
            "## High-Priority Review: Literal Match Misstates the Mathematical Demand",
            "",
            "These objectives use a verb found in the handout, but the whole statement indicates a different "
            "cognitive demand. They are not automatically flawed; they are the cases most likely to be "
            "misclassified by a simple keyword audit.",
            "",
        ]
    )
    false_rows = [
        [
            record["objective_id"],
            record["lead_verb"],
            ", ".join(LEVELS[level] for level in reference_levels(record["lead_verb"])),
            record["assigned_level_name"],
            record["statement"].replace("|", "\\|"),
        ]
        for record in false_friends
    ]
    lines.extend(markdown_table(["Objective", "Verb", "Reference", "Context", "Learning objective"], false_rows))

    broad_verbs = {"determine", "use", "write", "perform", "find"}
    broad_records = [record for record in records if record["lead_verb"] in broad_verbs]
    broad_counts = Counter(record["lead_verb"] for record in broad_records)
    lines.extend(
        [
            "",
            "## Wording Review Candidates",
            "",
            "### Broad lead verbs",
            "",
            "These verbs can be valid, but they disclose less about the student performance than the object "
            "that follows them. Revise only where the assessment method is not already obvious.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Verb", "Count", "Revision guidance"],
            [
                ["determine", str(broad_counts["determine"]), "Name the observable method when more than one method or representation is possible."],
                ["use", str(broad_counts["use"]), "Replace with the resulting performance: solve, graph, justify, calculate, or model."],
                ["write", str(broad_counts["write"]), "Keep for notation/formula production; specify derive or model when originality is intended."],
                ["perform", str(broad_counts["perform"]), "Name the operation or mathematical product directly."],
                ["find", str(broad_counts["find"]), "Prefer determine, solve, calculate, or derive when the method matters."],
            ],
        )
    )

    compound_records = [record for record in records if record["compound_action"] == "yes"]
    lines.extend(
        [
            "",
            "### Coordinated actions",
            "",
            f"{len(compound_records)} objectives contain a second coordinated action that may require a "
            "different assessment. Keep the compound form when the actions are inseparable; otherwise split "
            "the objective or make the higher-demand action explicit.",
            "",
        ]
    )
    compound_rows = [
        [record["objective_id"], record["assigned_level_name"], record["statement"].replace("|", "\\|")]
        for record in compound_records
    ]
    lines.extend(markdown_table(["Objective", "Assigned level", "Learning objective"], compound_rows))

    lines.extend(
        [
            "",
            "## Recommended Next Pass",
            "",
            "1. Keep clear mathematical performance verbs such as *calculate*, *graph*, *solve*, and *write* "
            "even when the handout omits them; they are observable and usually Applying.",
            "2. Review *evaluate* and *determine* in context rather than labeling them Evaluating automatically.",
            "3. Replace broad *use* objectives where the expected student product is not obvious.",
            "4. Review coordinated-action objectives for assessment burden and split only when each action "
            "needs independent evidence.",
            "5. If intentional course-level targets are adopted later, compare each unit's distribution with "
            "those targets; this audit describes current demand but does not impose quotas by Bloom level.",
            "",
            "## Method and Limits",
            "",
            "- Source of truth: `data/courses/math12.yaml` through `math49.yaml`.",
            "- Unit of analysis: the first action verb after *I can*. Coordinated actions are flagged separately.",
            "- Literal source lookup: exact, case-normalized match to the verified PDF verb columns.",
            "- Context assignment: the complete objective determines intended cognitive demand. Routine "
            "calculation and representation are Applying; structural comparison is Analyzing; judgment against "
            "criteria is Evaluating; production of a new model/function/argument is Creating.",
            "- Bloom level is not a difficulty rating. A demanding calculation can still be Applying, and an "
            "accessible model-design task can be Creating.",
            "- Verb-only analysis cannot confirm assessment alignment. Tasks, prompts, and scoring criteria "
            "must be reviewed to verify the enacted level.",
            "- The full objective-level record is in `data/audits/BLOOM_ACTION_VERB_AUDIT.csv`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(REFERENCE_PATH)
    records: list[dict[str, str]] = []
    for course_path in sorted(COURSE_DIR.glob("math*.yaml")):
        records.extend(parse_course(course_path))

    for record in records:
        levels = reference_levels(record["lead_verb"])
        assigned_level, rationale = classify(record)
        record.update(
            {
                "reference_status": source_status(levels),
                "reference_levels": "; ".join(
                    f"{level}. {LEVELS[level]}" for level in levels
                ) or "not listed",
                "assigned_level": str(assigned_level),
                "assigned_level_name": LEVELS[assigned_level],
                "alignment": alignment_status(assigned_level, levels),
                "compound_action": "yes" if compound_action(record) else "no",
                "rationale": rationale,
            }
        )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "course", "unit", "objective_id", "statement", "lead_verb", "reference_status",
        "reference_levels", "assigned_level", "assigned_level_name", "alignment",
        "compound_action", "rationale",
    ]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    REPORT_PATH.write_text(build_report(records), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {CSV_PATH}")
    print(f"Audited {len(records)} objectives")


if __name__ == "__main__":
    main()
