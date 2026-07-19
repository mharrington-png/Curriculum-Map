"""Generate branded course curriculum PDFs from the canonical course YAML files."""

from pathlib import Path
from html import escape
import json
import re
import shutil

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, HRFlowable, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "data" / "courses"
OUTPUT_DIR = ROOT / "output" / "pdf" / "courses"
AT_A_GLANCE_DIR = ROOT / "output" / "pdf" / "at-a-glance"
PUBLIC_DIR = ROOT / "ui" / "public" / "downloads"
SKILL_DATA = ROOT / "generated" / "skill_progressions.json"
OPENSTAX_MAP_DIR = ROOT / "mappings" / "openstax"
WORKBOOK_MAP_DIR = ROOT / "mappings" / "workbook"

MX_RED = colors.HexColor("#CF003D")
MX_PINK = colors.HexColor("#F8DBE3")
MX_PALE = colors.HexColor("#FFF7F9")
MX_BLACK = colors.HexColor("#111111")
MX_GRAY = colors.HexColor("#666666")
MX_LIGHT = colors.HexColor("#EFEFEF")
MX_LINE = colors.HexColor("#D1D1D1")


def parse_course(path: Path):
    course = {"id": "", "number": "", "title": "", "source": "", "units": []}
    current = None
    in_units = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line == "units:":
            in_units = True
            continue
        if not in_units:
            match = re.match(r"  (id|number|title|source):\s*(.+)", line)
            if match:
                course[match.group(1)] = match.group(2).strip().strip('"').strip("'")
            continue
        match = re.match(r"  - id: (M\d+-[A-Z]+)$", line)
        if match:
            current = {"id": match.group(1), "title": "", "priority": "", "objectives": []}
            course["units"].append(current)
            continue
        if current:
            match = re.match(r"    title: (.+)", line)
            if match:
                current["title"] = match.group(1).strip()
                continue
            match = re.match(r"    priority: (review|required|extension)", line)
            if match:
                current["priority"] = match.group(1)
                continue
            match = re.match(r'      - \{id: ([^,]+), statement: "(.+)"\}', line)
            if match:
                current["objectives"].append((match.group(1), match.group(2)))
    return course


styles = getSampleStyleSheet()
course_title_style = ParagraphStyle(
    "CourseTitle", parent=styles["Title"], fontName="Times-Bold", fontSize=21,
    leading=24, textColor=colors.HexColor("#202020"), alignment=TA_LEFT, spaceAfter=4,
)
course_meta_style = ParagraphStyle(
    "CourseMeta", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5,
    leading=11, textColor=colors.HexColor("#737373"), spaceAfter=17,
)
section_kicker_style = ParagraphStyle(
    "SectionKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
    leading=10, textColor=colors.HexColor("#999999"), alignment=TA_CENTER, spaceAfter=9,
)
glance_unit_title_style = ParagraphStyle(
    "GlanceUnitTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9,
    leading=11, textColor=colors.HexColor("#222222"),
)
glance_sections_style = ParagraphStyle(
    "GlanceSections", parent=styles["Normal"], fontName="Courier", fontSize=6.15,
    leading=8.7, textColor=colors.HexColor("#858585"),
)
glance_heading_style = ParagraphStyle(
    "GlanceHeading", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2,
    leading=9, textColor=colors.HexColor("#272727"),
)
glance_objective_style = ParagraphStyle(
    "GlanceObjective", parent=styles["Normal"], fontName="Helvetica", fontSize=8.25,
    leading=12.4, textColor=colors.HexColor("#292929"), spaceAfter=2.2,
)
detail_unit_style = ParagraphStyle(
    "DetailUnit", parent=styles["Heading1"], fontName="Times-Bold", fontSize=17,
    leading=20, textColor=colors.HexColor("#202020"),
)
detail_resource_style = ParagraphStyle(
    "DetailResource", parent=styles["Normal"], fontName="Helvetica", fontSize=8,
    leading=10.5, textColor=colors.HexColor("#858585"), spaceAfter=9,
)
detail_objective_id = ParagraphStyle(
    "DetailObjectiveId", parent=styles["Normal"], fontName="Courier", fontSize=6.5,
    leading=8, textColor=colors.HexColor("#B0B0B0"),
)
detail_objective_text = ParagraphStyle(
    "DetailObjectiveText", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5,
    leading=12, textColor=colors.HexColor("#222222"), spaceAfter=4,
)
detail_textbook_style = ParagraphStyle(
    "DetailTextbook", parent=styles["Normal"], fontName="Helvetica", fontSize=7.2,
    leading=9.2, textColor=colors.HexColor("#969696"), spaceAfter=8,
)
supporting_heading_style = ParagraphStyle(
    "SupportingHeading", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.6,
    leading=8, textColor=colors.HexColor("#A8A8A8"), spaceAfter=5,
)
detail_skill_text = ParagraphStyle(
    "DetailSkillText", parent=styles["Normal"], fontName="Helvetica", fontSize=8.1,
    leading=10.2, textColor=colors.HexColor("#303030"),
)


def expand_objective_references(text, valid_ids):
    """Expand objective IDs and same-prefix numeric ranges from a mapping table cell."""
    found = []
    range_pattern = re.compile(r"(M\d+-[A-Z]+-)(\d{3})\s+through\s+(?:M\d+-[A-Z]+-)?(\d{3})")
    for match in range_pattern.finditer(text):
        prefix, start, end = match.groups()
        found.extend(f"{prefix}{number:03d}" for number in range(int(start), int(end) + 1))
    without_ranges = range_pattern.sub("", text)
    found.extend(re.findall(r"M\d+-[A-Z]+-\d{3}", without_ranges))
    return [oid for oid in dict.fromkeys(found) if oid in valid_ids]


def load_resource_sections(course):
    """Read the course's canonical resource crosswalk and derive LO and unit coverage."""
    openstax_path = OPENSTAX_MAP_DIR / f"MATH{course['id'][1:]}_OPENSTAX_MAP.md"
    workbook_paths = {
        "M22": WORKBOOK_MAP_DIR / "MATH22_PACKET_MAP.md",
        "M32": WORKBOOK_MAP_DIR / "MATH32_WORKBOOK_MAP.md",
    }
    map_path = openstax_path if openstax_path.exists() else workbook_paths.get(course["id"])
    source_path = Path(course.get("source", ""))
    fallback_resource = source_path.stem if source_path.suffix else source_path.name
    result = {
        "resource": fallback_resource or "Course materials",
        "resource_label": "Resource",
        "objectives": {},
        "units": {},
    }
    if not map_path or not map_path.exists():
        return result
    text = map_path.read_text(encoding="utf-8")
    resource_match = re.search(r"- \*\*Resource:\*\*\s+(.+)", text)
    if resource_match:
        result["resource"] = re.sub(r"[*`]", "", resource_match.group(1)).strip()
        result["resource_label"] = "Textbook"
    else:
        title_match = re.search(r"^#\s+(.+?)(?:\s+Mapping)?\s*$", text, flags=re.MULTILINE)
        if title_match:
            result["resource"] = title_match.group(1).strip()
    valid_ids = {oid for unit in course["units"] for oid, _ in unit["objectives"]}
    in_crosswalk = False
    for line in text.splitlines():
        if (
            line.startswith("## Detailed Section-to-Objective Crosswalk")
            or line.startswith("## Extension Section Crosswalk")
            or line.startswith("## Detailed Section Crosswalk")
            or line.startswith("## Detailed Resource Crosswalk")
        ):
            in_crosswalk = True
            continue
        if in_crosswalk and line.startswith("## "):
            in_crosswalk = False
            continue
        if not in_crosswalk or not line.lstrip().startswith("|") or re.match(r"\|\s*-", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if course["id"] == "M22":
            section_match = re.match(r"(\d+\.\d+)\s+(.+)", cells[0])
            if not section_match:
                continue
            section, title = section_match.groups()
            references = cells[2]
        elif course["id"] == "M32":
            if cells[0] == "Workbook section":
                continue
            section, title, references = f"pp. {cells[1]}", cells[0], cells[2]
        else:
            if not re.match(r"\d+\.\d+$", cells[0]):
                continue
            section, title, references = cells[:3]
        for oid in expand_objective_references(references, valid_ids):
            result["objectives"].setdefault(oid, []).append({"section": section, "title": title})
    for unit in course["units"]:
        seen = set()
        sections = []
        for oid, _ in unit["objectives"]:
            for section in result["objectives"].get(oid, []):
                key = (section["section"], section["title"])
                if key not in seen:
                    seen.add(key)
                    sections.append(section)
        result["units"][unit["id"]] = sections
    return result


def format_sections(sections, include_titles=False):
    if not sections:
        return "No mapped textbook section"
    if include_titles:
        return "; ".join(f"{item['section']} {item['title']}" for item in sections)
    return ", ".join(item["section"] for item in sections)


def load_objective_skills():
    lookup = {}
    skill_records = json.loads(SKILL_DATA.read_text(encoding="utf-8-sig"))
    for skill in skill_records:
        for occurrence in skill["occurrences"]:
            key = (occurrence["course_id"], occurrence["objective_id"])
            note = ""
            if occurrence["progression"] != "introduce":
                if skill.get("first_introduced_course"):
                    note = f" (first introduced in {skill['first_introduced_course']})"
                elif skill.get("introduction_status") == "inherited":
                    inherited = skill.get("inherited_note") or "inherited from earlier mathematics"
                    note = f" ({inherited[0].lower() + inherited[1:]})"
            lookup.setdefault(key, []).append({
                "skill_id": skill["skill_id"],
                "description": skill["description"],
                "progression": occurrence["progression"],
                "note": note,
            })
    return lookup


OBJECTIVE_SKILLS = load_objective_skills()
ROLE_LABEL = {"introduce": "I", "reinforce": "R", "deepen": "D", "apply": "A"}
ROLE_NAME = {"introduce": "Introduce", "reinforce": "Reinforce", "deepen": "Deepen", "apply": "Apply"}
ROLE_COLOR = {
    "introduce": colors.HexColor("#202020"),
    "reinforce": colors.HexColor("#969696"),
    "deepen": colors.HexColor("#B83C62"),
    "apply": MX_RED,
}


class PriorityBadge(Flowable):
    def __init__(self, priority):
        super().__init__()
        self.label = priority.upper()
        self.width = {"REQUIRED": 0.66 * inch, "REVIEW": 0.52 * inch, "EXTENSION": 0.68 * inch}[self.label]
        self.height = 0.15 * inch

    def wrap(self, avail_width, avail_height):
        return self.width, self.height

    def draw(self):
        required = self.label == "REQUIRED"
        self.canv.setFillColor(colors.HexColor("#FBE8EE") if required else colors.HexColor("#EEEEEE"))
        self.canv.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        self.canv.setFillColor(MX_RED if required else colors.HexColor("#858585"))
        self.canv.setFont("Helvetica-Bold", 6.2)
        self.canv.drawCentredString(self.width / 2, 2.4, self.label)


class RoleDot(Flowable):
    def __init__(self, role):
        super().__init__()
        self.role = role
        self.width = self.height = 0.16 * inch

    def wrap(self, avail_width, avail_height):
        return self.width, self.height

    def draw(self):
        radius = self.height / 2
        self.canv.setFillColor(ROLE_COLOR[self.role])
        self.canv.circle(radius, radius, radius, stroke=0, fill=1)
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 5.6)
        self.canv.drawCentredString(radius, radius - 2, ROLE_LABEL[self.role])


class LegendBox(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 0
        self.height = 0.38 * inch

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return self.width, self.height

    def draw(self):
        self.canv.setFillColor(colors.HexColor("#FAF9F8"))
        self.canv.setStrokeColor(colors.HexColor("#E4E1DE"))
        self.canv.roundRect(0, 0, self.width, self.height, 4, stroke=1, fill=1)
        self.canv.setFillColor(colors.HexColor("#999999"))
        self.canv.setFont("Helvetica-Bold", 6.7)
        self.canv.drawString(15, 11, "SKILL PROGRESSION")
        start_x = 1.48 * inch
        item_width = 0.94 * inch
        for index, role in enumerate(("introduce", "reinforce", "deepen", "apply")):
            x = start_x + index * item_width
            self.canv.setFillColor(ROLE_COLOR[role])
            self.canv.circle(x, 13.5, 7, stroke=0, fill=1)
            self.canv.setFillColor(colors.white)
            self.canv.setFont("Helvetica-Bold", 5.8)
            self.canv.drawCentredString(x, 11.4, ROLE_LABEL[role])
            self.canv.setFillColor(colors.HexColor("#333333"))
            self.canv.setFont("Helvetica", 7.6)
            self.canv.drawString(x + 12, 10.8, ROLE_NAME[role])


class GlanceUnitFlowable(Flowable):
    """A unit overview that can split between objectives and label continuations."""

    def __init__(self, unit, resource_data, objectives=None, continued=False):
        super().__init__()
        self.unit = unit
        self.resource_data = resource_data
        self.objectives = list(objectives if objectives is not None else unit["objectives"])
        self.continued = continued
        self._table = None
        self._table_height = 0

    def _build_table(self, width):
        title = self.unit["title"] + (" (Continued)" if self.continued else "")
        left = [
            Paragraph(escape(title), glance_unit_title_style),
            Spacer(1, 5),
            PriorityBadge(self.unit["priority"]),
        ]
        if not self.continued:
            sections = self.resource_data["units"].get(self.unit["id"], [])
            left.extend([
                Spacer(1, 7),
                Paragraph(escape(format_sections(sections, include_titles=True)), glance_sections_style),
            ])
        heading = "UNIT LEARNING OBJECTIVES - CONTINUED" if self.continued else "UNIT LEARNING OBJECTIVES"
        right = [Paragraph(heading, glance_heading_style), Spacer(1, 6)]
        right.extend(Paragraph(escape(statement), glance_objective_style) for _, statement in self.objectives)
        table = Table([[left, right]], colWidths=[1.87 * inch, width - 1.87 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 18),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return table

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        self._table = self._build_table(avail_width)
        _, self._table_height = self._table.wrap(avail_width, avail_height)
        self.height = 0.45 + 11 + self._table_height + 14
        return self.width, self.height

    def split(self, avail_width, avail_height):
        _, full_height = self.wrap(avail_width, avail_height)
        if full_height <= avail_height:
            return [self]
        best_count = 0
        best_part = None
        for count in range(1, len(self.objectives) + 1):
            candidate = GlanceUnitFlowable(
                self.unit,
                self.resource_data,
                objectives=self.objectives[:count],
                continued=self.continued,
            )
            _, candidate_height = candidate.wrap(avail_width, avail_height)
            if candidate_height > avail_height:
                break
            best_count = count
            best_part = candidate
        if best_count == 0:
            return []
        if best_count == len(self.objectives):
            return [best_part]
        continuation = GlanceUnitFlowable(
            self.unit,
            self.resource_data,
            objectives=self.objectives[best_count:],
            continued=True,
        )
        return [best_part, continuation]

    def draw(self):
        if self._table is None:
            self.wrap(self.width, self.height)
        self.canv.setStrokeColor(colors.HexColor("#DDDDDD"))
        self.canv.setLineWidth(0.45)
        self.canv.line(0, self.height - 0.45, self.width, self.height - 0.45)
        self._table.drawOn(self.canv, 0, 14)


def course_header(course, resource_data):
    label = resource_data.get("resource_label", "Resource")
    meta = (
        f"{escape(course['title'])} &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; Middlesex School Mathematics"
        f" &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; {label}: {escape(resource_data['resource'])}"
    )
    return [
        Paragraph(f"{escape(course['number'])} Curriculum", course_title_style),
        Paragraph(meta, course_meta_style),
        Paragraph("COURSE AT A GLANCE", section_kicker_style),
    ]


def detail_intro():
    return [
        Spacer(1, 46),
        HRFlowable(width="100%", thickness=0.45, color=colors.HexColor("#DDDDDD")),
        Spacer(1, 34),
        Paragraph("IN-DEPTH CURRICULUM", section_kicker_style),
        Spacer(1, 2),
        LegendBox(),
        Spacer(1, 22),
    ]


def detail_unit_header(unit, width, resource_data):
    badge_width = 0.85 * inch
    title_width = min(pdfmetrics.stringWidth(unit["title"], "Times-Bold", 17) + 10, width - badge_width)
    title_row = Table(
        [[Paragraph(escape(unit["title"]), detail_unit_style), PriorityBadge(unit["priority"]), ""]],
        colWidths=[title_width, badge_width, width - title_width - badge_width], hAlign="LEFT",
    )
    title_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    sections = resource_data["units"].get(unit["id"], [])
    coverage = f"{resource_data.get('resource_label', 'Resource')} coverage: {escape(format_sections(sections, include_titles=True))}"
    return [title_row, Spacer(1, 4), Paragraph(coverage, detail_resource_style)]


def objective_detail_block(course_id, objective, width, resource_data):
    oid, statement = objective
    sections = resource_data["objectives"].get(oid, [])
    label = resource_data.get("resource_label", "Resource")
    content = [
        Paragraph(escape(statement), detail_objective_text),
        Paragraph(f"{label}: {escape(format_sections(sections, include_titles=True))}", detail_textbook_style),
    ]
    skills = OBJECTIVE_SKILLS.get((course_id, oid), [])
    if skills:
        content.append(Paragraph("SUPPORTING SKILLS", supporting_heading_style))
        skill_rows = []
        for skill in skills:
            note = skill["note"].strip().strip("()")
            metadata = escape(skill["skill_id"])
            if note:
                metadata += f" &nbsp;·&nbsp; {escape(note)}"
            skill_text = Paragraph(
                f"{escape(skill['description'] or skill['skill_id'])}<br/><font name='Courier' size='6.3' color='#B4B4B4'>{metadata}</font>",
                detail_skill_text,
            )
            skill_rows.append([RoleDot(skill["progression"]), skill_text])
        skill_table = Table(skill_rows, colWidths=[0.25 * inch, width - 1.10 * inch - 0.25 * inch], hAlign="LEFT")
        skill_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        content.append(skill_table)
    table = Table(
        [[Paragraph(escape(oid), detail_objective_id), content]],
        colWidths=[1.10 * inch, width - 1.10 * inch], hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        HRFlowable(width="100%", thickness=0.45, color=colors.HexColor("#E1E1E1")),
        Spacer(1, 12),
        table,
        Spacer(1, 11),
    ]


class CourseCurriculumDocument(BaseDocTemplate):
    def __init__(self, filename, course):
        super().__init__(
            filename,
            pagesize=letter,
            leftMargin=0.68 * inch,
            rightMargin=0.68 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.58 * inch,
            title=f"{course['number']} Curriculum",
            author="Middlesex School Mathematics Department",
        )
        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height,
            id="course", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="course", frames=[frame])])


def generate(course):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AT_A_GLANCE_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{course['id'].lower()}-curriculum.pdf"
    glance_filename = f"{course['id'].lower()}-curriculum-at-a-glance.pdf"
    resource_data = load_resource_sections(course)
    output = OUTPUT_DIR / filename
    doc = CourseCurriculumDocument(str(output), course)
    story = []

    story.extend(course_header(course, resource_data))
    for unit in course["units"]:
        story.append(GlanceUnitFlowable(unit, resource_data))

    story.append(PageBreak())
    for unit_index, unit in enumerate(course["units"]):
        if unit_index:
            story.append(PageBreak())
        prefix = detail_intro() if unit_index == 0 else [Spacer(1, 22)]
        objectives = unit["objectives"]
        if objectives:
            first_detail = prefix + detail_unit_header(unit, doc.width, resource_data) + objective_detail_block(
                course["id"], objectives[0], doc.width, resource_data
            )
            story.append(KeepTogether(first_detail))
            for objective_index, objective in enumerate(objectives[1:], start=1):
                if unit_index == 0 and objective_index == 2:
                    story.append(PageBreak())
                story.append(KeepTogether(objective_detail_block(course["id"], objective, doc.width, resource_data)))
        else:
            story.extend(prefix + detail_unit_header(unit, doc.width, resource_data))

    doc.build(story)
    shutil.copy2(output, PUBLIC_DIR / filename)
    reader = PdfReader(output)
    detail_page = next(
        index for index, page in enumerate(reader.pages)
        if "in-depth curriculum" in (page.extract_text() or "").casefold()
    )
    glance_writer = PdfWriter()
    for page in reader.pages[:detail_page]:
        glance_writer.add_page(page)
    glance_writer.add_metadata({
        "/Title": f"{course['number']} Curriculum - Course at a Glance",
        "/Author": "Middlesex School Mathematics Department",
        "/Subject": f"At-a-glance curriculum for {course['number']}",
    })
    glance_output = AT_A_GLANCE_DIR / glance_filename
    with glance_output.open("wb") as handle:
        glance_writer.write(handle)
    shutil.copy2(glance_output, PUBLIC_DIR / glance_filename)
    return output


if __name__ == "__main__":
    for course_file in sorted(COURSE_DIR.glob("math*.yaml")):
        result = generate(parse_course(course_file))
        print(result)
