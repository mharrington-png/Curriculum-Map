"""Build a one-primary-section OpenStax link manifest for the curriculum site.

The generator reads the canonical course YAML, the existing section crosswalks,
and the exact HTML files served by the local OpenStax Viewer.  It deliberately
leaves an objective unmatched when none of the available Viewer sections is an
honest instructional match.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER_SECTIONS = Path(r"C:\Users\mikeg\Documents\OpenStax Viewer\sections")
OUTPUT = ROOT / "data" / "resources" / "openstax_objective_links.json"
PUBLIC_OUTPUT = ROOT / "ui" / "public" / "data" / "openstax_objective_links.json"
REPORT = ROOT / "data" / "audits" / "OPENSTAX_OBJECTIVE_LINK_AUDIT.md"
VIEWER_BASE = "https://mathclass.today/OpenStax-Viewer"
IN_SCOPE = ("M12", "M21", "M31", "M39", "M49")

BOOKS = {
    "intermediate-algebra-2e": "Intermediate Algebra 2e",
    "college-algebra-2e": "College Algebra 2e",
    "precalculus-2e": "Precalculus 2e",
    "calculus-v1": "Calculus Volume 1",
    "calculus-v3": "Calculus Volume 3",
}

COURSE_BOOK = {
    "M12": "intermediate-algebra-2e",
    "M21": "intermediate-algebra-2e",
    "M31": "college-algebra-2e",
    "M49": "precalculus-2e",
}


@dataclass
class Candidate:
    book_id: str
    section: str
    alignment: str
    source: str


class SectionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.active_tag: str | None = None
        self.active_id: str | None = None
        self.buffer: list[str] = []
        self.headings: list[dict[str, str | None]] = []
        self.all_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.active_tag = tag
            self.active_id = dict(attrs).get("id")
            self.buffer = []

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self.active_tag:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self.active_tag:
            return
        text = " ".join("".join(self.buffer).split())
        if text:
            self.headings.append({"level": tag, "text": text, "anchor": self.active_id})
        self.active_tag = None
        self.active_id = None
        self.buffer = []


STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "can", "for", "from", "given", "i",
    "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their",
    "to", "using", "with", "whether", "where", "write", "determine", "identify",
    "interpret", "calculate", "construct", "create", "solve", "evaluate", "apply",
    "analyze", "explain", "use", "find", "graph", "express", "state", "recognize",
}


def tokens(text: str) -> set[str]:
    words = set(re.findall(r"[a-z][a-z0-9-]+", text.casefold()))
    return {word.rstrip("s") for word in words if word not in STOPWORDS and len(word) > 2}


def overlap_score(left: set[str], right: set[str]) -> int:
    """Count exact and conservative shared word stems for evidence routing."""
    return sum(
        1 for word in left
        if any(word == other or (len(word) >= 5 and len(other) >= 5 and word[:5] == other[:5]) for other in right)
    )


def parse_sections() -> dict[tuple[str, str], dict]:
    catalog = {}
    for book_id in BOOKS:
        directory = VIEWER_SECTIONS / book_id
        if not directory.exists():
            continue
        for path in directory.glob("*.html"):
            parser = SectionParser()
            parser.feed(path.read_text(encoding="utf-8"))
            section = path.stem.replace("-", ".")
            h1 = next((h["text"] for h in parser.headings if h["level"] == "h1"), section)
            title = re.sub(rf"^Section\s+{re.escape(section)}\s*", "", h1)
            title = re.sub(rf"^{re.escape(section)}\s*", "", title).strip()
            useful_headings = [
                h for h in parser.headings
                if h["level"] in {"h2", "h3"}
                and h["text"] not in {"Key Concepts", "Section Exercises", "Glossary"}
            ]
            catalog[(book_id, section)] = {
                "title": title,
                "headings": useful_headings,
                "text": " ".join(" ".join(parser.all_text).split()),
                "local_file": str(path),
            }
    return catalog


def parse_courses() -> tuple[list[dict], list[dict]]:
    included, excluded = [], []
    unit_id = unit_title = priority = ""
    for path in sorted((ROOT / "data" / "courses").glob("math*.yaml")):
        course_id = "M" + re.search(r"math(\d+)", path.stem).group(1)
        target = included if course_id in IN_SCOPE else excluded
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"  - id: (M\d+-[A-Z]+)$", line)
            if match:
                unit_id = match.group(1)
            match = re.match(r"    title: (.+)$", line)
            if match:
                unit_title = match.group(1)
            match = re.match(r"    priority: (.+)$", line)
            if match:
                priority = match.group(1)
            match = re.search(r'\{id: (M\d+-[A-Z]+-\d{3}), statement: "([^"]+)"\}', line)
            if match:
                target.append({
                    "course_id": course_id,
                    "unit_id": unit_id,
                    "unit_title": unit_title,
                    "priority": priority,
                    "objective_id": match.group(1),
                    "objective": match.group(2),
                })
    return included, excluded


def expand_references(text: str, valid_ids: set[str]) -> list[str]:
    found = []
    pattern = re.compile(r"(M\d+-[A-Z]+-)(\d{3})\s+through\s+(?:M\d+-[A-Z]+-)?(\d{3})")
    for match in pattern.finditer(text):
        prefix, start, end = match.groups()
        found.extend(f"{prefix}{number:03d}" for number in range(int(start), int(end) + 1))
    text = pattern.sub("", text)
    found.extend(re.findall(r"M\d+-[A-Z]+-\d{3}", text))
    return [item for item in dict.fromkeys(found) if item in valid_ids]


def normalize_alignment(value: str) -> str:
    value = value.casefold()
    if "direct" in value and "partial" not in value and "support" not in value:
        return "direct"
    if "partial" in value or "direct" in value:
        return "partial"
    return "supporting"


def parse_crosswalk_candidates(valid_ids: set[str]) -> dict[str, list[Candidate]]:
    result: dict[str, list[Candidate]] = defaultdict(list)
    for course_id, default_book in COURSE_BOOK.items():
        path = ROOT / "mappings" / "openstax" / f"MATH{course_id[1:]}_OPENSTAX_MAP.md"
        current_book = default_book
        in_crosswalk = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## Detailed Resource Crosswalk: Calculus Volume 1"):
                current_book = "calculus-v1"
                in_crosswalk = True
                continue
            if line.startswith((
                "## Detailed Section-to-Objective Crosswalk",
                "## Detailed Section Crosswalk",
                "## Extension Section Crosswalk",
            )):
                current_book = default_book
                in_crosswalk = True
                continue
            if line.startswith("## "):
                in_crosswalk = False
                continue
            if not in_crosswalk or not line.startswith("|") or re.match(r"\|\s*-", line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 4 or not re.fullmatch(r"\d+\.\d+", cells[0]):
                continue
            for objective_id in expand_references(cells[2], valid_ids):
                candidate = Candidate(
                    current_book, cells[0], normalize_alignment(cells[3]), path.name
                )
                if candidate not in result[objective_id]:
                    result[objective_id].append(candidate)
    return result


# Overrides fill objectives absent from the legacy detailed crosswalks and provide
# the first content-audited draft for Math 39.  A None book means that the current
# five-book Viewer library has no honest section match.
OVERRIDES: dict[str, tuple[str | None, str | None, str, bool, str]] = {
    "M12-REV-001": ("intermediate-algebra-2e", "1.1", "direct", False, "Order of operations is an explicit section outcome."),
    "M12-REV-002": ("intermediate-algebra-2e", "1.3", "partial", True, "Fraction operations are direct, while signed-integer operations are taught separately in section 1.2."),
    "M12-REV-003": ("intermediate-algebra-2e", "1.1", "direct", False, "Identifying and combining like terms is explicit."),
    "M12-REV-005": ("intermediate-algebra-2e", "1.1", "direct", False, "Prime factorization is explicit."),
    "M12-EQN-004": ("intermediate-algebra-2e", "2.2", "direct", False, "The section translates verbal relationships into equations as part of its problem-solving strategy."),
    "M12-EQN-005": ("intermediate-algebra-2e", "2.4", "partial", True, "Mixture and motion models are direct; number problems are taught separately in section 2.2."),
    "M12-INE-001": ("intermediate-algebra-2e", "2.5", "direct", False, "Solving and graphing one-variable linear inequalities is explicit."),
    "M12-INE-005": ("intermediate-algebra-2e", "2.7", "direct", False, "Solving absolute-value equations is explicit."),
    "M12-LIN-001": ("intermediate-algebra-2e", "3.2", "direct", False, "Finding and interpreting slope is explicit."),
    "M12-LIN-009": ("intermediate-algebra-2e", "3.5", "partial", False, "Domain and range are explicit, but contextual restrictions need selected examples."),
    "M12-SYS-005": ("intermediate-algebra-2e", "4.2", "direct", False, "Creating and solving systems for applications is the section focus."),
    "M12-POL-001": ("intermediate-algebra-2e", "5.2", "direct", False, "Integer exponent rules are explicit."),
    "M12-POL-004": ("intermediate-algebra-2e", "5.4", "direct", False, "Division of a polynomial by a monomial is explicit."),
    "M12-POL-005": ("intermediate-algebra-2e", "6.1", "direct", False, "Factoring a greatest common factor is explicit."),
    "M12-EXT-001": ("intermediate-algebra-2e", "2.7", "direct", False, "Solving and graphing absolute-value inequalities is explicit."),
    "M12-EXT-002": ("intermediate-algebra-2e", "4.7", "direct", False, "Graphing systems of linear inequalities and their solution regions is explicit."),
    "M12-EXT-003": ("intermediate-algebra-2e", "6.2", "direct", False, "Section 6.2, rather than 6.1, explicitly teaches factoring quadratic trinomials."),
    "M12-EXT-004": ("precalculus-2e", "1.2", "partial", False, "The section explicitly contrasts a discrete contextual function with a continuous treatment, but only briefly."),

    "M21-REV-003": ("college-algebra-2e", "4.1", "direct", False, "The section models real-world problems with linear functions."),
    "M21-FUN-001": ("intermediate-algebra-2e", "3.5", "partial", True, "Formula and tabular evaluation are direct; graph-based evaluation is developed in section 3.6."),
    "M21-FUN-002": ("intermediate-algebra-2e", "3.5", "direct", False, "Determining whether a relation is a function is explicit."),
    "M21-FUN-003": ("intermediate-algebra-2e", "3.5", "direct", False, "Finding domain and range is explicit."),
    "M21-FUN-004": ("intermediate-algebra-2e", "3.5", "direct", False, "Function input-output evaluation supports solving for a requested input."),
    "M21-FUN-005": ("intermediate-algebra-2e", "3.5", "partial", False, "Inputs, outputs, domain, and range are explicit; contextual interpretation depends on selected examples."),
    "M21-POL-003": ("intermediate-algebra-2e", "6.1", "direct", False, "Factoring out a greatest common factor is explicit."),
    "M21-RAT-001": ("intermediate-algebra-2e", "7.1", "direct", False, "Undefined values and restrictions are explicit."),
    "M21-RAT-002": ("intermediate-algebra-2e", "7.1", "direct", False, "Simplification with restrictions is explicit."),
    "M21-RAT-003": ("intermediate-algebra-2e", "7.1", "direct", False, "Multiplication and division of rational expressions are explicit."),
    "M21-RAT-004": ("intermediate-algebra-2e", "7.2", "direct", False, "Addition and subtraction with common denominators are explicit."),
    "M21-RAT-005": ("intermediate-algebra-2e", "7.4", "direct", False, "Solving rational equations and checking restrictions are explicit."),
    "M21-EXP-003": ("intermediate-algebra-2e", "8.2", "direct", False, "Simplifying radical expressions is explicit."),
    "M21-QUAD-001": ("intermediate-algebra-2e", "9.6", "direct", False, "The section identifies the principal features of quadratic graphs."),
    "M21-QUAD-002": ("intermediate-algebra-2e", "9.7", "partial", True, "Vertex form and transformations are direct, while factored-form features draw on sections 6.5 and 9.6."),
    "M21-QUAD-006": ("intermediate-algebra-2e", "9.3", "direct", False, "The quadratic formula is explicit."),
    "M21-QUAD-007": ("intermediate-algebra-2e", "9.3", "direct", False, "The section explicitly asks students to identify the most appropriate solution method."),
    "M21-QUAD-008": ("intermediate-algebra-2e", "9.6", "direct", False, "Graphing from vertex, intercepts, and symmetry is explicit."),
    "M21-EXT-002": ("intermediate-algebra-2e", "9.3", "direct", False, "The section uses the discriminant and quadratic formula to express nonreal solutions."),
    "M21-FUN-006": ("college-algebra-2e", "3.3", "direct", False, "Average rate of change is an explicit section outcome."),
    "M21-FUN-007": ("intermediate-algebra-2e", "3.5", "partial", False, "Intermediate Algebra 3.5 introduces relations and functions across representations; College Algebra 3.1 and 4.1 provide supplemental comparison contexts."),
    "M21-POL-006": ("intermediate-algebra-2e", "6.5", "direct", False, "The section uses the zero-product property to find polynomial solutions."),
    "M21-EXP-005": ("intermediate-algebra-2e", "8.6", "partial", True, "Radical equations are direct; equations stated in rational-exponent form also draw on section 8.3."),
    "M21-QUAD-003": ("intermediate-algebra-2e", "6.5", "direct", False, "Solving quadratic equations by factoring is explicit."),
    "M21-EXT-001": ("intermediate-algebra-2e", "8.8", "direct", False, "The section teaches basic complex-number arithmetic."),
    "M31-REV-001": ("intermediate-algebra-2e", "2.2", "direct", False, "Percent applications and percent change are taught in the section."),
    "M31-REV-002": ("intermediate-algebra-2e", "5.2", "direct", False, "Exponent properties are the central section topic."),
    "M31-REV-003": ("intermediate-algebra-2e", "5.1", "direct", False, "The section defines polynomial terms, coefficients, and degree."),
    "M31-REV-004": ("intermediate-algebra-2e", "5.3", "direct", False, "The section explicitly multiplies binomials."),
    "M31-FUN-005": ("college-algebra-2e", "3.2", "direct", False, "Graphing piecewise-defined functions is explicit."),
    "M31-FUN-006": ("college-algebra-2e", "3.2", "partial", False, "The section graphs piecewise formulas but gives limited practice constructing formulas from graphs; this coverage is accepted."),
    "M31-EXP-010": ("college-algebra-2e", "6.1", "direct", False, "The section develops continuous exponential models in base e and identifies their continuous growth or decay rates."),
    "M31-LOG-011": ("college-algebra-2e", "6.7", "direct", False, "The section explicitly expresses exponential models in base e."),
    "M31-EXT-002": ("college-algebra-2e", "3.5", "direct", False, "Determining even and odd functions is explicit."),
    "M31-EXT-003": ("college-algebra-2e", "6.7", "partial", False, "Section 6.7 provides contextual exponential and logarithmic models that support interpretation of logarithmic scales."),
    "M31-LIN-001": ("college-algebra-2e", "3.1", "direct", False, "Function notation and input-output meaning are explicit."),
    "M31-LIN-002": ("college-algebra-2e", "3.1", "direct", False, "Tests for whether a relation is a function are explicit."),
    "M31-LIN-003": ("college-algebra-2e", "3.1", "direct", False, "Finding inputs and outputs from functions is explicit."),
    "M31-LIN-004": ("college-algebra-2e", "3.1", "direct", False, "The section frames functions in terms of independent inputs and dependent outputs."),
    "M31-LIN-005": ("college-algebra-2e", "3.3", "direct", False, "Average rate of change is explicit."),
    "M31-LIN-007": ("college-algebra-2e", "3.3", "partial", False, "Average rate is explicit; recovering total change is an application of the definition rather than a separate outcome."),
    "M31-LIN-008": ("college-algebra-2e", "3.3", "partial", False, "Average rate is explicit, while dimensional interpretation of units needs selected examples."),
    "M31-LIN-011": ("intermediate-algebra-2e", "4.1", "direct", False, "Intersections of two linear relationships are solved graphically and algebraically."),
    "M31-FUN-001": ("college-algebra-2e", "3.1", "direct", False, "Determining whether a relation is a function is explicit."),
    "M31-FUN-002": ("college-algebra-2e", "3.1", "direct", False, "Function evaluation is explicit."),
    "M31-FUN-007": ("college-algebra-2e", "3.5", "direct", False, "Shifts, reflections, stretches, and compressions are explicit."),
    "M31-FUN-008": ("college-algebra-2e", "3.5", "partial", False, "Transformations are explicit; their effects on all domains, ranges, and asymptotes require synthesis."),
    "M31-FUN-009": ("college-algebra-2e", "3.4", "direct", False, "Evaluating composite functions is explicit."),
    "M31-FUN-010": ("college-algebra-2e", "3.4", "direct", False, "Creating formulas by composition is explicit."),
    "M31-FUN-011": ("college-algebra-2e", "3.7", "direct", False, "Finding inverse functions algebraically is explicit."),
    "M31-FUN-012": ("college-algebra-2e", "3.7", "direct", False, "Finding and evaluating inverses from formulas and graphs is explicit."),
    "M31-FUN-013": ("college-algebra-2e", "3.7", "partial", False, "Inverse meaning is explicit, but systematic units analysis is not a section outcome; this coverage is accepted."),
    "M31-FUN-014": ("college-algebra-2e", "3.7", "direct", False, "The domain-range reversal for inverse functions is explicit."),
    "M31-FUN-015": ("college-algebra-2e", "3.7", "direct", False, "The inverse domain-range relationship directly supports this reasoning."),
    "M31-FUN-016": ("college-algebra-2e", "3.7", "direct", False, "Verifying inverse functions is explicit."),
    "M31-FUN-017": ("college-algebra-2e", "3.4", "direct", False, "The section explicitly interprets meaningful composition and compatible units."),
    "M31-FUN-018": ("college-algebra-2e", "3.3", "partial", False, "Average rates and increasing/decreasing behavior are taught; a supplement is necessary for concavity from changing average rates."),
    "M31-FUN-019": ("college-algebra-2e", "3.7", "direct", False, "Invertibility and the horizontal line test are explicit."),
    "M31-FUN-020": ("college-algebra-2e", "3.7", "direct", False, "Inverse graphs as reflections across y=x are explicit."),
    "M31-QUAD-001": ("college-algebra-2e", "5.1", "direct", False, "Vertex, intercepts, axis, and opening direction are explicit."),
    "M31-QUAD-002": ("college-algebra-2e", "5.1", "partial", True, "General and vertex forms are explicit; factored-form interpretation relies on polynomial graph work in section 5.3."),
    "M31-QUAD-003": ("college-algebra-2e", "5.1", "direct", False, "The section rewrites and uses quadratic forms to reveal graph features."),
    "M31-QUAD-005": ("college-algebra-2e", "5.1", "direct", False, "Graphing from algebraic structure and key features is explicit."),
    "M31-QUAD-006": ("college-algebra-2e", "5.1", "partial", True, "Constructing from a vertex or graph is direct; constructing from specified zeros draws on section 5.3."),
    "M31-QUAD-007": ("college-algebra-2e", "5.1", "direct", False, "Projectile trajectories and their interpretation are explicit."),
    "M31-EXP-002": ("college-algebra-2e", "6.1", "direct", False, "Initial value and growth or decay factors are explicit in exponential equations."),
    "M31-EXP-001": ("college-algebra-2e", "6.1", "direct", False, "The section explicitly contrasts constant additive linear change with constant multiplicative exponential change."),
    "M31-EXP-003": ("college-algebra-2e", "6.1", "direct", False, "Constructing exponential functions from data is explicit."),
    "M31-EXP-004": ("college-algebra-2e", "6.1", "direct", False, "Evaluating and interpreting exponential models is explicit."),
    "M31-EXP-005": ("college-algebra-2e", "6.1", "direct", False, "Periodic compound interest is explicit."),
    "M31-EXP-006": ("college-algebra-2e", "6.1", "direct", False, "Continuous growth and continuous compounding are explicit."),
    "M31-EXP-007": ("college-algebra-2e", "6.1", "direct", False, "Finding an exponential equation from sufficient data is explicit."),
    "M31-EXP-009": ("college-algebra-2e", "6.1", "partial", False, "Growth factors are explicit; comparing two models needs selected exercises."),
    "M31-LOG-004": ("college-algebra-2e", "6.6", "direct", False, "Solving exponential equations with logarithms is explicit."),
    "M31-LOG-005": ("college-algebra-2e", "6.6", "direct", False, "Solving logarithmic equations and checking restrictions are explicit."),
    "M31-LOG-009": ("college-algebra-2e", "6.6", "direct", False, "Multi-step exponential and logarithmic equations are explicit."),
    "M31-LOG-010": ("college-algebra-2e", "6.6", "partial", True, "Algebraic intersections are direct; graphical intersections require selected graphing work."),
    "M31-LOG-008": ("college-algebra-2e", "6.3", "direct", False, "The section explicitly presents logarithmic and exponential forms as equivalent inverse relationships."),
    "M49-FND-003": ("precalculus-2e", "1.5", "direct", False, "Determining even and odd functions is explicit."),
    "M49-FND-004": ("precalculus-2e", "4.1", "partial", True, "Equations and contextual exponential behavior are direct; a full graph analysis is developed separately in section 4.2."),
    "M49-FND-005": ("precalculus-2e", "4.3", "partial", True, "Logarithmic equations and meaning are direct; a full graph analysis is developed separately in section 4.4."),
    "M49-FND-006": ("precalculus-2e", "4.6", "direct", False, "Solving exponential and logarithmic equations using equivalent forms and logarithm properties is explicit."),
    "M49-CON-003": ("precalculus-2e", "10.1", "partial", True, "Implicit circle equations and graphs are direct; parametric circle equations require section 8.6."),
    "M49-OPS-005": ("precalculus-2e", "1.7", "direct", False, "One-to-one restrictions and inverse existence are explicit."),
    "M49-OPS-006": ("precalculus-2e", "1.7", "direct", False, "Finding and verifying inverses algebraically is explicit."),
    "M49-OPS-007": ("precalculus-2e", "1.7", "direct", False, "The relationship between functions and inverse graphs is explicit."),
    "M49-PWR-001": ("precalculus-2e", "3.3", "direct", False, "Identifying power functions and their parameters is explicit."),
    "M49-PWR-002": ("precalculus-2e", "3.9", "direct", False, "Constructing proportional power relationships is explicit."),
    "M49-PWR-003": ("precalculus-2e", "3.3", "direct", False, "Power-function shape and end behavior are explicit."),
    "M49-PWR-004": ("precalculus-2e", "3.9", "direct", False, "Direct, inverse, and joint variation are explicit."),
    "M49-PWR-005": ("college-algebra-2e", "2.6", "direct", False, "Solving equations involving rational exponents is explicit."),
    "M49-PWR-007": ("precalculus-2e", "3.9", "direct", False, "Variation models and parameter interpretation are the section focus."),
    "M49-PWR-008": ("precalculus-2e", "3.8", "partial", False, "Sections 3.8 and 3.3 provide partial coverage of fractional-power domains, shapes, and near-zero behavior."),
    "M49-ALG-002": ("precalculus-2e", "3.4", "direct", False, "Polynomial end behavior from degree and leading coefficient is explicit."),
    "M49-ALG-003": ("precalculus-2e", "3.4", "direct", False, "Zeros and multiplicities are explicit."),
    "M49-ALG-005": ("precalculus-2e", "3.4", "direct", False, "Graphing with intercepts, multiplicity, and end behavior is explicit."),
    "M49-POL-001": ("precalculus-2e", "3.4", "partial", False, "Sections 3.4 and 3.6 support polynomial analysis, construction, and contextual model selection; parameter interpretation remains limited."),
    "M49-POL-002": ("precalculus-2e", "3.4", "partial", False, "Zeros, multiplicities, end behavior, and turning-point bounds are explicit; inflection-point evidence is not developed, and this coverage is accepted."),
    "M49-LIM-006": ("precalculus-2e", "3.7", "partial", False, "Precalculus 3.7 covers behavior at infinity; Calculus Volume 1 section 2.2 supplements it with formal limit-at-infinity notation."),
    "M49-LIM-007": ("precalculus-2e", "3.3", "partial", False, "Sections 3.3, 3.4, 3.7, and 4.4 collectively support growth comparisons and long-run behavior of combinations; the synthesis remains instructor-led."),
    "M49-ALG-008": ("precalculus-2e", "3.7", "partial", False, "The sections support rational modeling and variation, while rational-adjacent model selection remains incomplete; this coverage is accepted."),
    "M49-SEQ-001": ("precalculus-2e", "11.1", "partial", False, "Explicit and recursive evaluation is direct; sequence graphing is not a main section outcome, and this coverage is accepted."),
    "M49-SEQ-002": ("precalculus-2e", "11.2", "direct", False, "Explicit and recursive arithmetic formulas are explicit."),
    "M49-SEQ-003": ("precalculus-2e", "11.3", "direct", False, "Explicit and recursive geometric formulas are explicit."),
    "M49-SEQ-004": ("precalculus-2e", "11.2", "partial", True, "Arithmetic classification is direct, while distinguishing geometric and other sequences draws on sections 11.1 and 11.3."),
    "M49-SEQ-005": ("precalculus-2e", "11.3", "partial", True, "Discrete-change applications are present, but the objective spans arithmetic, geometric, and other models."),
    "M49-SER-001": ("precalculus-2e", "11.4", "direct", False, "Summation notation is explicit."),
    "M49-SER-002": ("precalculus-2e", "11.4", "direct", False, "Finite arithmetic series are explicit."),
    "M49-SER-003": ("precalculus-2e", "11.4", "direct", False, "Finite geometric series are explicit."),
    "M49-SER-004": ("precalculus-2e", "11.4", "direct", False, "Convergence and sums of infinite geometric series are explicit."),
    "M49-SER-005": ("precalculus-2e", "11.4", "direct", False, "Annuity and accumulated-sum models are explicit."),
    "M49-PAR-002": ("precalculus-2e", "8.6", "direct", False, "Eliminating a parameter to obtain a rectangular equation is explicit."),
    "M49-CON-001": ("precalculus-2e", "10.1", "partial", True, "Ellipse classification is direct, but the objective combines three conic families taught in separate sections."),
    "M49-CON-002": ("precalculus-2e", "10.1", "partial", True, "Completing the square for circle and ellipse equations is direct, but the objective applies across multiple conic families."),
    "M49-CON-004": ("precalculus-2e", "10.1", "partial", True, "Implicit ellipse equations and graphs are direct; parametric ellipse equations require section 8.6."),
    "M49-CON-005": ("precalculus-2e", "10.2", "partial", True, "Implicit hyperbola equations and graphs are direct; parametric hyperbola equations require section 8.6."),
    "M49-CON-006": ("precalculus-2e", "10.2", "partial", True, "Hyperbola features are direct, but the objective spans circles, ellipses, and hyperbolas."),
    "M49-CON-007": ("precalculus-2e", "10.1", "partial", True, "The focal definition of an ellipse is direct, but the objective spans three conic families."),

    "M39-LIN-001": ("college-algebra-2e", "3.3", "direct", False, "Average rate of change is explicit."),
    "M39-LIN-002": ("college-algebra-2e", "4.1", "direct", False, "The section writes and models linear functions from multiple forms of information."),
    "M39-LIN-003": ("college-algebra-2e", "4.3", "direct", False, "Least-squares linear regression with technology is explicit."),
    "M39-LIN-004": ("college-algebra-2e", "4.3", "direct", False, "The section defines and interprets the correlation coefficient."),
    "M39-LIN-005": ("college-algebra-2e", "4.3", "partial", True, "Regression fit is addressed, but residual calculation and residual plots are not taught."),
    "M39-LIN-006": ("college-algebra-2e", "4.3", "direct", False, "The section uses regression for interpolation, extrapolation, and prediction."),
    "M39-EXP-001": ("college-algebra-2e", "6.1", "direct", False, "The section explicitly contrasts constant additive linear change with constant multiplicative exponential change across formulas, tables, graphs, and contexts."),
    "M39-EXP-002": ("precalculus-2e", "4.1", "direct", False, "Constructing exponential functions from data is explicit."),
    "M39-EXP-003": ("precalculus-2e", "4.1", "direct", False, "Initial value, factor, and continuous growth are developed."),
    "M39-EXP-004": ("precalculus-2e", "4.7", "direct", False, "Growth, decay, doubling time, and half-life models are developed."),
    "M39-EXP-005": ("precalculus-2e", "4.6", "direct", False, "Applied exponential and logarithmic equations are explicit."),
    "M39-EXP-006": ("precalculus-2e", "4.8", "direct", False, "Fitting exponential models to data is the section focus."),
    "M39-EXP-007": ("precalculus-2e", "4.7", "partial", True, "Model selection is addressed, but explicit linear-versus-exponential comparison spans earlier sections."),
    "M39-POW-001": ("precalculus-2e", "3.3", "direct", False, "Identifying and interpreting power functions is explicit."),
    "M39-POW-002": ("precalculus-2e", "3.9", "direct", False, "Direct, inverse, and joint variation models are explicit."),
    "M39-POW-003": ("precalculus-2e", "3.3", "direct", False, "Power-function shape and end behavior are explicit."),
    "M39-POW-004": ("precalculus-2e", "3.9", "direct", False, "Variation relationships are the section focus."),
    "M39-POW-005": ("college-algebra-2e", "2.6", "direct", False, "Equations involving rational exponents are explicit."),
    "M39-POW-006": ("precalculus-2e", "3.3", "partial", False, "Power and polynomial end behavior are taught, but the four-family dominance comparison remains a synthesis task; this coverage is accepted."),
    "M39-POW-007": (None, None, "unmatched", False, "No current Viewer section teaches power regression with parameter and correlation interpretation; leaving this supplemental objective unlinked is accepted."),
    "M39-POL-001": ("precalculus-2e", "1.4", "direct", False, "Algebraic operations on functions are explicit."),
    "M39-POL-002": ("precalculus-2e", "1.4", "partial", False, "Function combinations and domains are taught, but sign analysis across representations is not; this coverage is accepted."),
    "M39-POL-003": ("precalculus-2e", "3.4", "direct", False, "Polynomial end behavior is explicit."),
    "M39-POL-004": ("precalculus-2e", "3.4", "direct", False, "Zeros, multiplicities, and graph behavior are explicit."),
    "M39-POL-005": ("precalculus-2e", "3.4", "partial", False, "Degree and turning points are taught; inflection-point evidence is not, and this coverage is accepted."),
    "M39-POL-006": ("precalculus-2e", "3.6", "direct", False, "Constructing polynomials from specified zeros is explicit."),
    "M39-POL-007": ("precalculus-2e", "3.4", "direct", False, "The section connects formulas and graphs through zeros, multiplicity, degree, and end behavior."),
    "M39-POL-008": (None, None, "unmatched", False, "No current Viewer section combines polynomial model construction with optimization in geometric or economic contexts; leaving this supplemental objective unlinked is accepted."),
    "M39-STA-001": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-002": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-003": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-004": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-005": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-006": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-007": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-008": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-009": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-STA-010": (None, None, "unmatched", False, "The current Viewer library has no descriptive-statistics textbook."),
    "M39-PRO-009": ("precalculus-2e", "11.7", "partial", False, "Compound-event notation is supported; a supplement is necessary for conditional probability."),
    "M39-PRO-001": (None, None, "unmatched", False, "Section 11.7 does not teach contingency tables or Venn diagrams as data organizers."),
    "M39-PRO-002": (None, None, "unmatched", False, "Section 11.7 does not teach marginal, joint, and conditional probabilities from contingency tables."),
    "M39-PRO-003": ("precalculus-2e", "11.7", "direct", False, "Probability models, outcomes, and sample spaces are explicit."),
    "M39-PRO-004": ("precalculus-2e", "11.7", "direct", False, "Equally likely outcomes are explicit."),
    "M39-PRO-005": ("precalculus-2e", "11.7", "direct", False, "The complement rule is explicit."),
    "M39-PRO-006": (None, None, "unmatched", False, "Section 11.7 does not teach and-events with independent and dependent events."),
    "M39-PRO-007": ("precalculus-2e", "11.7", "direct", False, "Unions and mutually exclusive events are explicit."),
    "M39-PRO-008": (None, None, "unmatched", False, "The current Viewer library does not teach experimental probability and the law of large numbers."),
    "M39-EV-001": (None, None, "unmatched", False, "The current Viewer library does not teach expected value."),
    "M39-EV-002": (None, None, "unmatched", False, "The current Viewer library does not teach expected-value decision analysis."),
    "M39-POW-008": (None, None, "unmatched", False, "The current Viewer library does not teach linearization and back-transformation of power or exponential data; leaving this supplemental objective unlinked is accepted."),
}


# Complementary sections are added only when inspection of the local HTML shows
# that they teach a distinct part of the canonical objective.
ADDITIONAL_RESOURCES: dict[str, list[tuple[str, str, str, list[str]]]] = {
    "M12-REV-002": [("intermediate-algebra-2e", "1.2", "direct", ["signed-integer operations"])],
    "M12-EQN-005": [("intermediate-algebra-2e", "2.2", "direct", ["number problems"])],
    "M21-FUN-001": [("intermediate-algebra-2e", "3.6", "direct", ["evaluation from graphs"])],
    "M21-FUN-007": [
        ("college-algebra-2e", "3.1", "supporting", ["functions in formulas, graphs, and tables"]),
        ("college-algebra-2e", "4.1", "supporting", ["linear-function comparison contexts"]),
    ],
    "M21-EXP-005": [("college-algebra-2e", "2.6", "direct", ["equations involving rational exponents"])],
    "M21-QUAD-002": [
        ("intermediate-algebra-2e", "9.6", "direct", ["standard-form graph features"]),
        ("intermediate-algebra-2e", "6.5", "direct", ["factored form and zeros"]),
    ],
    "M31-QUAD-002": [("college-algebra-2e", "5.3", "direct", ["factored form, zeros, and multiplicity"])],
    "M31-QUAD-006": [("college-algebra-2e", "5.5", "direct", ["constructing a polynomial from specified zeros"])],
    "M31-LOG-010": [("college-algebra-2e", "6.2", "direct", ["graphical exponential intersections"])],
    "M39-EXP-007": [
        ("college-algebra-2e", "4.3", "direct", ["linear regression and model fit"]),
        ("precalculus-2e", "4.8", "direct", ["exponential regression and model fit"]),
    ],
    "M39-POW-006": [
        ("precalculus-2e", "4.2", "supporting", ["exponential long-run behavior"]),
        ("precalculus-2e", "4.4", "supporting", ["logarithmic long-run behavior"]),
    ],
    "M39-POL-002": [("precalculus-2e", "3.4", "supporting", ["sign and zero behavior of polynomial components"])],
    "M49-FND-004": [
        ("precalculus-2e", "4.2", "direct", ["graphs of exponential functions"]),
        ("precalculus-2e", "4.7", "direct", ["exponential contexts and models"]),
    ],
    "M49-FND-005": [
        ("precalculus-2e", "4.4", "direct", ["graphs of logarithmic functions"]),
        ("precalculus-2e", "4.7", "direct", ["logarithmic contexts and models"]),
    ],
    "M49-PWR-008": [("precalculus-2e", "3.3", "supporting", ["general power-function behavior"])],
    "M49-POL-001": [("precalculus-2e", "3.6", "supporting", ["constructing polynomial functions and models"])],
    "M49-LIM-006": [("calculus-v1", "2.2", "supporting", ["formal limits at infinity"])],
    "M49-LIM-007": [
        ("precalculus-2e", "3.4", "supporting", ["polynomial end behavior"]),
        ("precalculus-2e", "3.7", "supporting", ["rational long-run behavior"]),
        ("precalculus-2e", "4.4", "supporting", ["logarithmic growth"]),
    ],
    "M49-ALG-008": [("precalculus-2e", "3.9", "supporting", ["variation models and contextual parameter interpretation"])],
    "M49-SEQ-004": [
        ("precalculus-2e", "11.1", "direct", ["other explicit and recursive sequences"]),
        ("precalculus-2e", "11.3", "direct", ["geometric-sequence classification"]),
    ],
    "M49-SEQ-005": [("precalculus-2e", "11.2", "direct", ["arithmetic discrete-change models"])],
    "M49-CON-001": [("precalculus-2e", "10.2", "direct", ["hyperbola classification"])],
    "M49-CON-002": [
        ("precalculus-2e", "10.2", "direct", ["hyperbolas in standard form"]),
        ("precalculus-2e", "10.3", "direct", ["parabolas in standard form"]),
    ],
    "M49-CON-003": [("precalculus-2e", "8.6", "direct", ["parametric circle equations"])],
    "M49-CON-004": [("precalculus-2e", "8.6", "direct", ["parametric ellipse equations"])],
    "M49-CON-005": [("precalculus-2e", "8.6", "direct", ["parametric hyperbola equations"])],
    "M49-CON-006": [("precalculus-2e", "10.1", "direct", ["circle and ellipse features"])],
    "M49-CON-007": [("precalculus-2e", "10.2", "direct", ["hyperbola focal definition and distance relationship"])],
}


COMBINED_RESOLUTIONS = {
    "M12-REV-002": "Sections 1.2 and 1.3 together directly cover integer and fraction operations.",
    "M12-EQN-005": "Sections 2.2 and 2.4 together directly cover number, mixture, and motion problems.",
    "M21-FUN-001": "Sections 3.5 and 3.6 together cover evaluation from formulas, tables, and graphs.",
    "M21-EXP-005": "Intermediate Algebra 8.6 and College Algebra 2.6 together cover radical and rational-exponent equations.",
    "M21-QUAD-002": "Sections 9.7, 9.6, and 6.5 together connect vertex, standard, and factored forms to graph features.",
    "M31-QUAD-002": "Sections 5.1 and 5.3 together connect standard, vertex, and factored forms to graph features.",
    "M31-QUAD-006": "Sections 5.1 and 5.5 together support construction from a vertex, graph, or specified zeros.",
    "M31-LOG-010": "Sections 6.6 and 6.2 together support algebraic and graphical intersection methods.",
    "M39-EXP-007": "College Algebra 4.3 and Precalculus 4.7-4.8 together support comparison of fitted linear and exponential models.",
    "M49-FND-004": "Sections 4.1, 4.2, and 4.7 together cover exponential equations, graphs, and contexts.",
    "M49-FND-005": "Sections 4.3, 4.4, and 4.7 together cover logarithmic equations, graphs, and contexts.",
    "M49-SEQ-004": "Sections 11.1-11.3 together support classification of arithmetic, geometric, and other sequences.",
    "M49-SEQ-005": "Sections 11.2 and 11.3 together support arithmetic and geometric discrete-change models.",
    "M49-CON-001": "Sections 10.1 and 10.2 together cover circle, ellipse, and hyperbola classification.",
    "M49-CON-002": "Sections 10.1-10.3 together cover completing the square and standard forms across the conic families.",
    "M49-CON-003": "Sections 10.1 and 8.6 together cover implicit and parametric circle equations.",
    "M49-CON-004": "Sections 10.1 and 8.6 together cover implicit and parametric ellipse equations.",
    "M49-CON-005": "Sections 10.2 and 8.6 together cover implicit and parametric hyperbola equations.",
    "M49-CON-006": "Sections 10.1 and 10.2 together cover the required features of circles, ellipses, and hyperbolas.",
    "M49-CON-007": "Sections 10.1 and 10.2 together cover the focal and distance definitions of the three conic families.",
}


PARTIAL_BUNDLE_NOTES: dict[str, str] = {}


def best_evidence(objective: str, section_data: dict) -> dict[str, str | None]:
    objective_tokens = tokens(objective)
    choices = [{"text": section_data["title"], "anchor": None}] + section_data["headings"]
    best = max(choices, key=lambda item: overlap_score(objective_tokens, tokens(item["text"])))
    return {"heading": best["text"], "anchor": best.get("anchor")}


def select_candidate(objective: dict, candidates: list[Candidate], catalog: dict) -> tuple[Candidate | None, bool, str]:
    objective_id = objective["objective_id"]
    if objective_id in OVERRIDES:
        book, section, alignment, review, note = OVERRIDES[objective_id]
        return (Candidate(book, section, alignment, "content-audit override") if book else None), review, note
    available = [item for item in candidates if (item.book_id, item.section) in catalog]
    if not available:
        return None, False, "No mapped section is available in the current Viewer library."
    alignment_rank = {"direct": 3, "partial": 2, "supporting": 1}
    objective_tokens = tokens(objective["objective"])

    def score(item: Candidate) -> tuple[int, int]:
        data = catalog[(item.book_id, item.section)]
        section_tokens = tokens(data["title"] + " " + " ".join(h["text"] for h in data["headings"]))
        return alignment_rank[item.alignment], overlap_score(objective_tokens, section_tokens)

    chosen = max(available, key=score)
    direct_sections = {(item.book_id, item.section) for item in available if item.alignment == "direct"}
    review = len(direct_sections) > 1
    note = (
        "The legacy crosswalk assigns direct coverage across multiple sections; review whether the objective should be narrowed."
        if review else "The selected section is the strongest single-section match in the existing crosswalk."
    )
    return chosen, review, note


def build_resource(objective: dict, catalog: dict, book_id: str, section: str, role: str, alignment: str, covers: list[str] | None = None) -> dict:
    data = catalog[(book_id, section)]
    evidence = best_evidence(objective["objective"], data)
    anchor = f"#{evidence['anchor']}" if evidence["anchor"] else ""
    return {
        "book_id": book_id,
        "book_title": BOOKS[book_id],
        "section": section,
        "section_title": data["title"],
        "viewer_url": f"{VIEWER_BASE}/sections/{book_id}/{section.replace('.', '-')}.html{anchor}",
        "role": role,
        "alignment": alignment,
        "covers": covers or [evidence["heading"]],
        "content_evidence": evidence,
        "viewer_source_file": f"sections/{book_id}/{section.replace('.', '-')}.html",
    }


def main() -> None:
    catalog = parse_sections()
    objectives, excluded = parse_courses()
    valid_ids = {item["objective_id"] for item in objectives}
    candidates = parse_crosswalk_candidates(valid_ids)
    records = []
    for objective in objectives:
        chosen, specificity_review, note = select_candidate(
            objective, candidates.get(objective["objective_id"], []), catalog
        )
        resources = []
        if chosen:
            resources.append(build_resource(
                objective, catalog, chosen.book_id, chosen.section, "primary", chosen.alignment
            ))
        for book_id, section, alignment, covers in ADDITIONAL_RESOURCES.get(objective["objective_id"], []):
            if (book_id, section) not in catalog:
                raise ValueError(f"Missing Viewer section for {objective['objective_id']}: {book_id} {section}")
            if any(item["book_id"] == book_id and item["section"] == section for item in resources):
                continue
            resources.append(build_resource(
                objective, catalog, book_id, section, "complementary", alignment, covers
            ))

        objective_id = objective["objective_id"]
        if not resources:
            alignment_status = "resource_gap"
        elif objective_id in COMBINED_RESOLUTIONS:
            alignment_status = "direct_combined"
            specificity_review = False
            note = COMBINED_RESOLUTIONS[objective_id]
        elif objective_id in PARTIAL_BUNDLE_NOTES:
            alignment_status = "partial"
            specificity_review = True
            note = PARTIAL_BUNDLE_NOTES[objective_id]
        elif resources[0]["alignment"] == "direct":
            alignment_status = "direct_single"
        else:
            alignment_status = "partial"
        records.append({
            **objective,
            "resources": resources,
            "alignment_status": alignment_status,
            "specificity_review": specificity_review,
            "audit_note": note,
        })

    status_counts = {status: sum(item["alignment_status"] == status for item in records) for status in (
        "direct_single", "direct_combined", "partial", "resource_gap"
    )}
    matched = len(records) - status_counts["resource_gap"]
    review_count = sum(item["specificity_review"] for item in records)
    primary_gaps = sum(item["course_id"] != "M39" and not item["resources"] for item in records)
    math39_gaps = sum(item["course_id"] == "M39" and not item["resources"] for item in records)
    payload = {
        "schema_version": 2,
        "generated_on": date.today().isoformat(),
        "viewer_base_url": VIEWER_BASE,
        "scope": {
            "included_courses": list(IN_SCOPE),
            "course_resource_roles": {
                "M12": "primary",
                "M21": "primary",
                "M31": "primary",
                "M39": "supplemental",
                "M49": "primary",
            },
            "excluded_courses": [
                {"course_id": "M22", "reason": "Uses an internal Geometry workbook."},
                {"course_id": "M32", "reason": "Uses an internal Trigonometry workbook."},
            ],
            "in_scope_objective_count": len(records),
        },
        "validation_rules": {
            "exactly_one_primary_section_when_matched": True,
            "complementary_sections_allowed": True,
            "section_must_exist_in_local_viewer": True,
            "section_content_checked_not_title_only": True,
            "unmatched_objectives_are_not_given_placeholder_links": True,
        },
        "summary": {
            "matched": matched,
            **status_counts,
            "primary_course_resource_gaps": primary_gaps,
            "math39_supplemental_gaps": math39_gaps,
            "specificity_review": review_count,
        },
        "objectives": records,
        "excluded_objective_count": len(excluded),
    }
    rendered_payload = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUTPUT.write_text(rendered_payload, encoding="utf-8")
    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUTPUT.write_text(rendered_payload, encoding="utf-8")

    gap_records = [item for item in records if not item["resources"]]
    primary_gap_records = [item for item in gap_records if item["course_id"] != "M39"]
    supplemental_gap_records = [item for item in gap_records if item["course_id"] == "M39"]
    review_records = [item for item in records if item["specificity_review"]]
    lines = [
        "# OpenStax Objective Link Audit",
        "",
        "The audit checks one primary Viewer section and any complementary sections per in-scope learning objective against the actual local HTML content.",
        "Math 22 and Math 32 are excluded because they use internal workbooks.",
        "",
        "## Summary",
        "",
        f"- In-scope objectives: {len(records)}",
        f"- Matched to a Viewer section: {matched}",
        f"- Direct through one section: {status_counts['direct_single']}",
        f"- Direct through combined sections: {status_counts['direct_combined']}",
        f"- Partial: {status_counts['partial']}",
        f"- Primary-course resource gaps: {primary_gaps}",
        f"- Math 39 supplemental gaps: {math39_gaps}",
        f"- Objectives needing specificity review: {review_count}",
        "",
        "## Primary-Course Resource Gaps",
        "",
        "| Objective | Statement | Finding |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {item['objective_id']} | {item['objective']} | {item['audit_note']} |"
        for item in primary_gap_records
    )
    if not primary_gap_records:
        lines.append("| — | — | None. Every Math 12, 21, 31, and 49 objective has a valid Viewer section. |")
    lines.extend([
        "",
        "## Math 39 Supplemental Gaps",
        "",
        "Math 39 does not primarily use OpenStax, so these findings are informational and do not indicate curriculum defects.",
        "",
        "| Objective | Statement | Finding |",
        "|---|---|---|",
    ])
    lines.extend(
        f"| {item['objective_id']} | {item['objective']} | {item['audit_note']} |"
        for item in supplemental_gap_records
    )
    lines.extend([
        "",
        "## Unresolved Section Mappings",
        "",
        "These objectives remain incomplete even after complementary Viewer sections are allowed.",
        "",
        "| Objective | Linked sections | Alignment | Finding |",
        "|---|---|---|---|",
    ])
    for item in review_records:
        linked = "; ".join(f"{resource['book_title']} {resource['section']}" for resource in item["resources"]) or "—"
        lines.append(f"| {item['objective_id']} | {linked} | {item['alignment_status']} | {item['audit_note']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(OUTPUT)
    print(PUBLIC_OUTPUT)
    print(REPORT)


if __name__ == "__main__":
    main()
