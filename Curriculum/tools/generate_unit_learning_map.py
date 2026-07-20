"""Generate student-facing unit learning maps from canonical curriculum data."""

from __future__ import annotations

import argparse
import io
import json
import re
from itertools import combinations
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import _listWrapOn
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "data" / "courses"
SKILL_DATA = ROOT / "generated" / "skill_progressions.json"
OUTPUT_DIR = ROOT / "output" / "pdf" / "unit-learning-maps"

MX_RED = colors.HexColor("#CF003D")
INK = colors.HexColor("#171717")
MUTED = colors.HexColor("#666666")
LINE = colors.HexColor("#D8D8D8")
PALE_RED = colors.HexColor("#FCE8EE")
PALE_PINK = colors.HexColor("#FFF0F4")
PALE_GRAY = colors.HexColor("#F4F1F2")

ROLE_LABELS = {
    "introduce": ("I", "Introduce", PALE_RED, colors.HexColor("#9D0030"), None),
    "deepen": ("D", "Deepen", PALE_PINK, colors.HexColor("#9D003D"), None),
    "apply": ("A", "Apply", colors.white, MX_RED, MX_RED),
    "reinforce": ("R", "Reinforce", PALE_GRAY, colors.HexColor("#383838"), None),
}


def student_text(value: str) -> str:
    """Convert light source-document notation into safe printable text."""
    cleaned = value.replace("`", "")
    escaped = escape(cleaned)
    return re.sub(r"\^([A-Za-z0-9]+)", r"<super>\1</super>", escaped)


def parse_course(path: Path) -> dict:
    course = {"id": "", "number": "", "title": "", "units": []}
    current = None
    in_units = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line == "units:":
            in_units = True
            continue
        if not in_units:
            match = re.match(r"  (id|number|title):\s*(.+)", line)
            if match:
                course[match.group(1)] = match.group(2).strip().strip('"').strip("'")
            continue
        match = re.match(r"  - id: (M\d+-[A-Z]+)$", line)
        if match:
            current = {"id": match.group(1), "title": "", "priority": "", "objectives": []}
            course["units"].append(current)
            continue
        if not current:
            continue
        title_match = re.match(r"    title: (.+)", line)
        if title_match:
            current["title"] = title_match.group(1).strip().strip('"').strip("'")
            continue
        priority_match = re.match(r"    priority: (review|required|extension)", line)
        if priority_match:
            current["priority"] = priority_match.group(1)
            continue
        objective_match = re.match(r'      - \{id: ([^,]+), statement: "(.+)"\}', line)
        if objective_match:
            current["objectives"].append(
                {"id": objective_match.group(1), "statement": objective_match.group(2)}
            )
    return course


def load_skills() -> tuple[dict, dict]:
    records = json.loads(SKILL_DATA.read_text(encoding="utf-8"))
    descriptions = {record["skill_id"]: record["description"] for record in records}
    by_objective: dict[str, list[dict]] = {}
    for record in records:
        for occurrence in record["occurrences"]:
            by_objective.setdefault(occurrence["objective_id"], []).append(
                {
                    "skill_id": record["skill_id"],
                    "description": record["description"],
                    "progression": occurrence["progression"],
                }
            )
    return descriptions, by_objective


styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle(
    "UnitMapTitle",
    parent=styles["Title"],
    fontName="Times-Bold",
    fontSize=23,
    leading=25.5,
    textColor=INK,
    alignment=0,
)
SECTION_STYLE = ParagraphStyle(
    "UnitMapSection",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=14.5,
    leading=20,
    textColor=MX_RED,
)


def highlighted_objective(statement: str) -> str:
    """Highlight the leading action phrase without adding presentation fields to the data."""
    cleaned = statement.replace("`", "")
    match = re.match(r"^I can\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if not match:
        return student_text(cleaned)
    remainder = match.group(1)
    action = re.match(
        r"^([A-Za-z]+(?:-[A-Za-z]+)*(?:(?:,\s*|\s+(?:and|or)\s+)[A-Za-z]+(?:-[A-Za-z]+)*)*)\b(.*)$",
        remainder,
        flags=re.IGNORECASE,
    )
    if not action:
        return student_text(cleaned)
    phrase, rest = action.groups()
    return f'I can <font color="#CF003D">{student_text(phrase)}</font>{student_text(rest)}'


def role_badge(progression: str, compact: bool = False) -> Table:
    letter, _label, background, foreground, border = ROLE_LABELS[progression]
    badge_width = (0.22 if compact else 0.27) * inch
    badge_height = (0.18 if compact else 0.21) * inch
    badge = Table([[letter]], colWidths=[badge_width], rowHeights=[badge_height])
    commands = [
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("TEXTCOLOR", (0, 0), (-1, -1), foreground),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.7 if compact else 7.3),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]
    if border:
        commands.append(("BOX", (0, 0), (-1, -1), 0.8, border))
    badge.setStyle(
        TableStyle(commands)
    )
    badge.hAlign = "LEFT"
    return badge


def objective_block(number: int, objective: dict, skills: list[dict], width: float, compact: bool):
    objective_style = ParagraphStyle(
        f"ObjectiveText{'Compact' if compact else 'Standard'}",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.4 if compact else 10.5,
        leading=10.4 if compact else 13.4,
        textColor=INK,
        spaceAfter=4 if compact else 6,
    )
    related_style = ParagraphStyle(
        f"RelatedSkills{'Compact' if compact else 'Standard'}",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.2 if compact else 7.7,
        leading=7 if compact else 9,
        textColor=colors.HexColor("#858585"),
        spaceAfter=2 if compact else 3,
    )
    skill_style = ParagraphStyle(
        f"SkillText{'Compact' if compact else 'Standard'}",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8 if compact else 8.6,
        leading=8.1 if compact else 10.4,
        textColor=INK,
    )
    no_skills_style = ParagraphStyle(
        f"NoSkills{'Compact' if compact else 'Standard'}",
        parent=skill_style,
        textColor=MUTED,
        fontName="Helvetica-Oblique",
    )
    skill_rows = []
    role_order = {"introduce": 0, "deepen": 1, "apply": 2, "reinforce": 3}
    for skill in sorted(skills, key=lambda item: (role_order[item["progression"]], item["description"])):
        skill_rows.append(
            [role_badge(skill["progression"], compact), Paragraph(student_text(skill["description"]), skill_style)]
        )
    if not skill_rows:
        skill_rows.append(["", Paragraph("No supporting skills are currently mapped.", no_skills_style)])

    badge_col = (0.27 if compact else 0.34) * inch
    content_width = width - (0.30 if compact else 0.38) * inch
    skills_table = Table(skill_rows, colWidths=[badge_col, content_width - badge_col], hAlign="LEFT")
    skills_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 5),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.4 if compact else 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4 if compact else 1.8),
            ]
        )
    )
    contents = [
        Paragraph(f"{number}. {highlighted_objective(objective['statement'])}", objective_style),
        Paragraph("RELATED SKILLS", related_style),
        skills_table,
    ]
    checkbox_size = (0.14 if compact else 0.18) * inch
    checkbox = Table([[""]], colWidths=[checkbox_size], rowHeights=[checkbox_size])
    checkbox.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK)]))
    row = Table([[checkbox, contents]], colWidths=[(0.27 if compact else 0.34) * inch, width - (0.27 if compact else 0.34) * inch])
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 7 if compact else 10),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    separator = HRFlowable(
        width="100%",
        thickness=0.65,
        color=LINE,
        spaceBefore=(5 if compact else 9),
        spaceAfter=(5 if compact else 9),
    )
    return KeepTogether([row, separator])


def display_unit_title(title: str) -> str:
    if ", and " in title:
        before, after = title.rsplit(", and ", 1)
        return f"{before} & {after}"
    if " and " in title:
        before, after = title.rsplit(" and ", 1)
        return f"{before} & {after}"
    return title


def header_geometry(unit: dict) -> tuple[Paragraph, float, float, float]:
    width, height = letter
    margin = 0.55 * inch
    title = Paragraph(escape(display_unit_title(unit["title"])), TITLE_STYLE)
    _, title_height = title.wrap(width - 2 * margin, 0.85 * inch)
    title_top = height - 0.72 * inch
    rule_y = title_top - title_height - 0.11 * inch
    section_top = rule_y - 0.17 * inch
    section = Paragraph("Student learning objectives<br/>for this unit", SECTION_STYLE)
    _, section_height = section.wrap(3.15 * inch, 0.65 * inch)
    content_top = section_top - section_height - 0.13 * inch
    return title, title_top, rule_y, content_top


def draw_first_page(canvas, doc, course: dict, unit: dict):
    width, height = letter
    margin = 0.55 * inch
    canvas.saveState()
    canvas.setFillColor(MX_RED)
    text = canvas.beginText(margin, height - 0.45 * inch)
    text.setFont("Helvetica-Bold", 8.2)
    text.setCharSpace(1.1)
    text.textLine(f"MIDDLESEX MATHEMATICS · {course['number'].upper()}")
    canvas.drawText(text)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.3)
    canvas.drawString(width - 1.92 * inch, height - 0.44 * inch, "Name:")
    canvas.drawString(width - 1.92 * inch, height - 0.70 * inch, "Date:")
    canvas.setStrokeColor(LINE)
    canvas.line(width - 1.55 * inch, height - 0.47 * inch, width - margin, height - 0.47 * inch)
    canvas.line(width - 1.55 * inch, height - 0.73 * inch, width - margin, height - 0.73 * inch)

    title, title_top, rule_y, _content_top = header_geometry(unit)
    _, title_height = title.wrap(width - 2 * margin, 0.85 * inch)
    title.drawOn(canvas, margin, title_top - title_height)
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.15)
    canvas.line(margin, rule_y, width - margin, rule_y)

    section_top = rule_y - 0.17 * inch
    section = Paragraph("Student learning objectives<br/>for this unit", SECTION_STYLE)
    _, section_height = section.wrap(3.15 * inch, 0.65 * inch)
    section.drawOn(canvas, margin, section_top - section_height)

    legend_y = section_top - 0.34 * inch
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.setFont("Helvetica", 7.1)
    canvas.drawRightString(width - margin, section_top - 0.03 * inch, "SUPPORTING SKILLS LEGEND")
    legend_widths = {"introduce": 1.00, "deepen": 0.96, "apply": 0.84, "reinforce": 1.08}
    legend_gap = 0.05 * inch
    total_width = sum(legend_widths.values()) * inch + legend_gap * 3
    x = width - margin - total_width
    for key in ("introduce", "deepen", "apply", "reinforce"):
        tag_letter, label, background, foreground, border = ROLE_LABELS[key]
        box_width = legend_widths[key] * inch
        canvas.setFillColor(background)
        canvas.rect(x, legend_y, box_width, 0.22 * inch, stroke=0, fill=1)
        if border:
            canvas.setStrokeColor(border)
            canvas.setLineWidth(0.8)
            canvas.rect(x, legend_y, box_width, 0.22 * inch, stroke=1, fill=0)
        canvas.setFillColor(foreground)
        canvas.setFont("Helvetica", 7.3)
        canvas.drawCentredString(x + box_width / 2, legend_y + 4.4, f"{tag_letter} — {label}")
        x += box_width + legend_gap
    canvas.restoreState()


def make_frames(top_y: float, compact: bool, prefix: str) -> tuple[list[Frame], float]:
    margin = 0.55 * inch
    bottom = 0.45 * inch
    available_width = letter[0] - 2 * margin
    if not compact:
        return [Frame(margin, bottom, available_width, top_y - bottom, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=f"{prefix}-full")], available_width
    gap = 0.20 * inch
    column_width = (available_width - gap) / 2
    return [
        Frame(margin, bottom, column_width, top_y - bottom, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=f"{prefix}-left"),
        Frame(margin + column_width + gap, bottom, column_width, top_y - bottom, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=f"{prefix}-right"),
    ], column_width


def compact_story(blocks: list, width: float, first_height: float, later_height: float) -> list:
    """Balance dense content across the four columns of a two-page handout."""
    measurement_canvas = Canvas(io.BytesIO(), pagesize=letter)
    heights = [
        _listWrapOn(block._content, width, measurement_canvas)[1]
        for block in blocks
    ]
    count = len(blocks)
    if count < 4:
        return blocks

    # Keep a reserve because KeepTogether's measured height does not include every
    # frame-edge spacing adjustment made during the final document build.
    capacities = [first_height - 36, first_height - 36, later_height - 36, later_height - 36]
    target_height = sum(heights) / 4
    target_count = count / 4
    candidates = []
    for cuts in combinations(range(1, count), 3):
        boundaries = (0, *cuts, count)
        loads = [sum(heights[boundaries[index]:boundaries[index + 1]]) for index in range(4)]
        if all(load <= capacity for load, capacity in zip(loads, capacities)):
            counts = [boundaries[index + 1] - boundaries[index] for index in range(4)]
            score = sum((load - target_height) ** 2 for load in loads)
            score += 300 * sum((group_count - target_count) ** 2 for group_count in counts)
            candidates.append((score, cuts))
    if not candidates:
        return blocks
    cuts = min(candidates, key=lambda item: item[0])[1]

    story = []
    boundaries = set(cuts)
    for index, block in enumerate(blocks, start=1):
        story.append(block)
        if index in boundaries:
            story.append(FrameBreak())
    return story


def build_document(course: dict, unit: dict, by_objective: dict, output_path: Path, compact: bool) -> None:
    _title, _title_top, _rule_y, first_top = header_geometry(unit)
    first_frames, content_width = make_frames(first_top, compact, "first")
    later_frames, _ = make_frames(letter[1] - 0.45 * inch, compact, "later")
    doc = BaseDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title=f"Student Learning Objectives - {course['number']} - {unit['title']}",
        author="Middlesex Mathematics",
        subject="Unit learning objectives and supporting skills",
    )
    doc.addPageTemplates([
        PageTemplate(id="first", frames=first_frames, onPage=lambda canvas, document: draw_first_page(canvas, document, course, unit), autoNextPageTemplate="later"),
        PageTemplate(id="later", frames=later_frames),
    ])
    blocks = []
    for number, objective in enumerate(unit["objectives"], start=1):
        blocks.append(objective_block(number, objective, by_objective.get(objective["id"], []), content_width, compact))
    if compact:
        first_height = first_frames[0]._height
        later_height = later_frames[0]._height
        story = compact_story(blocks, content_width, first_height, later_height)
    else:
        story = blocks
    doc.build(story)


def generate(course: dict, unit: dict, by_objective: dict, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_document(course, unit, by_objective, output_path, compact=False)
    if len(PdfReader(output_path).pages) > 2:
        build_document(course, unit, by_objective, output_path, compact=True)
    page_count = len(PdfReader(output_path).pages)
    if page_count > 2:
        raise RuntimeError(f"{unit['id']} produced {page_count} pages; revise the compact layout.")
    return len(unit["objectives"])


def normalized_course_id(value: str) -> str:
    cleaned = value.upper().replace("MATH", "M").replace(" ", "")
    if not re.fullmatch(r"M\d+", cleaned):
        raise argparse.ArgumentTypeError("Course must look like M32 or Math32.")
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", required=True, type=normalized_course_id, help="Course ID, such as M32")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--unit", help="Unit ID, such as M32-GRF")
    group.add_argument("--all", action="store_true", help="Generate every unit in the selected course")
    args = parser.parse_args()

    course_path = COURSE_DIR / f"math{args.course[1:]}.yaml"
    if not course_path.exists():
        parser.error(f"No course data found for {args.course}.")
    course = parse_course(course_path)
    _, by_objective = load_skills()
    units = course["units"] if args.all else [unit for unit in course["units"] if unit["id"] == args.unit.upper()]
    if not units:
        available = ", ".join(unit["id"] for unit in course["units"])
        parser.error(f"Unit not found. Available units: {available}")

    for unit in units:
        filename = f"{unit['id'].lower()}-student-learning-objectives.pdf"
        output_path = OUTPUT_DIR / filename
        count = generate(course, unit, by_objective, output_path)
        print(f"Generated {output_path} ({count} learning objectives)")


if __name__ == "__main__":
    main()
