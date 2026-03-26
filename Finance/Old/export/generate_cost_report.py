# Cost Report Generation Script
# This script generates a PDF cost report for Vertical A and Vertical B
# using data from the specified CSV files.

import pandas as pd
from fpdf import FPDF
import os

# File paths
vertical_a_cost_path = 'import_data/Sales Management-Mastersheet - Cost.csv'
vertical_b_plan_path = 'import_data/Vertical B Finance Planning.csv'
output_pdf_path = 'export/vertical_cost_report.pdf'

# Read Vertical A cost data
vertical_a_df = pd.read_csv(vertical_a_cost_path, header=1)

# Read Vertical B planning data
vertical_b_df = pd.read_csv(vertical_b_plan_path, header=2)

# Extract cost rows for Vertical B (from 'Equipment Purchases' to 'Other specific expenses')
cost_rows = [
    'Equipment Purchases',
    'Company legal registration in Singapore',
    'Global Patent Application (PCT)',
    'Professional Legal Documents Preparation',
    'Research & Engineering Salaries',
    'Engineering Consultant (Gemini AI Pro)',
    'Materials & Equipment (Prototyping)',
    'Technical Documenting',
    'Certification/Audit Fees',
    'Business Development/Lobbying',
    'Materials Purchase (15%/sales)',
    'Sales & Marketing (25%/sales)',
    'Other specific expenses'
]

vertical_b_costs = vertical_b_df[vertical_b_df['Category'].isin(cost_rows)].copy()
for col in vertical_b_costs.columns[1:]:
    vertical_b_costs[col] = vertical_b_costs[col].apply(lambda x: float(str(x).replace(',', '').replace('$', '').strip()) if str(x).replace(',', '').replace('$', '').strip() else 0)
vertical_b_summary = vertical_b_costs.set_index('Category').sum(axis=1).reset_index()
vertical_b_summary.columns = ['Category', 'Total (USD)']

# Clean and summarize Vertical A costs
def parse_vnd(val):
    if isinstance(val, str):
        val = val.replace('₫', '').replace(',', '').replace(' ', '').strip()
        try:
            return int(val)
        except:
            return 0
    return 0

vertical_a_sum = vertical_a_df.copy()
for col in vertical_a_sum.columns[1:]:
    vertical_a_sum[col] = vertical_a_sum[col].apply(parse_vnd)
vertical_a_summary = vertical_a_sum.set_index(vertical_a_sum.columns[0]).sum(axis=1).reset_index()
vertical_a_summary.columns = ['Category', 'Total (VND)']

# PDF generation
class PDF(FPDF):
    def add_paragraph(self, text):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 8, text)
        self.ln(3)
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Vertical A & B Cost Report', 0, 1, 'C')
        self.ln(5)

    def section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1)
        self.ln(2)

    def table(self, df, title):
        self.section_title(title)
        self.set_font('Arial', '', 10)
        # Calculate effective page width (epw)
        epw = self.w - 2 * self.l_margin
        col_width = epw / len(df.columns)
        for col in df.columns:
            # Remove non-ASCII characters for PDF compatibility
            col_str = str(col).replace('₫', 'VND').encode('ascii', 'ignore').decode('ascii')
            self.cell(col_width, 8, col_str, 1)
        self.ln()
        for i, row in df.iterrows():
            for item in row:
                # Remove non-ASCII characters for PDF compatibility
                item_str = str(item).replace('₫', 'VND').encode('ascii', 'ignore').decode('ascii')
                self.cell(col_width, 8, item_str, 1)
            self.ln()
        self.ln(5)

    def summary_table(self, df, title, currency):
        self.section_title(title)
        self.set_font('Arial', 'B', 11)
        col_width = (self.w - 2 * self.l_margin) / 2
        self.cell(col_width, 8, 'Category', 1)
        self.cell(col_width, 8, f'Total ({currency})', 1)
        self.ln()
        self.set_font('Arial', '', 10)
        for i, row in df.iterrows():
            self.cell(col_width, 8, str(row.iloc[0]), 1)
            self.cell(col_width, 8, f"{row.iloc[1]:,.0f}", 1, 0, 'R')
            self.ln()
        self.ln(5)

pdf = PDF()
pdf.add_page()
# Add updated descriptive paragraphs for each vertical
vertical_a_desc = (
    "Vertical A's main costs are Cost of Goods Sold and Financial Reporting Outsourcing Cost. "
    "Cost of Goods Sold reflects the direct costs attributable to the production of goods sold, while Financial Reporting Outsourcing Cost covers third-party services for accounting and compliance. "
    "Other costs include Stocking, Tax, Operating, and miscellaneous items. The cost structure is typical for a sales-driven operation, with irregular but significant expenses in certain months."
)
vertical_b_desc = (
    "Vertical B represents the upfront cost prediction for research, development, and intellectual property creation. "
    "Major cost categories include legal registration, patent applications, professional legal documentation, R&D salaries, prototyping, technical documentation, certification, and business development. "
    "The cost structure is front-loaded with legal and R&D expenses, followed by periodic certification and business development costs. This reflects a growth and innovation-driven approach, with significant investment in technology and compliance to support future scaling."
)
pdf.add_paragraph(vertical_a_desc)
pdf.summary_table(vertical_a_summary, 'Vertical A Cost Summary', 'VND')
pdf.add_paragraph(vertical_b_desc)
pdf.summary_table(vertical_b_summary, 'Vertical B Cost Summary', 'USD')
# Add source note
source_note = (
    "Source: Vertical A data from Sales Management-Mastersheet - Cost.csv; Vertical B data from Vertical B Finance Planning.csv."
)
pdf.add_paragraph(source_note)

# Ensure export directory exists
os.makedirs('export', exist_ok=True)
pdf.output(output_pdf_path)
print(f'PDF report generated: {output_pdf_path}')
