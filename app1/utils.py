"""
Utility functions shared between views and CameraManager.
"""
import io
import math
import logging
from datetime import timedelta

import qrcode
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)

# Minimum time between check-in and check-out.
# 10 minutes prevents accidental checkout while the person is still nearby.
_CHECKOUT_DELAY_SECONDS = 600


# ── QR generation ─────────────────────────────────────────────────────────────

def generate_qr_for_student(student) -> bool:
    """Encode student.unique_id into a QR PNG and save to student.qr_code."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(str(student.unique_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        student.qr_code.save(
            f"qr_{student.unique_id}.png",
            ContentFile(buf.read()),
            save=True,
        )
        logger.info("QR generated for %s (%s)", student.name, student.unique_id)
        return True
    except Exception:
        logger.exception("QR generation failed for %s", student.name)
        return False


# ── Attendance recording ───────────────────────────────────────────────────────

def record_attendance(student):
    """
    Create or update today's Attendance for *student*.
    Returns (event_type, message):
        event_type ∈ {'checked_in', 'checked_out', 'already_done', 'error'}

    Message format for already_done:
        "{name} — <reason>"  where reason is human-readable (shown in the kiosk UI)
    """
    from .models import Attendance  # local import avoids circular at module load
    try:
        today = timezone.localdate()
        attendance, created = Attendance.objects.get_or_create(
            student=student, date=today
        )
        if created:
            attendance.mark_checked_in()
            return 'checked_in', f"{student.name} checked in"

        if attendance.check_in_time and not attendance.check_out_time:
            elapsed_s  = (timezone.now() - attendance.check_in_time).total_seconds()
            remaining_s = _CHECKOUT_DELAY_SECONDS - elapsed_s

            if remaining_s > 0:
                # Still inside the protection window — show how long until checkout opens
                remaining_min = max(1, math.ceil(remaining_s / 60))
                return (
                    'already_done',
                    f"{student.name} — ya marcado, salida disponible en {remaining_min} min",
                )
            # Window passed — allow checkout
            attendance.mark_checked_out()
            return 'checked_out', f"{student.name} checked out"

        if attendance.check_in_time and attendance.check_out_time:
            return 'already_done', f"{student.name} — sesión completa hoy"

    except Exception as exc:
        logger.exception("Attendance error for %s", student.name)
        return 'error', str(exc)

    return 'already_done', f"{student.name} — sin acción"
