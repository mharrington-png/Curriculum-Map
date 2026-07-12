"""Generate branded course-at-a-glance PDFs from the canonical course YAML files."""

from pathlib import Path
from html import escape
import json
import re
import shutil

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, FrameBreak, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "data" / "courses"
OUTPUT_DIR = ROOT / "output" / "pdf" / "reports"
PUBLIC_DIR = ROOT / "ui" / "public" / "downloads"
SKILL_DATA = ROOT / "generated" / "skill_progressions.json"

MX_RED = colors.HexColor("#CF003D")
MX_PINK = colors.HexColor("#F8DBE3")
MX_PALE = colors.HexColor("#FFF7F9")
MX_BLACK = colors.HexColor("#111111")
MX_GRAY = colors.HexColor("#666666")
MX_LIGHT = colors.HexColor("#EFEFEF")
MX_LINE = colors.HexColor("#D1D1D1")


def parse_course(path: Path):
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
                course[match.group(1)] = match.group(2).strip()
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
unit_title = ParagraphStyle(
    "UnitTitle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.6,
    leading=11.6, textColor=colors.white, spaceAfter=0,
)
objective_id = ParagraphStyle(
    "ObjectiveId", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=5.7,
    leading=6.4, textColor=MX_RED,
)
objective_text = ParagraphStyle(
    "ObjectiveText", parent=styles["Normal"], fontName="Helvetica", fontSize=6.55,
    leading=7.45, textColor=MX_BLACK,
)
priority_style = ParagraphStyle(
    "Priority", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.5,
    leading=8, textColor=MX_GRAY, uppercase=True,
)
intro_style = ParagraphStyle(
    "Intro", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5,
    leading=11, textColor=MX_GRAY,
)
detail_unit_style = ParagraphStyle(
    "DetailUnit", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=19,
    leading=22, textColor=MX_BLACK, spaceAfter=5,
)
detail_priority_style = ParagraphStyle(
    "DetailPriority", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
    leading=10, textColor=MX_RED, spaceAfter=12,
)
detail_objective_id = ParagraphStyle(
    "DetailObjectiveId", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
    leading=10, textColor=MX_RED,
)
detail_objective_text = ParagraphStyle(
    "DetailObjectiveText", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.2,
    leading=11.2, textColor=MX_BLACK,
)
detail_skill_text = ParagraphStyle(
    "DetailSkillText", parent=styles["Normal"], fontName="Helvetica", fontSize=7.25,
    leading=8.7, textColor=MX_BLACK,
)
detail_skill_id = ParagraphStyle(
    "DetailSkillId", parent=styles["Normal"], fontName="Helvetica", fontSize=6.5,
    leading=8, textColor=MX_GRAY,
)
detail_role = ParagraphStyle(
    "DetailRole", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
    leading=10, textColor=colors.white, alignment=1,
)


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
ROLE_COLOR = {"introduce": MX_RED, "reinforce": colors.HexColor("#666666"), "deepen": MX_BLACK, "apply": colors.HexColor("#A83A5A")}


def unit_card(unit, width):
    priority = unit["priority"].upper()
    header_color = MX_RED if unit["priority"] == "required" else (MX_BLACK if unit["priority"] == "review" else MX_GRAY)
    body = [[Paragraph(priority, priority_style), ""]]
    for oid, statement in unit["objectives"]:
        body.append([Paragraph(oid, objective_id), Paragraph(statement, objective_text)])
    table = Table(
        [[Paragraph(unit["title"], unit_title), ""]] + body,
        colWidths=[0.70 * inch, width - 0.70 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    commands = [
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), header_color),
        ("BACKGROUND", (0, 1), (1, 1), MX_PINK if unit["priority"] == "required" else MX_LIGHT),
        ("SPAN", (0, 1), (1, 1)),
        ("BOX", (0, 0), (-1, -1), 0.7, header_color),
        ("LINEBELOW", (0, 2), (-1, -2), 0.35, MX_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
        ("TOPPADDING", (0, 2), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 2.5),
        ("BACKGROUND", (0, 2), (-1, -1), MX_PALE if unit["priority"] == "extension" else colors.white),
    ]
    table.setStyle(TableStyle(commands))
    return table


def objective_detail_card(course_id, objective, width):
    oid, statement = objective
    rows = [[Paragraph(escape(oid), detail_objective_id), Paragraph(escape(statement), detail_objective_text)]]
    skill_rows = []
    for skill in OBJECTIVE_SKILLS.get((course_id, oid), []):
        role = skill["progression"]
        description = escape(skill["description"] or skill["skill_id"])
        note = escape(skill["note"])
        skill_text = Paragraph(
            f"{description}<font color='#666666'>{note}</font><br/><font size='6.5' color='#777777'>{escape(skill['skill_id'])} · {ROLE_NAME[role]}</font>",
            detail_skill_text,
        )
        skill_rows.append([Paragraph(ROLE_LABEL[role], detail_role), skill_text])
    if skill_rows:
        rows.append([Paragraph("SUPPORTING SKILLS", priority_style), ""])
        rows.extend(skill_rows)
    table = Table(rows, colWidths=[0.74*inch, width - 0.74*inch], hAlign="LEFT")
    commands = [
        ("BOX", (0, 0), (-1, -1), 0.7, MX_LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]
    if skill_rows:
        commands.extend([
            ("SPAN", (0, 1), (1, 1)),
            ("BACKGROUND", (0, 1), (1, 1), MX_LIGHT),
            ("TOPPADDING", (0, 1), (1, 1), 4),
            ("BOTTOMPADDING", (0, 1), (1, 1), 4),
            ("BACKGROUND", (0, 2), (-1, -1), colors.HexColor("#FAFAFA")),
            ("LINEBELOW", (0, 2), (-1, -2), 0.3, MX_LINE),
            ("TOPPADDING", (0, 2), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 2), (-1, -1), 3.5),
        ])
        for row_index, skill in enumerate(OBJECTIVE_SKILLS.get((course_id, oid), []), start=2):
            commands.append(("BACKGROUND", (0, row_index), (0, row_index), ROLE_COLOR[skill["progression"]]))
            commands.append(("VALIGN", (0, row_index), (0, row_index), "MIDDLE"))
    table.setStyle(TableStyle(commands))
    return table


class GlanceDocument(BaseDocTemplate):
    def __init__(self, filename, course):
        page_width, page_height = landscape(letter)
        super().__init__(filename, pagesize=(page_width, page_height), leftMargin=0.42*inch, rightMargin=0.42*inch,
                         topMargin=1.18*inch, bottomMargin=0.42*inch,
                         title=f"{course['number']} Course at a Glance",
                         author="Middlesex School Mathematics Department")
        self.course = course
        self.page_width = page_width
        self.page_height = page_height
        gap = 0.11 * inch
        column_width = (self.width - 3 * gap) / 4
        frames = []
        for index in range(4):
            x = self.leftMargin + index * (column_width + gap)
            frames.append(Frame(x, self.bottomMargin, column_width, self.height, id=f"unit-{index + 1}", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0))
        detail_gap = 0.22 * inch
        self.detail_column_width = (self.width - detail_gap) / 2
        detail_frames = [
            Frame(self.leftMargin, self.bottomMargin, self.detail_column_width, self.height, id="detail-left", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Frame(self.leftMargin + self.detail_column_width + detail_gap, self.bottomMargin, self.detail_column_width, self.height, id="detail-right", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        ]
        cover_frame = Frame(0, 0, self.page_width, self.page_height, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=self.draw_cover),
            PageTemplate(id="glance", frames=frames, onPage=self.draw_header),
            PageTemplate(id="detail", frames=detail_frames, onPage=self.draw_detail_header),
        ])
        self.column_width = column_width

    def draw_cover(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(MX_RED)
        canvas.rect(0, self.page_height - 0.18*inch, self.page_width, 0.18*inch, stroke=0, fill=1)
        canvas.rect(0, 0, self.page_width, 0.18*inch, stroke=0, fill=1)
        canvas.setFillColor(MX_BLACK)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawCentredString(self.page_width / 2, self.page_height - 0.78*inch, "MIDDLESEX SCHOOL")
        canvas.setFillColor(MX_GRAY)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawCentredString(self.page_width / 2, self.page_height - 1.05*inch, "MATHEMATICS CURRICULUM REPORT")
        canvas.setStrokeColor(MX_RED)
        canvas.setLineWidth(2)
        canvas.line(self.page_width/2 - 0.65*inch, self.page_height/2 + 0.83*inch, self.page_width/2 + 0.65*inch, self.page_height/2 + 0.83*inch)
        number_style = ParagraphStyle("CoverNumber", fontName="Helvetica-Bold", fontSize=48, leading=54, alignment=TA_CENTER, textColor=MX_BLACK)
        title_style = ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=25, leading=30, alignment=TA_CENTER, textColor=MX_RED)
        number = Paragraph(escape(self.course["number"]), number_style)
        number.wrapOn(canvas, 7.5*inch, 1.0*inch)
        number.drawOn(canvas, (self.page_width - 7.5*inch)/2, self.page_height/2 + 0.05*inch)
        title = Paragraph(escape(self.course["title"]), title_style)
        _, title_height = title.wrapOn(canvas, 7.2*inch, 1.4*inch)
        title.drawOn(canvas, (self.page_width - 7.2*inch)/2, self.page_height/2 - 0.62*inch - title_height/2)
        canvas.restoreState()

    def draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(MX_RED)
        canvas.rect(0, self.page_height - 0.14*inch, self.page_width, 0.14*inch, stroke=0, fill=1)
        canvas.setFillColor(MX_BLACK)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(self.leftMargin, self.page_height - 0.34*inch, "MIDDLESEX SCHOOL  |  MATHEMATICS")
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(self.leftMargin, self.page_height - 0.66*inch, f"{self.course['number']}  Course at a Glance")
        canvas.setFillColor(MX_RED)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(self.leftMargin, self.page_height - 0.88*inch, self.course["title"])
        canvas.setFillColor(MX_GRAY)
        canvas.setFont("Helvetica", 6.8)
        canvas.drawRightString(self.page_width - self.rightMargin, 0.24*inch, f"Page {doc.page}")
        canvas.restoreState()

    def draw_detail_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(MX_RED)
        canvas.rect(0, self.page_height - 0.14*inch, self.page_width, 0.14*inch, stroke=0, fill=1)
        canvas.setFillColor(MX_BLACK)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(self.leftMargin, self.page_height - 0.34*inch, "MIDDLESEX SCHOOL  |  MATHEMATICS")
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(self.leftMargin, self.page_height - 0.63*inch, f"{self.course['number']}  In-Depth Curriculum")
        canvas.setFillColor(MX_RED)
        canvas.setFont("Helvetica-Bold", 9.5)
        canvas.drawString(self.leftMargin, self.page_height - 0.84*inch, self.course["title"])
        legend = [
            ("I", "Introduce", ROLE_COLOR["introduce"]),
            ("R", "Reinforce", ROLE_COLOR["reinforce"]),
            ("D", "Deepen", ROLE_COLOR["deepen"]),
            ("A", "Apply", ROLE_COLOR["apply"]),
        ]
        item_width = 0.88 * inch
        start_x = self.page_width - self.rightMargin - item_width * len(legend)
        legend_y = self.page_height - 0.68*inch
        canvas.setFillColor(MX_GRAY)
        canvas.setFont("Helvetica-Bold", 6.3)
        canvas.drawString(start_x, legend_y + 0.23*inch, "SKILL PROGRESSION")
        for index, (letter, label, color) in enumerate(legend):
            x = start_x + index * item_width
            canvas.setFillColor(color)
            canvas.roundRect(x, legend_y - 0.08*inch, 0.24*inch, 0.24*inch, 3, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 7)
            canvas.drawCentredString(x + 0.12*inch, legend_y, letter)
            canvas.setFillColor(MX_BLACK)
            canvas.setFont("Helvetica-Bold", 6.2)
            canvas.drawString(x + 0.30*inch, legend_y, label)
        canvas.setFillColor(MX_GRAY)
        canvas.setFont("Helvetica", 6.8)
        canvas.drawRightString(self.page_width - self.rightMargin, 0.24*inch, f"Page {doc.page}")
        canvas.restoreState()


def generate(course):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{course['id'].lower()}-course-report.pdf"
    output = OUTPUT_DIR / filename
    doc = GlanceDocument(str(output), course)
    story = [NextPageTemplate("glance"), PageBreak()]
    for index, unit in enumerate(course["units"]):
        story.append(KeepTogether([unit_card(unit, doc.column_width)]))
        if index < len(course["units"]) - 1:
            story.append(FrameBreak())
    story.extend([NextPageTemplate("detail"), PageBreak()])
    for unit_index, unit in enumerate(course["units"]):
        if unit_index:
            story.append(PageBreak())
        story.append(Paragraph(escape(unit["title"]), detail_unit_style))
        story.append(Paragraph(unit["priority"].upper(), detail_priority_style))
        for objective in unit["objectives"]:
            story.append(KeepTogether([objective_detail_card(course["id"], objective, doc.detail_column_width), Spacer(1, 0.10*inch)]))
    doc.build(story)
    shutil.copy2(output, PUBLIC_DIR / filename)
    return output


if __name__ == "__main__":
    for course_file in sorted(COURSE_DIR.glob("math*.yaml")):
        result = generate(parse_course(course_file))
        print(result)
