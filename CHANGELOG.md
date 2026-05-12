# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.4.0] — 2026-05-09

### Fixed
- **Critical IndexError in face recognition worker** (`app1/views.py`): `_get_known_embeddings` was calling `known_enc.extend(encs)` (N embeddings per student) but `known_names.append(name)` (1 name per student), causing `known_enc` and `known_names` to have different lengths. `_recognize` would then call `known_names[argmin_idx]` with an out-of-range index and crash the camera worker. Fix: use exactly 1 embedding per student (first detected face), warn on 0 or >1 faces, and add a length sanity check before caching.
- **`_recognize` hardened**: bounds-check `idx` against `len(known_names)` before access; on mismatch, invalidate cache and return `Unknown` instead of raising `IndexError`.
- **Face recognition block isolated in worker**: the per-frame face recognition loop is now wrapped in its own `try/except` so a bad frame or transient ML error clears the cached overlay and continues streaming without killing the camera thread.

### Added
- **Registration form fields**: `capture_student` view and form now include `position`, `area`, and `work_schedule` fields — previously these model fields existed but were never shown or saved during manual registration, causing them to appear empty in reports and credential cards.
- **Mirror on registration camera**: `#video` and `#snapshot-preview` in `capture_student.html` now have `transform: scaleX(-1)` for a natural selfie experience. The canvas `drawImage` call is unaffected by CSS transforms, so the saved photo and face recognition both use the unflipped frame.

### Improved
- Logging: `_get_known_embeddings` now emits `WARNING` for students with no image, unreadable image files, encoding failures, 0 faces detected, or >1 face detected; `DEBUG` log on each successful cache rebuild.

---

## [2.3.0] — 2026-05-09

### Added
- **Bulk personnel import** (`/import/`): drag-and-drop CSV or Excel upload; Spanish/English column name aliases (`cargo`/`position`, `área`/`area`, `horario`/`work_schedule`, `clase`/`student_class`); all rows auto-authorized with generated QR code; duplicate email and missing name rows skipped with per-row warnings displayed inline.
- **Attendance report export**: CSV export (`/students/attendance/export/csv/`) and Excel export (`/students/attendance/export/excel/`) respect active filters (name search, area filter, date range). Excel generated with openpyxl; CSV uses Python stdlib.
- **Printable credential card** (`/students/<pk>/credential/`): glassmorphism ID card displaying photo, name, position, area, work schedule, QR code, and UUID. Print CSS hides sidebar and controls.
- **System Configuration page** (`/config/`): iOS-style toggles for face recognition and QR attendance; numeric inputs for checkout delay, display throttle, and default recognition threshold; stored in `SystemConfig` singleton model.
- **`SystemConfig` model**: singleton (always `pk=1`), read via `SystemConfig.get()` classmethod. Fields: `face_recognition_enabled`, `qr_enabled`, `checkout_delay_minutes`, `display_throttle_seconds`, `recognition_threshold`.
- **Student model fields**: `position`, `area`, `work_schedule` (all `CharField`, `blank=True`) added to `Student` model with migration `0012`.
- **Redesigned dashboard** (`/`): stat cards (total students, authorized, today's check-ins, check-outs, active cameras), today's activity table, quick-action panel.
- **Attendance report filters**: area/department filter and date range filter added to `/students/attendance/`.
- **Attendance table columns**: added position, area, work schedule, and class/group columns.

### Changed
- Sidebar navigation updated with: Import List, Cameras, Configuration items and `{% block nav_import %}` / `{% block nav_config %}` extension blocks.

---

## [2.2.0] — 2026-05-09

### Fixed
- **Per-person cooldown feedback**: after marking a person, the system was showing no feedback to other persons in frame during the global cooldown window. Split into `_attendance_cooldown` (prevents DB writes per person) and `_cooldown_display` (throttles "ya fue registrado" UI feedback per person). Other persons are never blocked.
- **Frontend `already_done` blocking all persons**: kiosk JS was using a single global timestamp for the `already_done` throttle. Changed to a per-person dict `_alreadyDoneByName` keyed by parsed name.

### Changed
- **Mirror display**: MJPEG output is now `cv2.flip(frame, 1)` (horizontal mirror). Bounding-box x coordinates remapped: left edge = `w - x2`, right edge = `w - x1`. Text labels remain readable. Recognition (face + QR) still uses the original unflipped frame.
- **Faster QR detection**: frames pre-resized to 640 px before QR processing; raw grayscale tried first; `detectAndDecode` used instead of separate `detect` + `decode` calls; sharpening pass removed; `QR_PROCESS_EVERY` reduced from 2 to 1.

---

## [2.1.0] — 2025-05-09

### Added
- Full dark glassmorphism UI (kiosk + admin panel)
- MJPEG streaming via `/camera/stream/` (single `<img>` tag, no WebSocket)
- Hybrid QR + face attendance in one camera loop
- RBAC: public kiosk vs admin-only management views
- `CameraConfiguration` model: manage cameras from the admin panel
- Temporal face-stability buffer (3-frame confirmation before marking)
- High-confidence fast path (2 frames at ≥ 80% confidence)
- Embedding cache with 30-second TTL + instant invalidation on student changes
- Two-pass QR preprocessing: CLAHE + raw grayscale
- Per-person 10-second debounce to prevent duplicate attendance records
- Web Audio API chimes (check-in, check-out, already-marked tones)
- QR download and regeneration endpoints
- `_FACE_MARGIN = 20 px` crop expansion for more stable embeddings

### Changed
- Replaced `cv2.imshow` (headless-incompatible) with MJPEG stream
- Moved all ML inference to background worker threads
- Upgraded from Django 5.x to Django 6.0.5
- Upgraded from numpy 1.x to numpy 2.x (required for Python 3.14 wheels)

---

## [1.0.0] — 2025-05-07

### Added
- Initial Django project with `Student`, `Attendance` models
- Basic face recognition with MTCNN + InceptionResnetV1
- Admin registration flow with webcam photo capture (base64 POST)
- Attendance list view
- SQLite database
- MIT License
