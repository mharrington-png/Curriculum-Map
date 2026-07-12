"""Generate branded course-at-a-glance PDFs from the canonical course YAML files."""

from pathlib import Path
import re
import shutil

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, FrameBreak, KeepTogether, PageTemplate, Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "data" / "courses"
OUTPUT_DIR = ROOT / "output" / "pdf" / "landscape"
PUBLIC_DIR = ROOT / "ui" / "public" / "downloads"

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
        self.addPageTemplates(PageTemplate(id="glance", frames=frames, onPage=self.draw_header))
        self.column_width = column_width

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


def generate(course):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{course['id'].lower()}-course-at-a-glance-landscape.pdf"
    output = OUTPUT_DIR / filename
    doc = GlanceDocument(str(output), course)
    story = []
    for index, unit in enumerate(course["units"]):
        story.append(KeepTogether([unit_card(unit, doc.column_width)]))
        if index < len(course["units"]) - 1:
            story.append(FrameBreak())
    doc.build(story)
    shutil.copy2(output, PUBLIC_DIR / filename)
    return output


if __name__ == "__main__":
    for course_file in sorted(COURSE_DIR.glob("math*.yaml")):
        result = generate(parse_course(course_file))
        print(result)
