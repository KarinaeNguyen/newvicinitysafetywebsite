
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import collections
import os

# Paths
output_pdf = "export/executive_summary_2025.pdf"
report_text_path = "export/report_paragraph.txt"
sales_chart = "export/sales_over_time.png"
balance_chart = "export/sales_balance_2025.png"

# Read report paragraph
with open(report_text_path, "r", encoding="utf-8") as f:
    report_text = f.read()

styles = getSampleStyleSheet()
# Register Arial font for Vietnamese text
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    font_name = 'Arial'
except:
    font_name = 'Helvetica'
for style in styles.byName.values():
    style.fontName = font_name
    if hasattr(style, 'fontSize'):
        style.fontSize += 2
    if hasattr(style, 'leading'):
        style.leading += 2

story = []


# Remove logo from story, instead draw it on the first page in the top-right corner
logo_path = "export/vicinity_safety_logo.png"
def add_logo(canvas, doc):
    if os.path.exists(logo_path):
        # Place the logo in the top-right corner, small size
        logo_width = 60
        logo_height = 60
        page_width, page_height = A4
        x = page_width - logo_width - 20  # 20px from right edge
        y = page_height - logo_height - 20  # 20px from top edge
        canvas.drawImage(logo_path, x, y, width=logo_width, height=logo_height, mask='auto')


# Title
story.append(Paragraph("<b>Executive Financial Summary 2025</b>", styles['Title']))

# ...existing code...
# Major section headline for the charts
story.append(Paragraph("<b>Vertical A Home Fire Operation Summary</b>", styles['Heading1']))
story.append(Spacer(1, 12))

# Report paragraph
story.append(Paragraph(report_text, styles['BodyText']))
story.append(Spacer(1, 18))

# Add sales_over_time.png if exists
if os.path.exists(sales_chart):
    story.append(Paragraph("<b>Monthly Sales Trends</b>", styles['Heading2']))
    story.append(Image(sales_chart, width=400, height=220))
    story.append(Spacer(1, 12))
else:
    story.append(Paragraph("[sales_over_time.png not found]", styles['BodyText']))

# Add sales_balance_2025.png if exists
if os.path.exists(balance_chart):
    story.append(Paragraph("<b>Sales and Balance Chart</b>", styles['Heading2']))
    story.append(Paragraph(
        "This chart visualizes the relationship between total sales, total cost, and net balance for each month in 2025. "
        "It provides a clear overview of the company's revenue, expenditure, and financial position throughout the year.",
        styles['BodyText'])
    )
    story.append(Image(balance_chart, width=400, height=220))
    story.append(Spacer(1, 12))
else:
    story.append(Paragraph("[sales_balance_2025.png not found]", styles['BodyText']))


# Citation
story.append(Spacer(1, 24))
story.append(Paragraph("<font size=10 color=grey>Source: Vicinity Safety, 2025. Data from import_data/</font>", styles['Normal']))

# New headline for volunteering report
story.append(Spacer(1, 24))
story.append(Paragraph("<b>Vertical A Volunteering Report</b>", styles['Heading1']))
story.append(Spacer(1, 12))
story.append(Paragraph(
    "Vicinity Safety would like to express our sincere gratitude to the students from the Foreign Trade University for their volunteer collaboration with our Marketing Strategies team. "
    "Your dedication, creativity, and teamwork have made a meaningful impact on our initiatives, and we deeply appreciate your valuable contributions.",
    styles['BodyText'])
)

story.append(Spacer(1, 18))
# Calculate and display total volunteer hours for all students
import csv
cert_path = "import_data/Certifications Volunteer Group/3ef12cde-7800-4562-8aed-d009b9caffc3.csv"
total_hours = 0
with open(cert_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["Group name"] == "Certification of Hours":
            total_hours += 20  # Assume 20 hours per certification

story.append(Paragraph(
    f"<b>Total volunteer hours contributed by Foreign Trade University students:</b> {total_hours} hours",
    styles['BodyText'])
)
story.append(Paragraph(
    "<font size=10 color=grey>Source: Certifier.io</font>",
    styles['Normal'])
)
story.append(Spacer(1, 18))


# Add new section for Vertical B Research and Development Summary at the end
story.append(Spacer(1, 24))
story.append(Paragraph("<b>Vertical B Research and Development Summary</b>", styles['Heading1']))
story.append(Spacer(1, 12))

story.append(Paragraph(
    "Vicinity Safety's Vertical B Research and Development is a new initiative aimed at creating better opportunities for the company's scaling and growth. "
    "While this vertical is challenging and may not generate immediate income, Vicinity Safety is currently a leader in this field—specifically in Data Centers Fire Suppressing Projectile technology with our VFEP Intellectual Property Registration and ownership.",
    styles['BodyText'])
)

# Add Vertical B Upfront Cost Table
from reportlab.platypus import Table, TableStyle
import csv
story.append(Spacer(1, 12))
story.append(Paragraph("<b>Vertical B Upfront Cost Table (Short Version)</b>", styles['Heading2']))
table_data = []
with open("export/vertical_b_upfront_cost_short.csv", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        table_data.append(row)
table = Table(table_data, colWidths=[300, 100])
table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), '#f1f5f9'),
    ('TEXTCOLOR', (0,0), (-1,0), '#1e293b'),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('FONTNAME', (0,0), (-1,0), font_name),
    ('FONTSIZE', (0,0), (-1,0), 10),
    ('FONTSIZE', (0,1), (-1,-1), 9),
    ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ('GRID', (0,0), (-1,-1), 0.5, '#94a3b8'),
]))
story.append(table)
story.append(Spacer(1, 18))


# Build PDF with 10px left/right margins

doc = SimpleDocTemplate(output_pdf, pagesize=A4, leftMargin=10, rightMargin=10)
doc.build(story, onFirstPage=add_logo)

print(f"Executive summary PDF created: {output_pdf}")
