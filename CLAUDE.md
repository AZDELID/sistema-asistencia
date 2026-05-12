# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- **Python:** 3.14 on Arch Linux (the venv uses `python3.14`)
- **Django:** 6.0.5 — project package is `Project101`, sole app is `app1`
- **Database:** SQLite (`db.sqlite3`)
- **Timezone:** `Asia/Riyadh` (set in `settings.py`)

## Common Commands

```bash
# Activate the virtual environment first
source venv/bin/activate

# Run the development server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Create new migrations after model changes
python manage.py makemigrations

# Create a superuser (required to access /admin and admin-only views)
python manage.py createsuperuser

# Django system check
python manage.py check

# Run tests
python manage.py test app1
```

## Python 3.14 Dependency Setup

Do **not** run `pip install -r requirements.txt` on Python 3.14 — that file targets Python 3.x with older pinned versions. Use the dedicated script instead:

```bash
bash install_314.sh
```

This script installs from `requirements-314.txt` and then installs `facenet-pytorch==2.6.0` with `--no-deps` to avoid a false numpy<2.0 constraint. `pygame` is compiled from source and requires SDL2 system packages (`sdl2`, `sdl2_mixer`, etc.) installed via `pacman`.

## Camera API endpoints

| URL | Method | Purpose |
|-----|--------|---------|
| `/camera/start/` | POST | Start CameraManager threads |
| `/camera/stop/`  | POST | Stop all threads, release captures |
| `/camera/status/`| GET  | JSON: `{running, error, logs[]}` |
| `/camera/stream/`| GET  | MJPEG multipart stream for `<img>` tag |

The `CameraManager` singleton lives in `app1/views.py`. It is never restarted automatically — the user presses Start/Stop in the browser. The MJPEG stream is consumed directly by an `<img src="/camera/stream/">` element.

## Architecture

### Request flow

```
Browser → Project101/urls.py → app1/urls.py → app1/views.py → templates/
```

All templates live at the project root under `templates/` (not inside the app). Media uploads (student photos, QR codes) are stored under `media/`.

### ML pipeline (`app1/views.py`)

The face recognition stack (PyTorch + facenet-pytorch) is loaded lazily via module-level singletons `_mtcnn` and `_resnet`, initialized on first call to `_get_models()`. This lets Django start and run management commands without the ML stack being imported.

Recognition flow when the camera is running:
1. One OS thread per `CameraConfiguration` is spawned via `threading.Thread`.
2. Each thread opens its camera source (integer index for webcam, URL string for IP camera) with OpenCV.
3. Per frame: `_detect_and_encode()` runs MTCNN + InceptionResnetV1 to get 512-d embeddings.
4. Embeddings are compared via L2 distance to the cached known embeddings (`_get_known_embeddings()`).
5. **Exactly 1 embedding per student** is cached. Multi-face photos use the first detected face only. Corrupted or unreadable photos are skipped with a `WARNING` log.
6. On recognition: `record_attendance()` in `utils.py` handles check-in/check-out logic with the configurable delay.
7. The per-frame face recognition block is wrapped in `try/except` — a bad frame or ML error clears the overlay and continues streaming without crashing the worker.
8. Display is `cv2.flip(frame, 1)` (mirrored); bounding-box x-coordinates are remapped so labels stay over the correct face.
9. Pygame plays `app1/suc.wav` on each check-in/check-out event.

### Models (`app1/models.py`)

- **`Student`** — person record with photo, `authorized` flag, and optional `position`, `area`, `work_schedule`, `student_class`, `email`, `phone_number` fields. `qr_active` controls QR attendance independently.
- **`Attendance`** — one record per student per day; `check_in_time` / `check_out_time` are timestamps; `calculate_duration()` formats the session length.
- **`CameraConfiguration`** — named camera entry with `camera_source` (int index or RTSP/HTTP URL) and `threshold` (per-camera override; default 0.6; lower = stricter).
- **`SystemConfig`** — singleton model (`pk=1`). Access via `SystemConfig.get()`. Fields: `face_recognition_enabled`, `qr_enabled`, `checkout_delay_minutes`, `display_throttle_seconds`, `recognition_threshold`.

### Access control

- **Public** (no login required): `/`, `/kiosk/`, `/login/`, `/logout/`, `/camera/stream/`, `/students/attendance/`
- **Admin-only** (`@login_required` + `@user_passes_test(is_admin)` where `is_admin` checks `user.is_superuser`):
  - `/capture_student/` — register new person
  - `/import/` — bulk CSV/Excel import
  - `/students/` and sub-paths — manage students
  - `/students/attendance/export/*` — export reports
  - `/students/<pk>/credential/` — credential card
  - `/camera-config/…` — manage camera sources
  - `/config/` — system configuration

### Student registration flow

Admins register personnel at `/capture_student/`. The webcam captures a photo as base64-encoded POST field (`image_data`). Required fields: `name`. Optional: `email`, `phone_number`, `student_class`, `position`, `area`, `work_schedule`. Students created this way start with `authorized=True` and an auto-generated QR code. The embedding cache is invalidated immediately so the new person is recognizable right away.

### Embedding cache internals

`_get_known_embeddings()` (module-level, `app1/views.py`):
- Refreshes every 30 seconds (`_CACHE_TTL = 30.0`) or when `invalidate_embedding_cache()` is called.
- Skips students with no image field, unreadable image files, or 0 faces detected in the photo (with `WARNING` logs for each).
- If >1 face is detected in a registration photo (group photo uploaded by mistake), uses only `encs[0]` and logs a `WARNING`.
- Asserts `len(known_enc) == len(known_names)` before caching; on mismatch, resets both to empty lists.

### Attendance cooldown layers

| Layer | Constant | Effect |
|-------|----------|--------|
| `_attendance_cooldown` | `_COOLDOWN_SECONDS = 10` | Prevents DB writes within 10 s per person |
| `_cooldown_display` | `_DISPLAY_THROTTLE = 5.0` | "ya fue registrado" feedback at most once per 5 s per person |
| Checkout delay | `SystemConfig.checkout_delay_minutes` | Check-out only after N minutes |
| Frontend throttle | `_ALREADY_DONE_MS = 12000` (JS) | Per-person card shown at most once per 12 s in browser |

## Important file paths

| Path | Purpose |
|------|---------|
| `app1/views.py` | All business logic, ML pipeline, CameraManager, export views |
| `app1/models.py` | All Django models |
| `app1/utils.py` | `generate_qr_for_student()`, `record_attendance()` |
| `app1/urls.py` | All URL patterns |
| `templates/base.html` | Shared layout, dark glassmorphism CSS variables |
| `templates/attendance_kiosk.html` | Public kiosk — MJPEG + event overlay + Web Audio |
| `templates/capture_student.html` | Registration form + mirrored webcam |
| `templates/student_attendance_list.html` | Report with filters + export bar |
| `templates/import_students.html` | Drag-and-drop CSV/Excel import |
| `templates/student_credential.html` | Printable ID card |
| `templates/system_config.html` | iOS-style config toggles |
| `Project101/settings.py` | Django settings (timezone, media root, static files) |

## Known gotchas

- Do not `pip install -r requirements.txt` on Python 3.14 — use `install_314.sh`.
- `facenet-pytorch==2.6.0` must be installed with `--no-deps` (stale `numpy<2.0` metadata constraint).
- `pygame` has no cp314 wheel — `install_314.sh` compiles it from source, which requires SDL2 system packages.
- On headless servers, set `SDL_AUDIODRIVER=dummy` to prevent Pygame audio errors.
- `db.sqlite3` and `media/` are gitignored — do not commit them.
- Stray `=version` files in the project root (created by malformed `pip install =x.y.z` invocations) are also gitignored via the `=*` pattern in `.gitignore`.
