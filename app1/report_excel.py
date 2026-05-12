"""
Generate the IESTP Paucartambo attendance report Excel
with professional styling and automatic calculations.
"""

import calendar
import datetime
import io

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)
from openpyxl.utils import get_column_letter
from openpyxl.styles.numbers import FORMAT_TEXT


# ─────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────
NAVY        = "0B2161"
LIGHT_BLUE  = "DCE6F1"
YELLOW_BG   = "FFF2CC"
RED_BG      = "F4CCCC"
GREEN_BG    = "D9EAD3"
ORANGE_BG   = "FCE5CD"
PURPLE_BG   = "D9D2E9"
GREY_BG     = "E7E6E6"
WHITE       = "FFFFFF"
LIGHT_ROW   = "F8FBFF"
WEEKEND_BG  = "EEEEEE"

GREEN_TEXT  = "008000"
RED_TEXT    = "C00000"

# ─────────────────────────────────────────────────────────────
# STYLE HELPERS
# ─────────────────────────────────────────────────────────────
def _side(color="000000", style="thin"):
    return Side(border_style=style, color=color)


def _border(style="thin", color="B7B7B7"):
    s = _side(color, style)
    return Border(left=s, right=s, top=s, bottom=s)


def _fill(color):
    return PatternFill("solid", fgColor=color)


def _font(
    bold=False,
    size=10,
    color="000000",
    name="Arial",
    italic=False
):
    return Font(
        bold=bold,
        size=size,
        color=color,
        name=name,
        italic=italic
    )


def _align(h="center", v="center", wrap=True):
    return Alignment(
        horizontal=h,
        vertical=v,
        wrap_text=wrap
    )


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────
def build_report(
    students_data: list[dict],
    month: int,
    year: int
) -> bytes:

    wb = Workbook()
    ws = wb.active
    ws.title = "ASISTENCIA"

    # ─────────────────────────────────────────────────────────
    # MONTHS
    # ─────────────────────────────────────────────────────────
    MONTHS_ES = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SETIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }

    month_name = MONTHS_ES[month]

    days_in_month = calendar.monthrange(year, month)[1]

    day_abbr_es = {
        0: "L",
        1: "M",
        2: "M",
        3: "J",
        4: "V",
        5: "S",
        6: "D"
    }

    # ─────────────────────────────────────────────────────────
    # COLUMNS
    # ─────────────────────────────────────────────────────────
    COL_NUM     = 1
    COL_DNI     = 2
    COL_NAME    = 3
    COL_CARGO   = 4
    COL_COND    = 5

    COL_DAY1    = 6
    COL_DAYN    = COL_DAY1 + days_in_month - 1

    COL_T       = COL_DAYN + 1
    COL_F       = COL_DAYN + 2
    COL_P       = COL_DAYN + 3
    COL_PS      = COL_DAYN + 4
    COL_CS      = COL_DAYN + 5
    COL_TOTAL   = COL_DAYN + 6

    TOTAL_COLS  = COL_TOTAL

    # ─────────────────────────────────────────────────────────
    # ROWS
    # ─────────────────────────────────────────────────────────
    ROW_TITLE1      = 2
    ROW_TITLE2      = 3
    ROW_SUBTITLE    = 5
    ROW_META        = 8

    ROW_HDR_LABELS  = 10
    ROW_HDR_DAYS    = 11
    ROW_HDR_ABBR    = 12

    ROW_DATA_START  = 13

    # ─────────────────────────────────────────────────────────
    # COLUMN WIDTHS
    # ─────────────────────────────────────────────────────────
    widths = {
        COL_NUM: 5,
        COL_DNI: 13,
        COL_NAME: 35,
        COL_CARGO: 24,
        COL_COND: 14,
    }

    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    for col in range(COL_DAY1, COL_DAYN + 1):
        ws.column_dimensions[get_column_letter(col)].width = 3

    for col in [COL_T, COL_F, COL_P, COL_PS, COL_CS]:
        ws.column_dimensions[get_column_letter(col)].width = 6

    ws.column_dimensions[get_column_letter(COL_TOTAL)].width = 12

    # ─────────────────────────────────────────────────────────
    # ROW HEIGHTS
    # ─────────────────────────────────────────────────────────
    ws.row_dimensions[ROW_TITLE1].height = 28
    ws.row_dimensions[ROW_TITLE2].height = 34
    ws.row_dimensions[ROW_HDR_LABELS].height = 34

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    def merge_write(
        r1,
        c1,
        r2,
        c2,
        value,
        font=None,
        fill=None,
        align=None,
        border=None
    ):
        ws.merge_cells(
            start_row=r1,
            start_column=c1,
            end_row=r2,
            end_column=c2
        )

        cell = ws.cell(r1, c1, value)

        if font:
            cell.font = font

        if fill:
            cell.fill = fill

        if align:
            cell.alignment = align

        if border:
            cell.border = border

        return cell

    # ─────────────────────────────────────────────────────────
    # TITLES
    # ─────────────────────────────────────────────────────────
    merge_write(
        ROW_TITLE1,
        2,
        ROW_TITLE1,
        TOTAL_COLS,
        "Instituto de Educación Superior Tecnológico Público",
        font=_font(
            bold=True,
            size=16,
            color="FF0000"
        ),
        align=_align()
    )

    merge_write(
        ROW_TITLE2,
        2,
        ROW_TITLE2,
        TOTAL_COLS,
        '"PAUCARTAMBO"',
        font=_font(
            bold=True,
            size=22,
            color="FF0000"
        ),
        align=_align()
    )

    merge_write(
        ROW_SUBTITLE,
        2,
        ROW_SUBTITLE,
        TOTAL_COLS,
        "FORMATO: REPORTE DE ASISTENCIA DETALLADO PERSONAL",
        font=_font(
            bold=True,
            size=11
        ),
        align=_align()
    )

    # ─────────────────────────────────────────────────────────
    # META
    # ─────────────────────────────────────────────────────────
    merge_write(
        ROW_META,
        COL_NUM,
        ROW_META,
        COL_DNI,
        "DRE: PASCO",
        font=_font(
            bold=True,
            color="0070C0"
        ),
        align=_align("left")
    )

    merge_write(
        ROW_META,
        COL_NAME,
        ROW_META,
        COL_DAYN,
        f"PERIODO(mes/año) {month_name}/{year}",
        font=_font(
            bold=True
        ),
        align=_align()
    )

    merge_write(
        ROW_META,
        COL_T,
        ROW_META,
        TOTAL_COLS,
        "Turno: Tarde",
        font=_font(
            bold=True
        ),
        align=_align("right")
    )

    # ─────────────────────────────────────────────────────────
    # HEADERS
    # ─────────────────────────────────────────────────────────
    hdr_fill = _fill(LIGHT_BLUE)
    hdr_font = _font(
        bold=True,
        size=9
    )

    hdr_border = _border()

    headers = [
        (COL_NUM, "N°"),
        (COL_DNI, "DNI"),
        (COL_NAME, "Apellidos y Nombres"),
        (COL_CARGO, "Cargo"),
        (COL_COND, "Condición"),
    ]

    for col, text in headers:

        ws.merge_cells(
            start_row=ROW_HDR_LABELS,
            start_column=col,
            end_row=ROW_HDR_ABBR,
            end_column=col
        )

        cell = ws.cell(ROW_HDR_LABELS, col, text)

        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = _align()
        cell.border = hdr_border

    # DAYS TITLE
    merge_write(
        ROW_HDR_LABELS,
        COL_DAY1,
        ROW_HDR_LABELS,
        COL_DAYN,
        f"DIAS CALENDARIO - {month_name}",
        font=hdr_font,
        fill=hdr_fill,
        align=_align(),
        border=hdr_border
    )

    # DAY NUMBERS
    for day in range(1, days_in_month + 1):

        col = COL_DAY1 + day - 1

        c1 = ws.cell(
            ROW_HDR_DAYS,
            col,
            day
        )

        c1.font = hdr_font
        c1.fill = hdr_fill
        c1.alignment = _align()
        c1.border = hdr_border

        weekday = datetime.date(
            year,
            month,
            day
        ).weekday()

        c2 = ws.cell(
            ROW_HDR_ABBR,
            col,
            day_abbr_es[weekday]
        )

        c2.font = hdr_font
        c2.fill = hdr_fill
        c2.alignment = _align()
        c2.border = hdr_border

    # SUMMARY COLUMNS
    summary_columns = [
        (COL_T, "T", YELLOW_BG),
        (COL_F, "F", RED_BG),
        (COL_P, "P", GREEN_BG),
        (COL_PS, "P/S", ORANGE_BG),
        (COL_CS, "C/S", PURPLE_BG),
        (COL_TOTAL, "Días\nTrabajados", GREY_BG),
    ]

    for col, text, bg in summary_columns:

        ws.merge_cells(
            start_row=ROW_HDR_LABELS,
            start_column=col,
            end_row=ROW_HDR_ABBR,
            end_column=col
        )

        cell = ws.cell(
            ROW_HDR_LABELS,
            col,
            text
        )

        cell.font = _font(
            bold=True,
            size=8
        )

        cell.fill = _fill(bg)
        cell.alignment = _align()
        cell.border = hdr_border

    # ─────────────────────────────────────────────────────────
    # DATA
    # ─────────────────────────────────────────────────────────
    thin_border = _border()

    for index, student in enumerate(students_data):

        row = ROW_DATA_START + index

        alt_fill = (
            _fill(LIGHT_ROW)
            if index % 2 == 0
            else _fill(WHITE)
        )

        def write_data(
            col,
            value,
            align_h="center",
            bold=False,
            fill=None,
            color="000000"
        ):

            cell = ws.cell(
                row=row,
                column=col,
                value=value
            )

            cell.font = _font(
                bold=bold,
                size=9,
                color=color
            )

            cell.fill = fill or alt_fill
            cell.alignment = _align(align_h)
            cell.border = thin_border

            return cell

        # BASIC INFO
        write_data(
            COL_NUM,
            student.get("number", index + 1),
            bold=True
        )

        dni_cell = write_data(
            COL_DNI,
            student.get("dni", "")
        )

        dni_cell.number_format = FORMAT_TEXT

        write_data(
            COL_NAME,
            student.get("name", ""),
            align_h="left"
        )

        write_data(
            COL_CARGO,
            student.get("position", ""),
            align_h="left"
        )

        write_data(
            COL_COND,
            student.get("condition", "Contratado")
        )

        # ATTENDANCE
        attendance = student.get(
            "attendance",
            set()
        )

        attended = 0
        faltas = 0

        for day in range(1, days_in_month + 1):

            col = COL_DAY1 + day - 1

            weekday = datetime.date(
                year,
                month,
                day
            ).weekday()

            is_weekend = weekday >= 5

            if is_weekend:

                cell = ws.cell(
                    row=row,
                    column=col,
                    value=""
                )

                cell.fill = _fill(WEEKEND_BG)
                cell.border = thin_border
                cell.alignment = _align()

                continue

            if day in attendance:

                cell = ws.cell(
                    row=row,
                    column=col,
                    value="A"
                )

                cell.font = _font(
                    bold=True,
                    size=8,
                    color=GREEN_TEXT
                )

                attended += 1

            else:

                cell = ws.cell(
                    row=row,
                    column=col,
                    value="F"
                )

                cell.font = _font(
                    bold=True,
                    size=8,
                    color=RED_TEXT
                )

                faltas += 1

            cell.fill = alt_fill
            cell.border = thin_border
            cell.alignment = _align()

        # TOTALS
        write_data(
            COL_T,
            0,
            fill=_fill(YELLOW_BG)
        )

        write_data(
            COL_F,
            faltas,
            fill=_fill(RED_BG)
        )

        write_data(
            COL_P,
            0,
            fill=_fill(GREEN_BG)
        )

        write_data(
            COL_PS,
            0,
            fill=_fill(ORANGE_BG)
        )

        write_data(
            COL_CS,
            0,
            fill=_fill(PURPLE_BG)
        )

        write_data(
            COL_TOTAL,
            attended,
            bold=True,
            fill=_fill(GREY_BG)
        )

    # ─────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────
    last_data_row = ROW_DATA_START + len(students_data) - 1

    footer_row = last_data_row + 3

    today = datetime.date.today()

    merge_write(
        footer_row,
        COL_TOTAL - 2,
        footer_row,
        TOTAL_COLS,
        f"Paucartambo, {today.day:02d} de {month_name.lower()} del {year}",
        font=_font(
            italic=True,
            size=9
        ),
        align=_align("right")
    )

    # ─────────────────────────────────────────────────────────
    # FREEZE PANES
    # ─────────────────────────────────────────────────────────
    ws.freeze_panes = ws["F13"]

    # ─────────────────────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────────────────────
    buffer = io.BytesIO()

    wb.save(buffer)

    buffer.seek(0)

    return buffer.read()