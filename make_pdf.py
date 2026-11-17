"""Render README.md to a PDF with figures embedded -> storm-capstone.pdf.

Uses fpdf2 (pure Python). Handles the subset of markdown the README uses:
# / ## / ### headings, tables, bullets, blockquotes, code blocks, images.
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
        self.cell(0, 8, "Storm capstone - RQ2 analysis", align="C")


def clean(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = t.replace("\u2192", "->").replace("\u2014", "-").replace("\u2013", "-")
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2248", "~").replace("\u00b0", " deg")
    t = t.replace("\u03c1", "rho")
    return t.encode("latin-1", "replace").decode("latin-1")


def render_table(pdf, rows):
    ncol = len(rows[0])
    pdf.set_font("helvetica", "", 7.5)
    widths = [0] * ncol
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], pdf.get_string_width(clean(c)) + 4)
    scale = min(1.0, CW / sum(widths))
    widths = [w * scale for w in widths]
    for ri, r in enumerate(rows):
        if pdf.get_y() > 265:
            pdf.add_page()
        pdf.set_font("helvetica", "B" if ri == 0 else "", 7.5)
        pdf.set_fill_color(230, 235, 240) if ri == 0 else None
        maxh = 5
        x0 = pdf.get_x()
        for i, c in enumerate(r):
            pdf.cell(widths[i], 5, clean(c.strip()),
                     border=1, fill=ri == 0)
        pdf.ln()


def main():
    lines = open("README.md", encoding="utf-8").read().splitlines()
    pdf = Doc()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    in_code = False
    table_buf = []
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.strip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            pdf.set_font("courier", "", 8)
            pdf.set_text_color(60)
            pdf.multi_cell(CW, 4, clean(ln))
            pdf.set_text_color(0)
            i += 1
            continue
        # accumulate markdown table rows
        if ln.strip().startswith("|"):
            cells = [c for c in ln.strip().strip("|").split("|")]
            if not re.match(r"^[\s:\-]+$", "".join(cells).replace(" ", "")):
                table_buf.append(cells)
            i += 1
            continue
        elif table_buf:
            render_table(pdf, table_buf)
            table_buf = []
            pdf.ln(2)

        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", ln.strip())
        if m:
            img = m.group(1)
            if pdf.get_y() > 180:
                pdf.add_page()
            pdf.ln(2)
            pdf.image(img, x=MARGIN + 10, w=CW - 20)
            pdf.ln(4)
        elif ln.startswith("### "):
            pdf.ln(3)
            pdf.set_font("helvetica", "B", 12)
            pdf.multi_cell(CW, 6, clean(ln[4:]))
        elif ln.startswith("## "):
            pdf.ln(4)
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(20, 60, 110)
            pdf.multi_cell(CW, 7, clean(ln[3:]))
            pdf.set_text_color(0)
        elif ln.startswith("# "):
            pdf.set_font("helvetica", "B", 18)
            pdf.multi_cell(CW, 9, clean(ln[2:]))
        elif ln.startswith("> "):
            pdf.set_font("helvetica", "I", 10)
            pdf.set_text_color(80)
            pdf.multi_cell(CW, 5, "  " + clean(ln[2:]))
            pdf.set_text_color(0)
        elif ln.strip().startswith("- "):
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(CW, 5, "  - " + clean(ln.strip()[2:]))
        elif ln.strip().startswith("---"):
            pdf.ln(2)
        elif not ln.strip():
            pdf.ln(3)
        else:
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(CW, 5, clean(ln))
        i += 1
    if table_buf:
        render_table(pdf, table_buf)
    pdf.output("storm-capstone.pdf")
    print("wrote storm-capstone.pdf")


if __name__ == "__main__":
    main()
