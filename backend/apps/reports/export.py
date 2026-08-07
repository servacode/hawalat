"""حوالات — تصدير التقارير: Excel (openpyxl) و PDF عربي (reportlab + تشكيل)."""

import io
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONTS_DIR = Path(__file__).parent / "fonts"

_registered = False


def _register_fonts():
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont("ArabicFont", str(FONTS_DIR / "Amiri-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("ArabicFont-Bold", str(FONTS_DIR / "Amiri-Bold.ttf")))
    _registered = True


def _ar(text: str) -> str:
    """تهيئة النص العربي للعرض في PDF (تشكيل + اتجاه)."""
    return get_display(arabic_reshaper.reshape(str(text)))


def to_xlsx(report: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "تقرير"
    ws.sheet_view.rightToLeft = True

    ws.append([report["title"]])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    ws.append(report["columns"])
    header_row = ws.max_row
    for cell in ws[header_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0D9488")
        cell.alignment = Alignment(horizontal="center")
    for row in report["rows"]:
        ws.append(row)
    for column_cells in ws.columns:
        width = max((len(str(c.value or "")) for c in column_cells), default=8)
        ws.column_dimensions[column_cells[0].column_letter].width = min(width + 4, 40)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(report: dict) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
    )
    title_style = ParagraphStyle("t", fontName="ArabicFont-Bold", fontSize=16, alignment=1)
    # الأعمدة معكوسة (RTL): آخر عمود يظهر أولاً يميناً
    header = [_ar(c) for c in reversed(report["columns"])]
    body = [[_ar(v) for v in reversed(row)] for row in report["rows"]]
    data = [header] + (body or [[_ar("لا بيانات")] + [""] * (len(header) - 1)])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "ArabicFont"),
                ("FONTNAME", (0, 0), (-1, 0), "ArabicFont-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B9C4CE")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F6")]),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    doc.build([Paragraph(_ar(report["title"]), title_style), Spacer(1, 8 * mm), table])
    return buf.getvalue()
