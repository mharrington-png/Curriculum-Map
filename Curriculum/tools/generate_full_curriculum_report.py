"""Combine all course curricula into one linked, bookmarked curriculum PDF."""

from datetime import date
from pathlib import Path
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "output" / "pdf" / "courses"
OUTPUT = ROOT / "output" / "pdf" / "mathematics-curriculum.pdf"
FRONT_MATTER = ROOT / "tmp" / "pdfs" / "mathematics-curriculum-front-matter.pdf"

MX_RED = colors.HexColor("#CF003D")
MX_BLACK = colors.HexColor("#111111")
MX_GRAY = colors.HexColor("#666666")
PAGE_WIDTH, PAGE_HEIGHT = letter

COURSES = [
    ("m12", "Math 12", "Intermediate Algebra"),
    ("m21", "Math 21", "Algebra and its Functions"),
    ("m22", "Math 22", "Geometry"),
    ("m31", "Math 31", "Advanced Algebra"),
    ("m32", "Math 32", "Precalculus: Trigonometry"),
    ("m39", "Math 39", "Precalculus with Data Analysis"),
    ("m49", "Math 49", "Precalculus with Limits"),
]


def section_page(reader, marker):
    for index, page in enumerate(reader.pages):
        if marker.casefold() in (page.extract_text() or "").casefold():
            return index
    raise ValueError(f"Could not find {marker!r} in report")


def draw_front_matter(destinations):
    FRONT_MATTER.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(FRONT_MATTER), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle("Middlesex School Mathematics Curriculum")
    c.setAuthor("Middlesex School Mathematics Department")

    # Main title page
    c.setFillColor(MX_RED)
    c.rect(0, PAGE_HEIGHT - 14, PAGE_WIDTH, 14, stroke=0, fill=1)
    c.rect(0, 0, PAGE_WIDTH, 14, stroke=0, fill=1)
    c.setFillColor(MX_BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 72, "MIDDLESEX SCHOOL")
    c.setFillColor(MX_GRAY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 92, "MATHEMATICS DEPARTMENT")
    c.setStrokeColor(MX_RED)
    c.setLineWidth(2)
    c.line(PAGE_WIDTH / 2 - 58, PAGE_HEIGHT / 2 + 78, PAGE_WIDTH / 2 + 58, PAGE_HEIGHT / 2 + 78)
    c.setFillColor(MX_BLACK)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 + 23, "Mathematics Curriculum")
    c.setFillColor(MX_RED)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 15, "Math 12 through Math 49")
    c.setFillColor(MX_GRAY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_WIDTH / 2, 68, f"Generated {date.today().strftime('%B %d, %Y')}")
    c.showPage()

    # Traditional table of contents. Coordinates are also returned for link annotations.
    c.setFillColor(MX_RED)
    c.rect(0, PAGE_HEIGHT - 10, PAGE_WIDTH, 10, stroke=0, fill=1)
    c.setFillColor(MX_BLACK)
    c.setFont("Times-Roman", 15)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 50, "TABLE OF CONTENTS")
    c.setFillColor(MX_GRAY)
    c.setFont("Times-Italic", 8)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 67, "Select any entry to jump directly to that section")
    link_rects = []
    y = PAGE_HEIGHT - 98
    roman = ("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.")

    def toc_entry(label, page_number, y_position, indent, font_name, font_size, target):
        left = 62 + indent
        right = PAGE_WIDTH - 62
        c.setFillColor(MX_BLACK)
        c.setFont(font_name, font_size)
        c.drawString(left, y_position, label)
        page_text = str(page_number)
        page_width = c.stringWidth(page_text, font_name, font_size)
        label_width = c.stringWidth(label, font_name, font_size)
        dot_start = left + label_width + 7
        dot_end = right - page_width - 7
        if dot_end > dot_start:
            c.saveState()
            c.setStrokeColor(colors.HexColor("#777777"))
            c.setLineWidth(0.45)
            c.setDash(0.7, 2.1)
            c.line(dot_start, y_position + 2, dot_end, y_position + 2)
            c.restoreState()
        c.drawRightString(right, y_position, page_text)
        link_rects.append(((left - 4, y_position - 5, right + 4, y_position + 11), target))

    for index, (key, number, title) in enumerate(COURSES):
        info = destinations[key]
        toc_entry(f"{roman[index]}     {number.upper()} - {title}", info["cover"] + 1, y, 0, "Times-Bold", 10.5, info["cover"])
        y -= 20
        toc_entry("At a Glance", info["glance"] + 1, y, 42, "Times-Roman", 9.5, info["glance"])
        y -= 18
        toc_entry("In-Depth Curriculum", info["detail"] + 1, y, 42, "Times-Roman", 9.5, info["detail"])
        y -= 28
    c.setFillColor(MX_GRAY)
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_WIDTH - 42, 24, "Page 2")
    c.save()
    return link_rects


def generate(output=OUTPUT):
    curricula = []
    destinations = {}
    output_index = 2  # title page and table of contents
    for key, _, _ in COURSES:
        path = COURSE_DIR / f"{key}-curriculum.pdf"
        reader = PdfReader(path)
        glance_local = section_page(reader, "Course at a Glance")
        detail_local = section_page(reader, "In-Depth Curriculum")
        destinations[key] = {
            "cover": output_index,
            "glance": output_index + glance_local,
            "detail": output_index + detail_local,
        }
        curricula.append((key, reader))
        output_index += len(reader.pages)

    link_rects = draw_front_matter(destinations)
    writer = PdfWriter()
    for page in PdfReader(FRONT_MATTER).pages:
        writer.add_page(page)
    for _, reader in curricula:
        for page in reader.pages:
            writer.add_page(page)

    writer.add_outline_item("Title Page", 0)
    writer.add_outline_item("Table of Contents", 1)
    for key, number, _ in COURSES:
        info = destinations[key]
        course_bookmark = writer.add_outline_item(number, info["cover"], bold=True)
        writer.add_outline_item("At a Glance", info["glance"], parent=course_bookmark)
        writer.add_outline_item("In-Depth Curriculum", info["detail"], parent=course_bookmark)
    for rect, target_page in link_rects:
        writer.add_annotation(1, Link(rect=rect, target_page_index=target_page))

    writer.add_metadata({
        "/Title": "Middlesex School Mathematics Curriculum",
        "/Author": "Middlesex School Mathematics Department",
        "/Subject": "Mathematics curriculum for Math 12 through Math 49",
    })
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)
    return output


if __name__ == "__main__":
    print(generate(sys.argv[1] if len(sys.argv) > 1 else OUTPUT))
