import csv
import io
import os
import threading
import time
import base64
import logging
import queue
from collections import defaultdict

import cv2
import numpy as np
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Student, Attendance, CameraConfiguration, SystemConfig
from .utils import generate_qr_for_student, record_attendance
from .fotocheck import generate_all_fotocheck_assets, generate_fotocheck_png, generate_fotocheck_pdf, generate_qr_with_logo

logger = logging.getLogger(__name__)

# ── ML model singletons ───────────────────────────────────────────────────────

_mtcnn  = None
_resnet = None
_device = None


def _get_models():
    global _mtcnn, _resnet, _device
    if _mtcnn is None:
        import torch
        from facenet_pytorch import InceptionResnetV1, MTCNN
        _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info("Loading ML models on %s", _device)
        _mtcnn  = MTCNN(keep_all=True, device=_device)
        _resnet = InceptionResnetV1(pretrained='vggface2').eval().to(_device)
    return _mtcnn, _resnet, _device


# ── Embedding cache ───────────────────────────────────────────────────────────

_embedding_cache    = None
_embedding_cache_ts = 0.0
_CACHE_TTL          = 30.0


def _get_known_embeddings(force=False):
    global _embedding_cache, _embedding_cache_ts
    now = time.monotonic()
    if not force and _embedding_cache is not None and (now - _embedding_cache_ts) < _CACHE_TTL:
        return _embedding_cache

    known_enc, known_names = [], []
    for student in Student.objects.filter(authorized=True):
        if not student.image:
            logger.warning("Student %r (pk=%s) has no image — skipped", student.name, student.pk)
            continue
        path = os.path.join(settings.MEDIA_ROOT, str(student.image))
        img  = cv2.imread(path)
        if img is None:
            logger.warning("Student %r (pk=%s) image unreadable at %s — skipped",
                           student.name, student.pk, path)
            continue
        rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            encs = _detect_and_encode(rgb)
        except Exception:
            logger.exception("Encoding failed for student %r (pk=%s) — skipped",
                             student.name, student.pk)
            continue

        if not encs:
            logger.warning("No face detected in photo for student %r (pk=%s) — skipped",
                           student.name, student.pk)
            continue

        if len(encs) > 1:
            # Registration photos should contain exactly one face. If MTCNN
            # finds several (e.g. a group photo was uploaded by mistake) use
            # only the first one to avoid polluting the known-face database.
            logger.warning("Student %r (pk=%s) photo has %d faces detected; "
                           "using only the first. Re-register with a solo portrait.",
                           student.name, student.pk, len(encs))

        # 1 embedding per student keeps known_enc and known_names 1-to-1.
        known_enc.append(encs[0])
        known_names.append(student.name)

    # Sanity check — both lists must be equal length before we cache.
    if len(known_enc) != len(known_names):
        logger.error("Embedding/name length mismatch (%d vs %d) — clearing cache",
                     len(known_enc), len(known_names))
        known_enc, known_names = [], []

    _embedding_cache    = (np.array(known_enc) if known_enc else np.array([]), known_names)
    _embedding_cache_ts = now
    logger.debug("Embedding cache rebuilt: %d students", len(known_names))
    return _embedding_cache


def invalidate_embedding_cache():
    global _embedding_cache
    _embedding_cache = None


# ── Face helpers ──────────────────────────────────────────────────────────────

# Pixels added on each side of the MTCNN bounding box before encoding.
# A margin of 20 px gives the model more context around the face and makes
# embeddings more tolerant of slight pose/angle changes.
_FACE_MARGIN = 20


def _detect_and_encode(image_rgb):
    import torch
    mtcnn, resnet, device = _get_models()
    results = []
    h_img, w_img = image_rgb.shape[:2]
    with torch.no_grad():
        boxes, _ = mtcnn.detect(image_rgb)
        if boxes is None:
            return results
        for box in boxes:
            # Expand crop by _FACE_MARGIN pixels (clamped to image bounds)
            x1 = max(0,     int(box[0]) - _FACE_MARGIN)
            y1 = max(0,     int(box[1]) - _FACE_MARGIN)
            x2 = min(w_img, int(box[2]) + _FACE_MARGIN)
            y2 = min(h_img, int(box[3]) + _FACE_MARGIN)
            face = image_rgb[y1:y2, x1:x2]
            if face.size == 0:
                continue
            face = cv2.resize(face, (160, 160))
            t = (torch.tensor(
                    np.transpose(face, (2, 0, 1)).astype(np.float32) / 255.0
                 ).unsqueeze(0).to(device))
            enc = resnet(t).cpu().detach().numpy().flatten()
            results.append(enc)
    return results


def _recognize(known_enc, known_names, test_encs, threshold=0.6):
    out = []
    n_known = len(known_names)
    for enc in test_encs:
        if len(known_enc) == 0 or n_known == 0:
            out.append(('Unknown', 0.0))
            continue
        dists = np.linalg.norm(known_enc - enc, axis=1)
        idx   = int(np.argmin(dists))
        if idx >= n_known:
            # known_enc and known_names are out of sync — treat as unknown
            # rather than crashing. This should never happen after the fix in
            # _get_known_embeddings, but guards against any future regression.
            logger.error("_recognize: idx %d out of range for known_names (len %d) — "
                         "marking face Unknown. Invalidating cache.", idx, n_known)
            invalidate_embedding_cache()
            out.append(('Unknown', 0.0))
            continue
        dist = float(dists[idx])
        if dist < threshold:
            conf = max(0.0, 1.0 - dist / threshold)
            out.append((known_names[idx], conf))
        else:
            out.append(('Unknown', 0.0))
    return out


# ── Attendance cooldown ───────────────────────────────────────────────────────
# Per-person 10-second debounce: prevents the same face/QR from re-triggering
# a DB write within the same brief exposure window.
# The 10-minute checkout delay in utils.py is the second line of defence.

_attendance_cooldown: dict[str, float] = {}
_cooldown_display:    dict[str, float] = {}   # last "ya fue registrado" shown per person
_cooldown_lock = threading.Lock()
_COOLDOWN_SECONDS = 10
_DISPLAY_THROTTLE = 5.0   # "ya fue registrado" shown at most once per 5 s per person


def _can_mark(name: str) -> bool:
    with _cooldown_lock:
        return (time.monotonic() - _attendance_cooldown.get(name, 0)) > _COOLDOWN_SECONDS


def _set_cooldown(name: str):
    with _cooldown_lock:
        _attendance_cooldown[name] = time.monotonic()


# ── QR decoder (OpenCV built-in, zero extra deps) ────────────────────────────
# Pipeline: detect → validate geometry → decode.
# Two-pass preprocessing (CLAHE first, unsharp-mask retry) improves detection
# of dark, blurry or low-contrast QR codes without adding extra dependencies.

_qr_detector   = cv2.QRCodeDetector()
_clahe         = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
_QR_PROC_WIDTH = 640   # downscale target for QR detection; sufficient at kiosk distances


def _decode_qr(frame_bgr) -> str | None:
    """Return decoded QR string or None.  Never raises."""
    try:
        h, w = frame_bgr.shape[:2]
        # Downscale once; smaller frame → faster detection, negligible quality loss
        if w > _QR_PROC_WIDTH:
            scale = _QR_PROC_WIDTH / w
            small = cv2.resize(frame_bgr, (_QR_PROC_WIDTH, int(h * scale)))
        else:
            small = frame_bgr

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        # Pass 1 — raw gray (fastest; works for well-lit codes)
        data, _, _ = _qr_detector.detectAndDecode(gray)
        if data and isinstance(data, str):
            return data

        # Pass 2 — CLAHE (better for dark/uneven lighting)
        enhanced = _clahe.apply(gray)
        data, _, _ = _qr_detector.detectAndDecode(enhanced)
        return data if (data and isinstance(data, str)) else None

    except cv2.error:
        return None
    except Exception:
        return None


# ── CameraManager ─────────────────────────────────────────────────────────────

class CameraManager:
    # Frames needed to confirm a face (higher = more stable, less jitter)
    FACE_CONFIRM_FRAMES = 3
    # High-confidence shortcut: confirm after this many frames when conf >= threshold
    FACE_CONFIRM_FAST   = 2
    FACE_FAST_THRESHOLD = 0.80
    # Run face recognition every N frames (2 = ~15 fps on a 30 fps source)
    FACE_PROCESS_EVERY  = 2
    # Run QR decode every N frames (1 = every frame; QR decode is cheap after resize)
    QR_PROCESS_EVERY    = 1
    # Width of the downscaled image fed to MTCNN (higher = better quality)
    INFER_WIDTH         = 480

    def __init__(self):
        self._lock        = threading.Lock()
        self._threads:     list[threading.Thread] = []
        self._stop_events: list[threading.Event]  = []
        self._frame_q:     queue.Queue            = queue.Queue(maxsize=2)
        self._running      = False
        self._error:       str | None             = None
        self._log_lock     = threading.Lock()
        self._log:         list[dict]             = []

    # ── Public control ──────────────────────────────────────────────────

    def start(self):
        with self._lock:
            if self._running:
                return
            cam_configs = list(CameraConfiguration.objects.all())
            if not cam_configs:
                self._error = "No camera configurations found. Add one in the admin panel."
                return
            self._error   = None
            self._running = True
            self._threads.clear()
            self._stop_events.clear()
            for cfg in cam_configs:
                ev = threading.Event()
                self._stop_events.append(ev)
                t  = threading.Thread(target=self._worker, args=(cfg, ev), daemon=True)
                self._threads.append(t)
                t.start()

    def stop(self):
        with self._lock:
            for ev in self._stop_events:
                ev.set()
            self._running = False
            self._drain_queue()

    def is_running(self) -> bool:
        with self._lock:
            return self._running and any(t.is_alive() for t in self._threads)

    def get_error(self) -> str | None:
        return self._error

    def pop_log(self) -> list[dict]:
        with self._log_lock:
            logs, self._log = list(self._log), []
            return logs

    def _push_log(self, event_type: str, message: str, source: str):
        entry = {'type': event_type, 'msg': message, 'source': source}
        with self._log_lock:
            self._log.append(entry)

    def _drain_queue(self):
        while not self._frame_q.empty():
            try:
                self._frame_q.get_nowait()
            except queue.Empty:
                break

    # ── Worker thread ───────────────────────────────────────────────────

    def _worker(self, cam_config, stop_event: threading.Event):
        cap = None
        try:
            src = cam_config.camera_source
            cap = cv2.VideoCapture(int(src) if src.isdigit() else src)
            if not cap.isOpened():
                self._error = f"Cannot open camera: {cam_config.name}"
                return

            # Sound (optional)
            try:
                import pygame
                pygame.mixer.init()
                sound = pygame.mixer.Sound('app1/suc.wav')
            except Exception:
                sound = None

            threshold   = cam_config.threshold
            frame_idx   = 0

            # ── Overlay state (drawn every frame, recomputed every N frames) ──
            cached_boxes   = []    # scaled to full resolution
            cached_results = []    # [(name, conf), ...]

            # ── Temporal face-stability buffer ─────────────────────────────
            # Maps name → consecutive-frame count; reset on miss
            face_stability: dict[str, int] = defaultdict(int)
            # Track which names are in the current detection set
            last_detected: set[str] = set()

            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.04)
                    continue

                frame_idx += 1
                h, w = frame.shape[:2]

                # ── QR check (every QR_PROCESS_EVERY frames) ────────────────
                if frame_idx % self.QR_PROCESS_EVERY == 0:
                    qr_data = _decode_qr(frame)
                    if qr_data:
                        self._handle_qr(qr_data, frame, sound)

                # ── Face recognition (every FACE_PROCESS_EVERY frames) ───────
                if frame_idx % self.FACE_PROCESS_EVERY == 0:
                    try:
                        scale = self.INFER_WIDTH / w
                        small = cv2.resize(frame, (self.INFER_WIDTH, int(h * scale)))
                        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                        test_encs = _detect_and_encode(rgb)

                        # Always detect boxes first so the rectangle shows
                        # for ANY face (recognised or Unknown).
                        mtcnn_m, _, _ = _get_models()
                        boxes_small, _ = mtcnn_m.detect(rgb)

                        if boxes_small is not None:
                            # ── Run recognition only when we have face boxes ──
                            if test_encs:
                                known_enc, known_names = _get_known_embeddings()
                                results = _recognize(known_enc, known_names, test_encs, threshold)
                            else:
                                # Faces detected but encoding failed (rare) — mark all Unknown
                                results = [('Unknown', 0.0)] * len(boxes_small)

                            cached_boxes   = (boxes_small / scale).astype(int)
                            cached_results = results
                            current_names  = {n for n, _ in results if n != 'Unknown'}

                            # ── Temporal stability update ─────────────────
                            for name in current_names:
                                face_stability[name] += 1
                            for name in (last_detected - current_names):
                                face_stability[name] = max(0, face_stability[name] - 1)
                            last_detected = current_names

                            # ── Trigger attendance for stable faces ───────
                            for name, conf in results:
                                if name == 'Unknown':
                                    continue
                                stable = face_stability[name]
                                fast_ok = (conf >= self.FACE_FAST_THRESHOLD
                                           and stable >= self.FACE_CONFIRM_FAST)
                                if fast_ok or stable >= self.FACE_CONFIRM_FRAMES:
                                    self._handle_face(name, conf, sound)
                        else:
                            # No faces in this cycle — decay and clear overlay
                            for name in last_detected:
                                face_stability[name] = max(0, face_stability[name] - 1)
                            last_detected = set()
                            cached_boxes   = []
                            cached_results = []

                    except Exception as _face_exc:
                        # An error in one recognition cycle must never kill the
                        # camera worker. Clear cached overlay and keep streaming.
                        logger.exception("Face recognition error on frame %d: %s",
                                         frame_idx, _face_exc)
                        cached_boxes   = []
                        cached_results = []

                # ── Mirror for natural "selfie/webcam" display ───────────────
                # Recognition (QR + face) already ran on the original frame.
                # Only the display copy is flipped; bounding-box x coords are
                # remapped so they stay over the correct (mirrored) face region.
                display = cv2.flip(frame, 1)   # 1 = horizontal flip

                for box, (name, conf) in zip(cached_boxes, cached_results):
                    x1, y1, x2, y2 = box
                    # Mirror x: original x1 → (w - x2), original x2 → (w - x1)
                    mx1 = w - x2
                    mx2 = w - x1
                    color  = (0, 255, 120) if name != 'Unknown' else (0, 80, 255)
                    stable = face_stability.get(name, 0)
                    label  = (f"{name} {int(conf*100)}% ({'✓' if (stable >= self.FACE_CONFIRM_FRAMES or (conf >= self.FACE_FAST_THRESHOLD and stable >= self.FACE_CONFIRM_FAST)) else str(stable)+'f'})"
                              if name != 'Unknown' else "Unknown")
                    cv2.rectangle(display, (mx1, y1), (mx2, y2), color, 2)
                    cv2.rectangle(display, (mx1, y2 - 22), (mx2, y2), color, cv2.FILLED)
                    cv2.putText(display, label, (mx1 + 4, y2 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 0, 0), 1, cv2.LINE_AA)

                # ── Push MJPEG frame ─────────────────────────────────────────
                _, jpg = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 75])
                try:
                    self._frame_q.put_nowait(jpg.tobytes())
                except queue.Full:
                    pass

        except Exception as exc:
            logger.exception("Camera worker error: %s", exc)
            self._error = str(exc)
        finally:
            if cap is not None:
                cap.release()

    # ── Attendance helpers ──────────────────────────────────────────────

    def _handle_qr(self, qr_data: str, frame, sound):
        """Process a decoded QR payload."""
        import uuid as _uuid
        if not isinstance(qr_data, str) or not qr_data.strip():
            return
        try:
            uid = _uuid.UUID(qr_data.strip())
        except (ValueError, AttributeError):
            logger.debug("Invalid QR payload (not UUID): %s", repr(qr_data)[:60])
            return

        try:
            student = Student.objects.get(unique_id=uid, authorized=True, qr_active=True)
        except Student.DoesNotExist:
            self._push_log('qr_invalid', "QR not recognized or not authorized", 'qr')
            return

        name = student.name
        should_show_already = False
        proceed = False

        with _cooldown_lock:
            now = time.monotonic()
            if (now - _attendance_cooldown.get(name, 0)) <= _COOLDOWN_SECONDS:
                # Still in debounce window — show "ya registrado" feedback (throttled per person)
                if (now - _cooldown_display.get(name, 0)) > _DISPLAY_THROTTLE:
                    _cooldown_display[name] = now
                    should_show_already = True
            else:
                _attendance_cooldown[name] = now
                proceed = True

        if should_show_already:
            self._push_log('already_done', f"{name} — ya fue registrado", 'qr')
            return
        if not proceed:
            return

        event_type, msg = record_attendance(student)
        if event_type in ('checked_in', 'checked_out'):
            if sound:
                sound.play()
        self._push_log(event_type, msg, 'qr')
        logger.info("[QR] %s", msg)

    def _handle_face(self, name: str, conf: float, sound):
        """Process a stable face recognition hit."""
        should_show_already = False
        proceed = False

        with _cooldown_lock:
            now = time.monotonic()
            if (now - _attendance_cooldown.get(name, 0)) <= _COOLDOWN_SECONDS:
                # Still in debounce window — show "ya registrado" feedback (throttled per person)
                if (now - _cooldown_display.get(name, 0)) > _DISPLAY_THROTTLE:
                    _cooldown_display[name] = now
                    should_show_already = True
            else:
                _attendance_cooldown[name] = now
                proceed = True

        if should_show_already:
            self._push_log('already_done', f"{name} — ya fue registrado", 'face')
            return
        if not proceed:
            return

        try:
            student = Student.objects.get(name=name, authorized=True)
        except Student.DoesNotExist:
            return

        event_type, msg = record_attendance(student)
        if event_type in ('checked_in', 'checked_out'):
            if sound:
                sound.play()
        self._push_log(event_type, f"{msg} (face {int(conf*100)}%)", 'face')
        logger.info("[Face] %s (conf=%.2f)", msg, conf)

    # ── MJPEG generator ─────────────────────────────────────────────────

    def generate_mjpeg(self):
        boundary = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
        while self._running:
            try:
                jpg = self._frame_q.get(timeout=1.0)
                yield boundary + jpg + b'\r\n'
            except queue.Empty:
                continue


_camera_manager = CameraManager()


# ── Permission helpers ────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_superuser


def is_staff_or_admin(user):
    return user.is_authenticated


# ── Camera API views (public — kiosk is accessible without login) ─────────────

def camera_start(request):
    _camera_manager.start()
    err = _camera_manager.get_error()
    if err:
        return JsonResponse({'status': 'error', 'message': err})
    return JsonResponse({'status': 'started'})


def camera_stop(request):
    _camera_manager.stop()
    return JsonResponse({'status': 'stopped'})


def camera_status(request):
    logs = _camera_manager.pop_log()
    return JsonResponse({
        'running': _camera_manager.is_running(),
        'error':   _camera_manager.get_error(),
        'logs':    logs,
    })


def camera_stream(request):
    if not _camera_manager.is_running():
        _camera_manager.start()
    return StreamingHttpResponse(
        _camera_manager.generate_mjpeg(),
        content_type='multipart/x-mixed-replace; boundary=frame',
    )


# ── Admin: full attendance control view ───────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def capture_and_recognize(request):
    return render(request, 'capture_and_recognize.html', {
        'cam_configs': CameraConfiguration.objects.all(),
        'is_running':  _camera_manager.is_running(),
    })


# ── Personal: kiosk (public — no login required) ─────────────────────────────

def attendance_kiosk(request):
    """Public kiosk view. Authenticated admins are sent to the full panel."""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('capture_and_recognize')
    return render(request, 'attendance_kiosk.html', {
        'is_running': _camera_manager.is_running(),
    })


# ── Student registration (admin only) ────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def capture_student(request):
    if request.method == 'POST':
        name          = request.POST.get('name', '').strip()
        email         = request.POST.get('email', '').strip()
        phone_number  = request.POST.get('phone_number', '').strip()
        student_class = request.POST.get('student_class', '').strip()
        position      = request.POST.get('position', '').strip()
        area          = request.POST.get('area', '').strip()
        work_schedule = request.POST.get('work_schedule', '').strip()
        dni           = request.POST.get('dni', '').strip()
        image_data    = request.POST.get('image_data')

        # ── Resolve photo: prefer file upload, fall back to webcam capture ──
        image_file = None
        photo_file = request.FILES.get('photo_upload')
        if photo_file:
            # Validate size (5 MB max)
            if photo_file.size > 5 * 1024 * 1024:
                messages.error(request, "La foto no puede superar 5 MB.")
                return render(request, 'capture_student.html',
                              {'cam_running': _camera_manager.is_running()})
            ext        = os.path.splitext(photo_file.name)[1].lower()
            safe_name  = f"{name}{ext}" if ext in ('.jpg', '.jpeg', '.png') else f"{name}.jpg"
            image_file = ContentFile(photo_file.read(), name=safe_name)
        elif image_data:
            header, encoded = image_data.split(',', 1)
            image_file = ContentFile(base64.b64decode(encoded), name=f"{name}.jpg")

        if not name:
            messages.error(request, "El nombre es obligatorio.")
            return render(request, 'capture_student.html',
                          {'cam_running': _camera_manager.is_running()})

        if image_file:
            student = Student.objects.create(
                name=name, email=email,
                phone_number=phone_number, student_class=student_class,
                position=position, area=area, work_schedule=work_schedule,
                dni=dni,
                image=image_file,
                authorized=True,
                qr_active=True,
            )
            # Generate QR + fotocheck assets in background thread so the admin
            # is not blocked waiting for image processing.
            import threading as _threading
            def _gen_assets(pk):
                try:
                    s = Student.objects.get(pk=pk)
                    generate_all_fotocheck_assets(s)
                    invalidate_embedding_cache()
                except Exception:
                    logger.exception("Asset generation failed for student pk=%s", pk)
            _threading.Thread(target=_gen_assets, args=(student.pk,), daemon=True).start()
            return redirect('selfie_success')
        else:
            messages.error(request, "Debes subir una foto o capturarla con la webcam.")

    return render(request, 'capture_student.html', {
        'cam_running': _camera_manager.is_running(),
    })


def selfie_success(request):
    return render(request, 'selfie_success.html')


# ── Attendance list ───────────────────────────────────────────────────────────

def _attendance_queryset(request):
    """Shared filter logic for the attendance list and export views."""
    search   = request.GET.get('search', '').strip()
    area     = request.GET.get('area', '').strip()
    date_val = request.GET.get('attendance_date', '').strip()
    date_from= request.GET.get('date_from', '').strip()
    date_to  = request.GET.get('date_to', '').strip()

    students = Student.objects.all()
    if search:
        students = students.filter(name__icontains=search)
    if area:
        students = students.filter(area__icontains=area)

    rows = []
    for student in students:
        records = Attendance.objects.filter(student=student)
        if date_val:
            records = records.filter(date=date_val)
        elif date_from:
            records = records.filter(date__gte=date_from)
            if date_to:
                records = records.filter(date__lte=date_to)
        for r in records.order_by('-date', '-check_in_time'):
            rows.append((student, r))
    return rows


@login_required
@user_passes_test(is_admin)
def student_attendance_list(request):
    search   = request.GET.get('search', '')
    area     = request.GET.get('area', '')
    date_val = request.GET.get('attendance_date', '')
    date_from= request.GET.get('date_from', '')
    date_to  = request.GET.get('date_to', '')

    rows = _attendance_queryset(request)

    # Group by student for the nested template structure
    from collections import OrderedDict
    grouped = OrderedDict()
    for student, record in rows:
        if student.pk not in grouped:
            grouped[student.pk] = {'student': student, 'attendance_records': []}
        grouped[student.pk]['attendance_records'].append(record)

    import datetime as _dt
    _today = _dt.date.today()
    month_choices = [
        (1,"Enero"),(2,"Febrero"),(3,"Marzo"),(4,"Abril"),
        (5,"Mayo"),(6,"Junio"),(7,"Julio"),(8,"Agosto"),
        (9,"Setiembre"),(10,"Octubre"),(11,"Noviembre"),(12,"Diciembre"),
    ]
    try:
        _cur_month = int(request.GET.get('month', _today.month))
        _cur_year  = int(request.GET.get('year',  _today.year))
    except (ValueError, TypeError):
        _cur_month, _cur_year = _today.month, _today.year

    return render(request, 'student_attendance_list.html', {
        'student_attendance_data': list(grouped.values()),
        'flat_rows':     rows,
        'search_query':  search,
        'area_filter':   area,
        'date_filter':   date_val,
        'date_from':     date_from,
        'date_to':       date_to,
        'month_choices': month_choices,
        'year_choices':  list(range(_today.year - 3, _today.year + 2)),
        'current_month': _cur_month,
        'current_year':  _cur_year,
    })


@login_required
@user_passes_test(is_admin)
def export_attendance_csv(request):
    rows = _attendance_queryset(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="asistencia.csv"'
    response.write('﻿')  # BOM so Excel opens it correctly as UTF-8
    writer = csv.writer(response)
    writer.writerow(['Nombre', 'Cargo', 'Área', 'Horario', 'Fecha', 'Entrada', 'Salida', 'Duración', 'Estado'])
    for student, record in rows:
        estado = 'Completo' if (record.check_in_time and record.check_out_time) else 'Solo entrada'
        writer.writerow([
            student.name,
            student.position,
            student.area,
            student.work_schedule,
            str(record.date),
            record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else '',
            record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else '',
            record.calculate_duration() or '',
            estado,
        ])
    return response


@login_required
@user_passes_test(is_admin)
def export_attendance_excel(request):
    """
    Export attendance as the official IESTP Paucartambo report format.
    Accepts ?month=8&year=2025 (defaults to current month/year).
    Also accepts the existing date filters for backward compatibility.
    """
    import calendar as cal_mod
    import datetime
    from app1.report_excel import build_report

    # ── resolve month/year ────────────────────────────────────────────────────
    today = datetime.date.today()
    try:
        month = int(request.GET.get('month', today.month))
        year  = int(request.GET.get('year',  today.year))
        if not (1 <= month <= 12 and 1900 <= year <= 2100):
            raise ValueError
    except (ValueError, TypeError):
        month, year = today.month, today.year

    days_in_month = cal_mod.monthrange(year, month)[1]

    # ── fetch all students ────────────────────────────────────────────────────
    from app1.models import Student, Attendance
    search = request.GET.get('search', '').strip()
    area   = request.GET.get('area',   '').strip()

    students_qs = Student.objects.all().order_by('name')
    if search:
        students_qs = students_qs.filter(name__icontains=search)
    if area:
        students_qs = students_qs.filter(area__icontains=area)

    # ── build per-student attendance sets ─────────────────────────────────────
    students_data = []
    for idx, student in enumerate(students_qs, 1):
        records = Attendance.objects.filter(
            student=student,
            date__year=year,
            date__month=month,
        )
        attended_days = set(r.date.day for r in records if r.check_in_time)
        students_data.append({
            'number':    idx,
            'dni':       student.dni or '',
            'name':      student.name,
            'position':  student.position or '',
            'condition': 'Contratado',   # default; extend model if needed
            'attendance': attended_days,
        })

    # ── generate Excel ────────────────────────────────────────────────────────
    xlsx_bytes = build_report(students_data, month=month, year=year)

    month_name_es = {
        1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",
        5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",
        9:"Setiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
    }[month]
    filename = f"Reporte_Asistencia_{month_name_es}_{year}.xlsx"

    response = HttpResponse(
        xlsx_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def home(request):
    if not request.user.is_authenticated:
        return redirect('attendance_kiosk')
    if not request.user.is_superuser:
        return redirect('attendance_kiosk')

    today = timezone.localdate()
    total_students     = Student.objects.count()
    authorized_count   = Student.objects.filter(authorized=True).count()
    pending_count      = Student.objects.filter(authorized=False).count()
    today_checkins     = Attendance.objects.filter(date=today, check_in_time__isnull=False).count()
    today_checkouts    = Attendance.objects.filter(date=today, check_out_time__isnull=False).count()
    recent_attendance  = (Attendance.objects
                          .select_related('student')
                          .filter(date=today)
                          .order_by('-check_in_time')[:10])

    return render(request, 'home.html', {
        'total_students':    total_students,
        'authorized_count':  authorized_count,
        'pending_count':     pending_count,
        'today_checkins':    today_checkins,
        'today_checkouts':   today_checkouts,
        'recent_attendance': recent_attendance,
        'today':             today,
    })


# ── Admin-only student management ─────────────────────────────────────────────


@login_required
@user_passes_test(is_admin)
def student_list(request):
    return render(request, 'student_list.html', {'students': Student.objects.all()})


@login_required
@user_passes_test(is_admin)
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'student_detail.html', {'student': student})


@login_required
@user_passes_test(is_admin)
def student_authorize(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.authorized = bool(request.POST.get('authorized', False))
        student.qr_active  = bool(request.POST.get('qr_active', False))
        student.save()
        invalidate_embedding_cache()
        # Auto-generate QR+fotocheck if not present and student just got authorized
        if student.authorized and not student.qr_code:
            generate_qr_with_logo(student)
        if student.authorized and not student.fotocheck_png:
            import threading as _threading
            _threading.Thread(target=generate_all_fotocheck_assets,
                              args=(student,), daemon=True).start()
        return redirect('student-detail', pk=pk)
    return render(request, 'student_authorize.html', {'student': student})


@login_required
@user_passes_test(is_admin)
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        invalidate_embedding_cache()
        messages.success(request, 'Student deleted successfully.')
        return redirect('student-list')
    return render(request, 'student_delete_confirm.html', {'student': student})


@login_required
@user_passes_test(is_admin)
def student_regenerate_qr(request, pk):
    """Force-regenerate the QR code for a student."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        ok = generate_qr_for_student(student)
        if ok:
            messages.success(request, f"QR regenerated for {student.name}.")
        else:
            messages.error(request, "QR generation failed.")
    return redirect('student-detail', pk=pk)


@login_required
@user_passes_test(is_admin)
def student_qr_download(request, pk):
    """Serve the QR image as a downloadable file."""
    student = get_object_or_404(Student, pk=pk)
    if not student.qr_code:
        raise Http404("No QR code for this student.")
    path = student.qr_code.path
    if not os.path.exists(path):
        raise Http404("QR image file not found on disk.")
    return FileResponse(open(path, 'rb'), content_type='image/png',
                        as_attachment=True,
                        filename=f"qr_{student.name}.png")


# ── Auth ──────────────────────────────────────────────────────────────────────

def user_login(request):
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


# ── Camera configuration CRUD ─────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def camera_config_create(request):
    if request.method == "POST":
        try:
            CameraConfiguration.objects.create(
                name=request.POST.get('name'),
                camera_source=request.POST.get('camera_source'),
                threshold=request.POST.get('threshold'),
            )
            return redirect('camera_config_list')
        except IntegrityError:
            messages.error(request, "A configuration with this name already exists.")
    return render(request, 'camera_config_form.html')


@login_required
@user_passes_test(is_admin)
def camera_config_list(request):
    return render(request, 'camera_config_list.html',
                  {'configs': CameraConfiguration.objects.all()})


@login_required
@user_passes_test(is_admin)
def camera_config_update(request, pk):
    config = get_object_or_404(CameraConfiguration, pk=pk)
    if request.method == "POST":
        config.name          = request.POST.get('name')
        config.camera_source = request.POST.get('camera_source')
        config.threshold     = request.POST.get('threshold')
        config.save()
        return redirect('camera_config_list')
    return render(request, 'camera_config_form.html', {'config': config})


@login_required
@user_passes_test(is_admin)
def camera_config_delete(request, pk):
    config = get_object_or_404(CameraConfiguration, pk=pk)
    if request.method == "POST":
        config.delete()
        return redirect('camera_config_list')
    return render(request, 'camera_config_delete.html', {'config': config})


# ── Import personnel (CSV / XLSX) ─────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def import_students(request):
    if request.method != 'POST':
        return render(request, 'import_students.html')

    uploaded = request.FILES.get('file')
    if not uploaded:
        messages.error(request, 'No file selected.')
        return redirect('import_students')

    ext = uploaded.name.rsplit('.', 1)[-1].lower()
    raw_rows = []

    if ext == 'csv':
        content = uploaded.read().decode('utf-8-sig')
        reader  = csv.DictReader(io.StringIO(content))
        raw_rows = [{k.strip().lower(): (v or '').strip() for k, v in row.items()} for row in reader]
    elif ext in ('xlsx', 'xls'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(uploaded, read_only=True)
            ws = wb.active
            headers = [str(c.value or '').strip().lower() for c in next(ws.iter_rows(max_row=1))]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if any(v for v in row):
                    raw_rows.append({headers[i]: str(v or '').strip() for i, v in enumerate(row)})
        except Exception as exc:
            messages.error(request, f'Could not read Excel file: {exc}')
            return redirect('import_students')
    else:
        messages.error(request, 'Unsupported format. Upload CSV or XLSX.')
        return redirect('import_students')

    imported = 0
    skipped  = []
    for i, row in enumerate(raw_rows, start=2):
        name = row.get('name', row.get('nombre', '')).strip()
        if not name:
            skipped.append(f'Row {i}: missing name — skipped.')
            continue
        email = row.get('email', row.get('correo', '')).strip()
        if email and Student.objects.filter(email=email).exists():
            skipped.append(f'Row {i}: {name} — email already registered, skipped.')
            continue
        student = Student.objects.create(
            name          = name,
            email         = email,
            phone_number  = row.get('phone_number', row.get('telefono', row.get('phone', ''))).strip(),
            student_class = row.get('student_class', row.get('clase', row.get('class', ''))).strip(),
            position      = row.get('position', row.get('cargo', '')).strip(),
            area          = row.get('area', row.get('área', '')).strip(),
            work_schedule = row.get('work_schedule', row.get('horario', '')).strip(),
            authorized    = True,
            qr_active     = True,
        )
        generate_qr_for_student(student)
        imported += 1

    invalidate_embedding_cache()
    messages.success(request, f'{imported} person(s) imported successfully.')
    for msg in skipped:
        messages.warning(request, msg)
    return redirect('import_students')


# ── Printable credential card + fotocheck ─────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def student_credential(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'student_credential.html', {'student': student})


@login_required
@user_passes_test(is_admin)
def student_fotocheck_download_png(request, pk):
    """Serve the fotocheck PNG as a download."""
    student = get_object_or_404(Student, pk=pk)
    if not student.fotocheck_png:
        messages.error(request, "Fotocheck PNG no generado. Regénéralo primero.")
        return redirect('student-credential', pk=pk)
    path = student.fotocheck_png.path
    if not os.path.exists(path):
        messages.error(request, "Archivo fotocheck no encontrado en disco.")
        return redirect('student-credential', pk=pk)
    return FileResponse(open(path, 'rb'), content_type='image/png',
                        as_attachment=True,
                        filename=f"fotocheck_{student.name}.png")


@login_required
@user_passes_test(is_admin)
def student_fotocheck_download_pdf(request, pk):
    """Serve the fotocheck PDF as a download."""
    student = get_object_or_404(Student, pk=pk)
    if not student.fotocheck_pdf:
        messages.error(request, "Fotocheck PDF no generado. Regénéralo primero.")
        return redirect('student-credential', pk=pk)
    path = student.fotocheck_pdf.path
    if not os.path.exists(path):
        messages.error(request, "Archivo fotocheck PDF no encontrado en disco.")
        return redirect('student-credential', pk=pk)
    return FileResponse(open(path, 'rb'), content_type='application/pdf',
                        as_attachment=True,
                        filename=f"fotocheck_{student.name}.pdf")


@login_required
@user_passes_test(is_admin)
def student_regenerate_fotocheck(request, pk):
    """Force-regenerate QR + fotocheck PNG + PDF for a single student."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        results = generate_all_fotocheck_assets(student)
        ok_list = [k for k, v in results.items() if v]
        fail_list = [k for k, v in results.items() if not v]
        if ok_list:
            messages.success(request, f"Fotocheck regenerado: {', '.join(ok_list)} ✓")
        if fail_list:
            messages.warning(request, f"Falló: {', '.join(fail_list)}")
    return redirect('student-credential', pk=pk)


@login_required
@user_passes_test(is_admin)
def credentials_list(request):
    """Panel: list all personnel with fotocheck status + bulk generation."""
    students = Student.objects.all().order_by('name')
    total_students = students.count()
    generated_count = students.exclude(fotocheck_png='').count()
    pending_count = total_students - generated_count
    return render(request, 'credentials_list.html', {
        'students': students,
        'total_students': total_students,
        'generated_count': generated_count,
        'pending_count': pending_count,
    })


@login_required
@user_passes_test(is_admin)
def credentials_bulk_generate(request):
    """Bulk-generate fotochecks for all students (runs synchronously, streams progress via messages)."""
    if request.method != 'POST':
        return redirect('credentials-list')

    students = Student.objects.all()
    total    = students.count()
    ok       = 0
    failed   = []

    for s in students:
        results = generate_all_fotocheck_assets(s)
        if all(results.values()):
            ok += 1
        else:
            failed.append(s.name)

    messages.success(request, f"Generación masiva completada: {ok}/{total} correctos.")
    for name in failed:
        messages.warning(request, f"Fallo parcial en: {name}")
    return redirect('credentials-list')


# ── System configuration ──────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def system_config_view(request):
    config = SystemConfig.get()
    if request.method == 'POST':
        config.face_recognition_enabled = 'face_recognition_enabled' in request.POST
        config.qr_enabled               = 'qr_enabled'               in request.POST
        try:
            config.checkout_delay_minutes   = max(1, int(request.POST.get('checkout_delay_minutes', 10)))
            config.display_throttle_seconds = max(1, int(request.POST.get('display_throttle_seconds', 5)))
            config.recognition_threshold    = max(0.1, min(1.0, float(request.POST.get('recognition_threshold', 0.6))))
        except (ValueError, TypeError):
            messages.error(request, 'Invalid numeric value.')
            return redirect('system_config')
        config.save()
        messages.success(request, 'Configuration saved.')
        return redirect('system_config')
    return render(request, 'system_config.html', {'config': config})