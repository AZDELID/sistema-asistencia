from __future__ import annotations

import io
import logging
import os
from pathlib import Path

import numpy as np
import qrcode
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# =============================================================================
# ASSETS
# =============================================================================

from pathlib import Path

# =============================================================================
# RUTAS DE ARCHIVOS (PATHS)
# =============================================================================
# Define la ruta base donde se encuentran las imágenes y recursos estáticos
_ASSETS_DIR = Path(__file__).parent / "static" / "app1" / "fotocheck_assets"

# Ruta específica del archivo de imagen que sirve como base o fondo del fotocheck
PLANTILLA_PATH = _ASSETS_DIR / "plantilla.jpeg"
LOGO_PATH = _ASSETS_DIR / "logo.png"

# =============================================================================
# TAMAÑO DE LA TARJETA (CARD SIZE)
# =============================================================================
# Dimensiones totales en píxeles de la imagen final (Ancho x Alto)
CARD_W = 650   # Corresponde a 5.5 cm
CARD_H = 1004  # Corresponde a 8.5 cm
# =============================================================================
# CONFIGURACIÓN DE LA FOTO (PHOTO)
# =============================================================================
# Coordenadas del centro (X, Y) donde se posicionará la foto del empleado
PHOTO_CX = 325
PHOTO_CY = 405
# Radio del círculo de la foto (si se recorta de forma circular)
PHOTO_R = 146

# =============================================================================
# ÁREA DEL NOMBRE (NAME)
# =============================================================================
# Define el recuadro (bounding box) donde se escribirá el nombre
# (X1, Y1) es la esquina superior izquierda; (X2, Y2) la inferior derecha
NAME_X1, NAME_Y1 = 70, 550
NAME_X2, NAME_Y2 = 700, 655

# =====================1=======================================================
# CAMPOS DE TEXTO ADICIONALES (TEXT FIELDS)
# =============================================================================
# Coordenadas de los rectángulos delimitadores para cada dato específico.
# Se usan para centrar o ajustar el texto automáticamente dentro de esos límites.

# Área para el número de documento de identidad
DNI_X1, DNI_Y1, DNI_X2, DNI_Y2 = 185, 670, 470, 800

# Área para el puesto o cargo laboral
CARGO_X1, CARGO_Y1, CARGO_X2, CARGO_Y2 = 185, 740, 470, 900

# Área para el departamento o área a la que pertenece
AREA_X1, AREA_Y1, AREA_X2, AREA_Y2 = 185, 818, 470, 1000

# =============================================================================
# CÓDIGO QR (QR)
# =============================================================================
# Define el espacio donde se pegará la imagen del código QR generado
QR_X1, QR_Y1 = 200, 680
QR_X2, QR_Y2 = 800, 900

# (Nota: Las líneas comentadas abajo son coordenadas alternativas o de versiones previas)
#QR_X1, QR_Y1 = 660, 983  
#QR_X2, QR_Y2 = 840, 1246

# =============================================================================
# ESTADO / ETIQUETA (STATUS)
# =============================================================================
# Coordenadas del centro (CX, CY) para un indicador de estado (ej: "Activo")
ESTADO_CX = 420
ESTADO_CY = 1339

# Half-Width y Half-Height: Mitad del ancho y mitad del alto para dibujar el cuadro de estado
ESTADO_HW = 175
ESTADO_HH = 44

# =============================================================================
# PALETA DE COLORES (COLORS)
# =============================================================================
# Definición de colores en formato RGB (Rojo, Verde, Azul)

# Azul marino oscuro: Ideal para títulos o encabezados institucionales
C_NAVY = (15, 45, 100)

# Gris muy oscuro / Negro azulado: Para textos secundarios que requieren lectura fácil
C_DARK = (20, 30, 60)

# Blanco puro: Para textos que van sobre fondos oscuros o limpieza visual
C_WHITE = (255, 255, 255)

# =============================================================================
# TIPOGRAFÍAS (FONTS)
# =============================================================================
# (Aquí iría la carga de archivos .ttf para el estilo de letra)

def _find_font(bold: bool) -> str:

    candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )

    return next((p for p in candidates if os.path.exists(p)), "")


_F_BOLD = _find_font(True)

_F_REGULAR = _find_font(False)


def _font(path: str, size: int):

    try:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass

    return ImageFont.load_default()


# =============================================================================
# VALIDATION
# =============================================================================


def validate_assets():

    if not PLANTILLA_PATH.exists():
        return False, f"Plantilla no encontrada: {PLANTILLA_PATH}"

    return True, "OK"


# =============================================================================
# STORAGE
# =============================================================================


def _clear_field(field):

    if field and field.name:
        try:
            field.storage.delete(field.name)
        except Exception:
            pass


# =============================================================================
# TEXT HELPERS
# =============================================================================


def _fit_text(
    draw,
    text,
    max_width,
    font_path,
    max_size,
    min_size=18,
):

    for size in range(max_size, min_size - 1, -2):

        f = _font(font_path, size)

        bb = draw.textbbox((0, 0), text, font=f)

        width = bb[2] - bb[0]

        if width <= max_width:
            return f

    return _font(font_path, min_size)


def _fit_name(
    draw,
    full_name,
    max_width,
    font_path,
    max_size=58,
    min_size=22,
):

    words = full_name.upper().split()

    candidates = []

    # primer nombre + apellidos
    if len(words) >= 3:
        candidates.append(
            f"{words[0]} {words[-2]} {words[-1]}"
        )

    # solo apellidos
    if len(words) >= 2:
        candidates.append(
            f"{words[-2]} {words[-1]}"
        )

    # completo
    candidates.append(" ".join(words))

    # último apellido
    candidates.append(words[-1])

    fixed_size = 33

    f = _font(font_path, fixed_size)

    for text in candidates:

        bb = draw.textbbox((0, 0), text, font=f)

        width = bb[2] - bb[0]

        if width <= max_width:
            return text, f

    return candidates[-1], f


# =============================================================================
# BACKGROUND REMOVAL
# =============================================================================


def _remove_background(img):

    try:

        from rembg import remove as rembg_remove

        buf_in = io.BytesIO()

        img.save(buf_in, format="PNG")

        buf_in.seek(0)

        result = rembg_remove(buf_in.read())

        buf_out = io.BytesIO(result)

        buf_out.seek(0)

        return Image.open(buf_out).convert("RGBA")

    except Exception as exc:

        logger.debug("rembg failed: %s", exc)

        return img.convert("RGBA")


# =============================================================================
# FACE DETECTION
# =============================================================================


def _detect_face_crop(image_path: str, size: int):

    """
    Detecta rostro y conserva hombros.
    """

    try:

        from app1.views import _get_models

        mtcnn, _, _ = _get_models()

        pil = Image.open(image_path).convert("RGB")

        boxes, _ = mtcnn.detect(pil)

        if boxes is not None and len(boxes) > 0:

            x1, y1, x2, y2 = boxes[0]

            iw, ih = pil.size

            face_w = x2 - x1
            face_h = y2 - y1

            # más zoom
            pad_x = face_w * 0.70

            # menos espacio arriba
            top_pad = face_h * 0.45

            # hombros
            bottom_pad = face_h * 1.60

            nx1 = max(0, int(x1 - pad_x))
            ny1 = max(0, int(y1 - top_pad))

            nx2 = min(iw, int(x2 + pad_x))
            ny2 = min(ih, int(y2 + bottom_pad))

            crop = pil.crop((nx1, ny1, nx2, ny2))

            cw, ch = crop.size

            side = max(cw, ch)

            canvas = Image.new(
                "RGB",
                (side, side),
                (255, 255, 255),
            )

            ox = (side - cw) // 2

            # centrado visual
            oy = int((side - ch) * 0.35)

            canvas.paste(crop, (ox, oy))

            return canvas.resize(
                (size, size),
                Image.LANCZOS,
            )

    except Exception:

        logger.exception("Face detection failed")

    # fallback

    try:

        pil = Image.open(image_path).convert("RGB")

        ww, hh = pil.size

        m = min(ww, hh)

        pil = pil.crop(
            (
                (ww - m) // 2,
                (hh - m) // 2,
                (ww + m) // 2,
                (hh + m) // 2,
            )
        )

        return pil.resize((size, size), Image.LANCZOS)

    except Exception:

        return None


# =============================================================================
# CIRCULAR
# =============================================================================


def _make_circular(img, radius):

    size = radius * 2

    img = img.convert("RGBA")

    img = img.resize((size, size), Image.LANCZOS)

    mask = Image.new("L", (size, size), 0)

    draw = ImageDraw.Draw(mask)

    draw.ellipse(
        (0, 0, size - 1, size - 1),
        fill=255,
    )

    out = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0),
    )

    out.paste(img, (0, 0), mask)

    return out


# =============================================================================
# QR
# =============================================================================


def _load_qr_logo():

    if not LOGO_PATH.exists():
        return None

    try:
        return Image.open(LOGO_PATH).convert("RGBA")
    except Exception:
        logger.exception("QR logo load failed")
        return None


def _embed_qr_logo(qr_img):

    logo = _load_qr_logo()
    if logo is None:
        return qr_img

    qr_w, qr_h = qr_img.size
    max_logo_side = int(min(qr_w, qr_h) * 0.22)
    logo.thumbnail((max_logo_side, max_logo_side), Image.LANCZOS)

    logo_w, logo_h = logo.size
    ox = (qr_w - logo_w) // 2
    oy = (qr_h - logo_h) // 2

    # Fondo cuadrado blanco detrás del logo, casi del tamaño del logo actual
    bg_size = max(logo_w, logo_h) + 12
    bg = Image.new("RGBA", (bg_size, bg_size), (255, 255, 255, 255))

    bg_x = (qr_w - bg_size) // 2
    bg_y = (qr_h - bg_size) // 2

    overlay = Image.new("RGBA", qr_img.size, (0, 0, 0, 0))
    overlay.paste(bg, (bg_x, bg_y))
    overlay.paste(logo, (ox, oy), logo)

    return Image.alpha_composite(qr_img, overlay)


def _make_qr(data):

    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )

    qr.add_data(data)

    qr.make(fit=True)

    qr_img = qr.make_image(
        fill_color=(0, 0, 0),       # Color de los módulos (Negro)
        back_color="transparent"    # Esto activa la transparencia directamente
    ).convert("RGBA")

    return _embed_qr_logo(qr_img)


def generate_qr_with_logo(student):

    try:

        _clear_field(student.qr_code)

        qr_img = _make_qr(str(student.unique_id))

        buf = io.BytesIO()

        qr_img.save(buf, format="PNG")

        buf.seek(0)

        student.qr_code.save(
            f"qr_{student.unique_id}.png",
            ContentFile(buf.read()),
            save=True,
        )

        return True

    except Exception:

        logger.exception("QR failed")

        return False


def _paste_qr(card, student):

    if not student.qr_code:
        return

    try:

        qr = Image.open(student.qr_code.path).convert("RGBA")

        side = min(
            QR_X2 - QR_X1,
            QR_Y2 - QR_Y1,
        )

        qr = qr.resize((side, side), Image.LANCZOS)

        ox = QR_X1 + ((QR_X2 - QR_X1) - side) // 2

        oy = QR_Y1 + ((QR_Y2 - QR_Y1) - side) // 2

        bg = Image.new(
            "RGBA",
            (side + 8, side + 8),
            (255, 255, 255, 255),
        )

        card.paste(bg, (ox - 4, oy - 4), bg)

        card.paste(qr, (ox, oy), qr)

    except Exception:

        logger.exception("QR paste failed")


# =============================================================================
# PHOTO
# =============================================================================


def _paste_photo(card, student):

    src = None

    if student.image:

        try:

            face = _detect_face_crop(
                student.image.path,
                PHOTO_R * 2,
            )

            if face is not None:
                src = _remove_background(face)

        except Exception:

            logger.exception("Photo failed")

    if src is None:

        src = Image.new(
            "RGBA",
            (PHOTO_R * 2, PHOTO_R * 2),
            (210, 220, 235, 255),
        )

    circ = _make_circular(src, PHOTO_R)

    # centrado visual
    offset_y = 4

    card.paste(
        circ,
        (
            PHOTO_CX - PHOTO_R,
            PHOTO_CY - PHOTO_R + offset_y,
        ),
        circ,
    )


# =============================================================================
# BUILD CARD
# =============================================================================


def _build_card(student):

    ok, _ = validate_assets()

    if not ok:
        return None

    card = Image.open(PLANTILLA_PATH).convert("RGBA")

    if card.size != (CARD_W, CARD_H):

        card = card.resize(
            (CARD_W, CARD_H),
            Image.LANCZOS,
        )

    draw = ImageDraw.Draw(card)

    # =============================================================================
    # PHOTO
    # =============================================================================

    _paste_photo(card, student)

    # =============================================================================
    # NAME BAND
    # =============================================================================

    full_name = student.name.upper()

    disp_name, nfont = _fit_name(
        draw,
        full_name,
        NAME_X2 - NAME_X1 - 40,
        _F_BOLD,
        max_size=58,
        min_size=22,
    )

    bb = draw.textbbox((0, 0), disp_name, font=nfont)

    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    # centrar texto horizontalmente y verticalmente dentro del área de nombre
    tx = NAME_X1 + ((NAME_X2 - NAME_X1) - tw) // 2
    ty = NAME_Y1 + ((NAME_Y2 - NAME_Y1) - th) // 2 - bb[1]

    draw.text(
        (tx, ty),
        disp_name,
        font=nfont,
        fill=(0, 0, 0),  # texto en blanco sobre la plantilla
    )

    # =============================================================================
    # DNI
    # =============================================================================

    dni_text = student.dni or "—"

    dni_font = _fit_text(
        draw,
        dni_text,
        DNI_X2 - DNI_X1,
        _F_BOLD,
        26,
    )

    draw.text(
        (DNI_X1, DNI_Y1),
        dni_text,
        font=dni_font,
        fill=C_DARK,
    )

    # =============================================================================
    # CARGO
    # =============================================================================

    cargo_text = (
        student.position.upper()
        if student.position
        else "—"
    )

    cargo_font = _fit_text(
        draw,
        cargo_text,
        CARGO_X2 - CARGO_X1,
        _F_BOLD,
        26,
    )

    draw.text(
        (CARGO_X1, CARGO_Y1),
        cargo_text,
        font=cargo_font,
        fill=C_DARK,
    )

    # =============================================================================
    # AREA
    # =============================================================================

    area_text = (
        student.area.upper()
        if student.area
        else "—"
    )

    area_font = _fit_text(
        draw,
        area_text,
        AREA_X2 - AREA_X1,
        _F_BOLD,
        24,
    )

    draw.text(
        (AREA_X1, AREA_Y1),
        area_text,
        font=area_font,
        fill=C_DARK,
    )

    # =============================================================================
    # STATUS
    # =============================================================================

    if not student.authorized:

        draw.rounded_rectangle(
            (
                ESTADO_CX - ESTADO_HW,
                ESTADO_CY - ESTADO_HH,
                ESTADO_CX + ESTADO_HW,
                ESTADO_CY + ESTADO_HH,
            ),
            radius=ESTADO_HH,
            fill=(160, 30, 30, 240),
        )

        fb = _font(_F_BOLD, 36)

        txt = "INACTIVO"

        bb = draw.textbbox((0, 0), txt, font=fb)

        draw.text(
            (
                ESTADO_CX - (bb[2] - bb[0]) // 2,
                ESTADO_CY - (bb[3] - bb[1]) // 2 - bb[1],
            ),
            txt,
            font=fb,
            fill=C_WHITE,
        )

    # =============================================================================
    # QR
    # =============================================================================

    _paste_qr(card, student)

    return card.convert("RGB")


# =============================================================================
# PNG
# =============================================================================


def generate_fotocheck_png(student):

    try:

        _clear_field(student.fotocheck_png)

        card = _build_card(student)

        if card is None:
            return False

        buf = io.BytesIO()

        card.save(
            buf,
            format="PNG",
            dpi=(300, 300),
        )

        buf.seek(0)

        student.fotocheck_png.save(
            f"fotocheck_{student.unique_id}.png",
            ContentFile(buf.read()),
            save=True,
        )

        return True

    except Exception:

        logger.exception("PNG failed")

        return False


# =============================================================================
# PDF
# =============================================================================


def generate_fotocheck_pdf(student):

    try:

        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas as rl_canvas

        _clear_field(student.fotocheck_pdf)

        if (
            student.fotocheck_png
            and os.path.exists(student.fotocheck_png.path)
        ):

            png_buf = io.BytesIO(
                open(student.fotocheck_png.path, "rb").read()
            )

        else:

            return False

        page_w = CARD_W / 300 * 25.4 * mm

        page_h = CARD_H / 300 * 25.4 * mm

        pdf_buf = io.BytesIO()

        c = rl_canvas.Canvas(
            pdf_buf,
            pagesize=(page_w, page_h),
        )

        c.drawImage(
            ImageReader(png_buf),
            0,
            0,
            width=page_w,
            height=page_h,
        )

        c.save()

        pdf_buf.seek(0)

        student.fotocheck_pdf.save(
            f"fotocheck_{student.unique_id}.pdf",
            ContentFile(pdf_buf.read()),
            save=True,
        )

        return True

    except Exception:

        logger.exception("PDF failed")

        return False


# =============================================================================
# MAIN
# =============================================================================


def generate_all_fotocheck_assets(student):

    results = {
        "qr": generate_qr_with_logo(student),
        "png": generate_fotocheck_png(student),
        "pdf": generate_fotocheck_pdf(student),
    }

    logger.info(
        "Fotocheck generado para %s: %s",
        student.name,
        results,
    )

    return results