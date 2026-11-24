"""Render ashik_capstone_report.md to ashik_capstone_report.pdf.

Adapted from make_pdf.py (fpdf2, pure Python). Handles the markdown subset
used by the report: # / ## headings, images, numbered lists, italics.
"""
import re

from fpdf import FPDF

PAGE_W = 210
MARGIN = 15
CW = PAGE_W - 2 * MARGIN  # content width mm


class Doc(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(130)
        self.cell(0, 8, "Ashik Dey Rupak - Capstone Report (RQ2)", align="C")


def clean(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = t.replace("\u2192", "->").replace("\u2014", "-").replace("\u2013", "-")
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2248", "~").replace("\u00b0", " deg")
    t = t.replace("\u03c1", "rho")
    t = t.replace("\u00d7", "x")
    return t.encode("latin-1", "replace").decode("latin-1")


def main():
    lines = open("ashik_capstone_report.md", encoding="utf-8").read().splitlines()
    pdf = Doc()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    for ln in lines:
        s = ln.strip()
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", s)
        if m:
            img = m.group(1)
            if pdf.get_y() > 180:
                pdf.add_page()
            pdf.ln(2)
            pdf.image(img, x=MARGIN + 10, w=CW - 20)
            pdf.ln(4)
        elif s.startswith("## "):
            pdf.ln(4)
            pdf.set_font("helvetica", "B", 13)
            pdf.set_text_color(20, 60, 110)
            pdf.multi_cell(CW, 7, clean(s[3:]))
            pdf.set_text_color(0)
        elif s.startswith("# "):
            pdf.set_font("helvetica", "B", 17)
            pdf.multi_cell(CW, 9, clean(s[2:]))
            pdf.ln(2)
        elif re.match(r"^\d+\.\s", s):
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(CW, 5, "   " + clean(s))
        elif s.startswith("*") and s.endswith("*"):
            pdf.set_font("helvetica", "I", 10)
            pdf.set_text_color(80)
            pdf.multi_cell(CW, 5, clean(s))
            pdf.set_text_color(0)
        elif not s:
            pdf.ln(3)
        else:
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(CW, 5, clean(s))
    pdf.output("ashik_capstone_report.pdf")
    print("wrote ashik_capstone_report.pdf")


if __name__ == "__main__":
    main()
