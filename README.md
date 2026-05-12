# Sistema de Control de Asistencia en Tiempo Real

**Real-time attendance system with facial recognition, QR codes, institutional ID card generation, PostgreSQL, MJPEG streaming, bulk import, Excel/CSV reports, and a dark glassmorphism kiosk UI — built on Django 6 and Python 3.14.**

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start — Docker](#quick-start--docker)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Institutional Fotocheck (ID Cards)](#institutional-fotocheck-id-cards)
- [PostgreSQL](#postgresql)
- [Project Structure](#project-structure)
- [URL Reference](#url-reference)
- [Camera API](#camera-api)
- [Reports & Export](#reports--export)
- [Personnel Import](#personnel-import)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Author](#author)

---

## Overview

A real-time biometric attendance system designed for institutions and organizations. Staff or students approach the kiosk and are recognized automatically by face or QR code — no manual input required. The system records check-in and check-out times, enforces duplicate-prevention logic, generates institutional ID cards (fotochecks) as PNG and print-ready PDF, and provides a full admin panel for managing personnel, cameras, attendance records, and system settings.

---

## Features

### Recognition
- **Real-time facial recognition** via MTCNN + InceptionResnetV1 (512-d embeddings, L2 distance)
- **QR code attendance** — each registered person gets a personal QR (UUID-based) with the institutional logo embedded at the centre
- **Hybrid mode** — face and QR run simultaneously every frame; whichever triggers first marks attendance
- **Temporal stability buffer** — 3-frame confirmation before marking (2 frames at ≥ 80 % confidence)
- **Robust embedding cache** — 1 embedding per person; corrupted photos skipped with warnings; no IndexError on multi-face photos
- **Mirror display** — camera feed is horizontally flipped for natural selfie/webcam feel; recognition uses the original unflipped frame

### Attendance
- **Check-in / Check-out** — automatic: first scan = check-in, second scan (after configurable window) = check-out
- **Smart duplicate prevention** — per-person 10-second debounce, "ya fue registrado" feedback every 5 s while person remains in frame
- **Multi-camera support** — any number of cameras (webcam index or RTSP/HTTP URL)
- **Configurable thresholds** — global default + per-camera override

### Institutional ID Cards (Fotocheck)
- **Template-based generation** — overlays student data on the official `plantilla.jpeg` template
- **Circular face photo** — MTCNN crops and masks the face into the card's photo circle
- **QR with institutional logo** — ERROR_CORRECT_H QR with `logo.jpeg` embedded in the centre
- **PNG + PDF** — 1024 × 1536 px PNG (300 DPI) and a matching print-ready PDF (86 × 129 mm)
- **Automatic generation** — assets are built in a background thread immediately after registration
- **Bulk generation panel** — regenerate cards for all personnel at `/credentials/`
- **Individual download** — download PNG or PDF per person from the credential view

### Admin & Management
- **Bulk personnel import** — CSV or Excel (.xlsx) with Spanish/English column aliases
- **Attendance reports** — filterable by name, area, date range; exportable as CSV or Excel
- **Printable credential card** — glassmorphism ID card with photo, QR, and position details
- **System configuration** — toggle face/QR recognition, set checkout delay, recognition threshold, and display throttle from the UI
- **RBAC** — admins manage everything; public kiosk requires no login

### UX
- **Dark glassmorphism UI** — full-screen kiosk with animated result overlay and Web Audio chimes
- **MJPEG live stream** — single `/camera/stream/` endpoint consumed by `<img>` tag, no WebSocket needed
- **Sound feedback** — Web Audio API chimes on check-in/check-out, distinct tone for "already marked"

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | Django 6.0.5 |
| Language | Python 3.14 |
| Face detection | MTCNN (facenet-pytorch 2.6.0) |
| Face embedding | InceptionResnetV1 — vggface2 pretrained |
| ML framework | PyTorch 2.11 |
| Computer vision | OpenCV 4.13 |
| QR generation | qrcode 8.2 + Pillow 12 |
| QR reading | `cv2.QRCodeDetector` (built-in, zero extra deps) |
| ID card / PDF | Pillow 12 (PNG overlay) + ReportLab 4.5 (PDF) |
| Video streaming | MJPEG multipart over HTTP |
| Database | PostgreSQL 17+ (production) / SQLite (dev fallback) |
| DB adapter | psycopg2-binary 2.9 |
| Audio | Pygame (server-side) + Web Audio API (browser-side) |
| Excel export/import | openpyxl |
| Frontend | Vanilla JS, CSS glassmorphism, Font Awesome |

---

## Quick Start — Docker

The fastest way to run the system without installing Python or ML dependencies locally.
Docker Compose starts both the **Django web service** and a **PostgreSQL 17** database automatically.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2.20+
- A camera connected to the host (optional — the system runs without one)

> **Image size warning:** The first build downloads PyTorch (~1–2 GB CPU build) and other heavy ML libraries. Expect 5–8 GB total image size and 10–20 minutes on the first build. Subsequent builds use the Docker layer cache.

### 1. Clone and configure

```bash
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia
cp .env.example .env
# Edit .env — set DB_PASSWORD, SECRET_KEY and any other values
```

### 2. Build the image

```bash
docker compose build
```

### 3. Run the system

```bash
docker compose up
```

`entrypoint.sh` waits for PostgreSQL to be ready, then runs `python manage.py migrate` automatically. Open `http://localhost:8000/` in your browser.

To run in the background:

```bash
docker compose up -d
```

### 4. Create an admin user

```bash
docker compose exec web python manage.py createsuperuser
```

### 5. Enable camera access (Linux)

Edit `docker-compose.yml` and uncomment the `devices` section:

```yaml
devices:
  - /dev/video0:/dev/video0
```

Your user must be in the `video` group on the host:

```bash
sudo usermod -aG video $USER   # log out and back in
```

Then restart the container:

```bash
docker compose down && docker compose up
```

### Common Docker commands

```bash
# View live logs
docker compose logs -f

# Stop the system
docker compose down

# Rebuild after dependency changes
docker compose build --no-cache

# Run any manage.py command
docker compose exec web python manage.py <command>

# Open a shell inside the container
docker compose exec web bash

# Apply migrations manually
docker compose exec web python manage.py migrate

# Regenerate all fotochecks inside the container
docker compose exec web python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    generate_all_fotocheck_assets(s)
    print(s.name, 'done')
"
```

### Docker file overview

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.14-slim image with all system and Python deps |
| `docker-compose.yml` | Web + PostgreSQL services, ports, volumes, env, camera devices |
| `.dockerignore` | Excludes venv, media, .git, caches from build context |
| `requirements-docker.txt` | Headless deps (opencv-headless; torch installed separately) |
| `entrypoint.sh` | Waits for DB, auto-runs migrations, then starts the server |

---

## Requirements

### Hardware

- Webcam or IP camera accessible from the server
- GPU optional but recommended for faster face recognition

### Software

- Python 3.14 (Arch Linux — see `install_314.sh`) or Python 3.12+ (other systems)
- PostgreSQL 17+ for production; SQLite works for local development
- Liberation Sans fonts for ID card text: `ttf-liberation` (Arch) / `fonts-liberation` (Debian/Ubuntu)
- SDL2 system libraries for Pygame audio: `sdl2 sdl2_mixer sdl2_image sdl2_ttf portmidi`
- Git + SSH key configured for GitHub

---

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia
```

### 2. Create and activate a virtual environment

```bash
python3.14 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

**On Python 3.14 / Arch Linux (recommended):**

```bash
bash install_314.sh
```

This script:
1. Installs SDL2 system packages via `pacman`
2. Installs all Python packages from `requirements-314.txt`
3. Installs `facenet-pytorch==2.6.0` with `--no-deps` (avoids a false `numpy<2.0` constraint)

**On Python 3.12 / other systems:**

```bash
pip install -r requirements.txt
pip install --no-deps facenet-pytorch==2.6.0
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env — at minimum set DB_PASSWORD if using PostgreSQL
```

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (admin)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The kiosk is available at `http://127.0.0.1:8000/`.

---

## Configuration

### Environment variables

Copy `.env.example` to `.env` and fill in values for production:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | insecure dev key | Django secret key — **change in production** |
| `DEBUG` | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hosts |
| `DB_ENGINE` | `django.db.backends.postgresql` | Set to `django.db.backends.sqlite3` for local dev |
| `DB_NAME` | `attendance_db` | PostgreSQL database name |
| `DB_USER` | `attendance_user` | PostgreSQL user |
| `DB_PASSWORD` | _(required)_ | PostgreSQL password |
| `DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `SDL_AUDIODRIVER` | _(unset)_ | Set to `dummy` on headless servers |

### System configuration (in-app)

Go to **System Configuration** (`/config/`) in the admin panel to adjust:

| Setting | Description |
|---------|-------------|
| Face recognition enabled | Toggle face recognition globally |
| QR attendance enabled | Toggle QR attendance globally |
| Check-out delay (min) | Minimum minutes between check-in and check-out |
| Duplicate feedback throttle (s) | Seconds between "ya fue registrado" messages per person |
| Default recognition threshold | L2 distance cutoff (0.1–1.0; lower = stricter) |

### Camera setup

1. Log in as admin
2. Go to **Camera Config** → **Add**
3. Enter a name and camera source:
   - Local webcam: `0` (or `1`, `2` for additional cameras)
   - IP camera: `rtsp://user:pass@192.168.1.100/stream`
   - HTTP MJPEG: `http://192.168.1.100:8080/video`
4. Optionally set a per-camera recognition threshold (overrides global default)

---

## Usage

### Personnel registration (admin)

1. Log in as admin
2. Go to **Register Student** (`/capture_student/`)
3. Fill in name, DNI, email, phone, position, area, work schedule, and class/group
4. Capture a photo via the webcam tab **or** upload a photo file
5. The person is immediately authorized; QR, face crop, PNG card, and PDF card are generated in the background

### Bulk personnel import (admin)

1. Go to **Import Personnel** (`/import/`)
2. Upload a CSV or Excel file
3. Required column: `name` or `nombre`
4. Optional columns: `email`, `phone_number`, `position`/`cargo`, `area`/`área`, `work_schedule`/`horario`, `student_class`/`clase`, `dni`
5. All imported rows are auto-authorized with a generated QR code

### Attendance kiosk (public)

1. Open `http://127.0.0.1:8000/` — redirects to the kiosk
2. Press **Start Camera**
3. The person looks at the camera **or** shows their QR code
4. The system recognizes them and records attendance automatically:
   - **First scan of the day** → Check-in registered
   - **After check-out delay** → Check-out registered
   - **Already marked** → "Ya fue registrado" card shown (no duplicate in DB)

### Attendance reports (admin)

1. Go to **Attendance** (`/students/attendance/`)
2. Filter by name, area, or date range
3. Export results as **Excel** or **CSV**
4. Print the filtered table directly from the browser

### Credential / Fotocheck (admin)

1. Go to **Students** → select a person → **Credential** (`/students/<pk>/credential/`)
2. Preview the generated PNG card with the institutional template
3. Download the **PNG** (screen use) or **PDF** (print-ready, 86 × 129 mm)
4. Click **Regenerate** to rebuild all assets if the template or data changed

---

## Institutional Fotocheck (ID Cards)

The system automatically generates institutional ID cards (fotochecks) for every registered person.
Cards are built by overlaying student data on the official template image and are available as a high-resolution PNG and a print-ready PDF.

### Card specifications

| Property | Value |
|----------|-------|
| Base image | `plantilla.jpeg` (official IESTP Paucartambo template) |
| Output size | 1024 × 1536 px portrait |
| Print size | 86 × 129 mm at 300 DPI |
| Formats | PNG (download / screen) + PDF (print-ready) |
| QR error correction | ERROR_CORRECT_H (~30 % recovery — survives logo overlay) |
| Face detection | MTCNN crop + circular mask |
| Fonts | Liberation Sans Bold / Regular |

### Asset locations

```
app1/static/app1/fotocheck_assets/
    plantilla.jpeg   ← card background template  (versioned in git)
    logo.jpeg        ← institutional logo (embedded in QR centre)  (versioned in git)
```

### How to replace the template

1. Replace `app1/static/app1/fotocheck_assets/plantilla.jpeg` with the new template image.
2. Update the pixel-coordinate constants at the top of `app1/fotocheck.py`:
   - `PHOTO_CX`, `PHOTO_CY`, `PHOTO_R` — centre and radius of the face circle
   - `NAME_X1 … NAME_Y2` — name text bounding box
   - `DNI_VAL_X`, `DNI_VAL_Y`, `CARGO_VAL_Y`, `AREA_VAL_Y` — field value positions
   - `QR_X1 … QR_Y2` — QR code paste zone
   - `ESTADO_CX`, `ESTADO_CY` — ACTIVO/INACTIVO badge centre
3. Run the bulk regeneration command (see below) to rebuild all cards.

### How to replace the institutional logo (QR centre)

1. Replace `app1/static/app1/fotocheck_assets/logo.jpeg` with the new logo.
2. Regenerate all QR codes + cards:

```bash
python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    generate_all_fotocheck_assets(s)
    print(s.name, 'OK')
"
```

### How to regenerate fotochecks (bulk)

**Via the web UI:**
Go to `/credentials/` → click **Generate All**.

**Via the Django shell:**

```bash
source venv/bin/activate
python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    r = generate_all_fotocheck_assets(s)
    print(s.name, r)
"
```

**Via Docker:**

```bash
docker compose exec web python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    generate_all_fotocheck_assets(s)
    print(s.name, 'done')
"
```

### How to print at real size (86 × 129 mm)

1. Download the **PDF** from `/students/<pk>/credential/` → **Download PDF**.
2. Open in any PDF viewer (Acrobat, Okular, Evince).
3. In the print dialog, set **page scaling to None / Actual size** (do not scale to fit).
4. The PDF page is already set to exactly 86 × 129 mm at 300 DPI — it will print at the correct physical size.
5. For standard credit-card size (85.6 × 54 mm), crop horizontally after printing, or adjust `CARD_H` in `fotocheck.py` to match your template's actual height.

### Individual regeneration (per person)

```
POST /students/<pk>/fotocheck/regen/
```

Accessible via the **Regenerate** button on the credential page. Rebuilds QR, face crop, PNG, and PDF in a background thread.

---

## PostgreSQL

The project uses **PostgreSQL** by default. SQLite is available as a development fallback by setting `DB_ENGINE=django.db.backends.sqlite3` in `.env`.

### Local setup (Arch Linux)

```bash
# Install and start PostgreSQL
sudo pacman -S postgresql
sudo systemctl enable --now postgresql

# Create user and database
sudo -u postgres psql <<'SQL'
CREATE USER attendance_user WITH PASSWORD 'YourStrongPassword';
CREATE DATABASE attendance_db OWNER attendance_user;
GRANT ALL PRIVILEGES ON DATABASE attendance_db TO attendance_user;
SQL

# Configure .env
echo "DB_ENGINE=django.db.backends.postgresql" >> .env
echo "DB_NAME=attendance_db" >> .env
echo "DB_USER=attendance_user" >> .env
echo "DB_PASSWORD=YourStrongPassword" >> .env
echo "DB_HOST=127.0.0.1" >> .env
echo "DB_PORT=5432" >> .env

# Apply migrations
source venv/bin/activate
python manage.py migrate
```

### Migrating from SQLite to PostgreSQL

```bash
# 1. Export data from SQLite
DB_ENGINE=django.db.backends.sqlite3 python manage.py dumpdata \
  --natural-foreign --natural-primary \
  --exclude=admin.logentry --exclude=contenttypes \
  --indent=2 > data_backup.json

# 2. Switch .env to PostgreSQL and run migrations
python manage.py migrate

# 3. Load data (fake migration 0004 if DuplicateColumn appears)
python manage.py loaddata data_backup.json

# 4. Reset PostgreSQL sequences
python manage.py sqlsequencereset app1 | python manage.py dbshell
```

> **Known quirk:** Migration `app1.0004_uploadedimage_authorized` may fail on PostgreSQL with `DuplicateColumn` because `0001_initial` already creates the column. Fix: `python manage.py migrate app1 0003 && python manage.py migrate app1 0004 --fake && python manage.py migrate`

---

## Project Structure

```
.
├── app1/                                   # Main Django application
│   ├── models.py                           # Student, Attendance, CameraConfiguration, SystemConfig
│   ├── views.py                            # All views + CameraManager (MJPEG + ML pipeline)
│   ├── fotocheck.py                        # Institutional ID card generator (PNG + PDF)
│   ├── utils.py                            # QR generation, attendance recording logic
│   ├── urls.py                             # App URL patterns
│   ├── admin.py                            # Django admin registration
│   ├── forms.py                            # Django forms
│   ├── migrations/                         # Database migrations
│   │   ├── 0001_initial.py
│   │   ├── ...
│   │   └── 0013_student_fotocheck_fields.py  # dni, face_crop, fotocheck_png, fotocheck_pdf
│   ├── static/app1/fotocheck_assets/       # Institutional card assets (versioned)
│   │   ├── plantilla.jpeg                  # Official card template image
│   │   └── logo.jpeg                       # Institutional shield/logo for QR centre
│   └── suc.wav                             # Success sound (server-side Pygame)
├── Project101/                             # Django project package
│   ├── settings.py                         # Env-driven DB backend (PostgreSQL default)
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── templates/                              # All HTML templates (project-level)
│   ├── base.html                           # Shared layout + dark glassmorphism CSS
│   ├── attendance_kiosk.html               # Public kiosk (MJPEG + result overlay)
│   ├── capture_student.html                # Personnel registration (webcam + file upload)
│   ├── credentials_list.html               # Bulk fotocheck management panel
│   ├── student_credential.html             # Per-person card preview + downloads
│   ├── student_attendance_list.html        # Attendance report with export
│   ├── import_students.html                # Bulk CSV/Excel import
│   ├── system_config.html                  # System settings
│   └── ...                                # Other admin templates
├── media/                                  # Uploaded files (gitignored)
│   ├── students/                           # Face photos
│   ├── qrcodes/                            # Generated QR PNG files
│   ├── faces/                              # Circular face crops
│   └── fotochecks/                         # Generated PNG and PDF cards
├── Dockerfile                              # Python 3.14-slim image definition
├── docker-compose.yml                      # Web + PostgreSQL services
├── entrypoint.sh                           # Wait for DB → migrate → runserver
├── .dockerignore                           # Excludes venv, media, caches from context
├── requirements.txt                        # Dependencies (Python 3.12+ reference)
├── requirements-314.txt                    # Dependencies (Python 3.14 / Arch Linux)
├── requirements-docker.txt                 # Dependencies (headless Docker build)
├── install_314.sh                          # Local setup script for Python 3.14 / Arch
├── manage.py
├── .env.example                            # Template for environment variables
├── CLAUDE.md                               # Notes for Claude Code AI assistant
└── LICENSE
```

---

## URL Reference

| URL | Method | Auth | Description |
|-----|--------|------|-------------|
| `/` | GET | Public | Redirect to kiosk |
| `/kiosk/` | GET | Public | Attendance kiosk |
| `/capture_student/` | GET/POST | Admin | Register new person |
| `/import/` | GET/POST | Admin | Bulk CSV/Excel import |
| `/students/` | GET | Admin | Personnel list |
| `/students/<pk>/` | GET | Admin | Personnel detail |
| `/students/<pk>/authorize/` | GET/POST | Admin | Toggle face+QR access |
| `/students/<pk>/credential/` | GET | Admin | Printable ID card |
| `/students/<pk>/fotocheck/png/` | GET | Admin | Download fotocheck PNG |
| `/students/<pk>/fotocheck/pdf/` | GET | Admin | Download fotocheck PDF |
| `/students/<pk>/fotocheck/regen/` | POST | Admin | Regenerate all card assets |
| `/students/<pk>/qr/` | GET | Admin | Download QR PNG |
| `/students/<pk>/regenerate-qr/` | POST | Admin | Regenerate QR |
| `/students/<pk>/delete/` | GET/POST | Admin | Delete person |
| `/credentials/` | GET | Admin | Bulk fotocheck management |
| `/credentials/generate/` | POST | Admin | Bulk regenerate all cards |
| `/students/attendance/` | GET | Admin | Attendance report |
| `/students/attendance/export/csv/` | GET | Admin | Export CSV |
| `/students/attendance/export/excel/` | GET | Admin | Export Excel |
| `/config/` | GET/POST | Admin | System configuration |
| `/camera-config/` | GET/POST | Admin | Add camera |
| `/camera-config/list/` | GET | Admin | List cameras |
| `/camera/start/` | POST | Admin | Start worker threads |
| `/camera/stop/` | POST | Admin | Stop all threads |
| `/camera/status/` | GET | Admin | JSON: `{running, error, logs[]}` |
| `/camera/stream/` | GET | Public | MJPEG multipart stream |
| `/login/` | GET/POST | Public | Login |
| `/logout/` | GET | Auth | Logout |

---

## Camera API

These endpoints are consumed internally by the kiosk frontend:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/camera/start/` | POST | Start `CameraManager` worker threads |
| `/camera/stop/` | POST | Stop all threads and release captures |
| `/camera/status/` | GET | JSON: `{running, error, logs[]}` — polled every 1 s |
| `/camera/stream/` | GET | MJPEG multipart stream for `<img src="...">` |

The `logs[]` array carries attendance events (`checked_in`, `checked_out`, `already_done`, `qr_invalid`, `error`) that the frontend renders as overlay cards.

---

## Reports & Export

The attendance report at `/students/attendance/` supports:

- **Search** by name
- **Filter** by area/department
- **Date range** filter
- **Export to CSV** — standard comma-separated, UTF-8
- **Export to Excel** — `.xlsx` with formatted headers via openpyxl
- **Print** — print-optimized CSS hides the sidebar and controls

Columns exported: Date, Name, Position, Area, Work Schedule, Class/Group, Check-in, Check-out, Duration.

---

## Personnel Import

Supported file formats: `.csv` (UTF-8 or UTF-8 BOM) and `.xlsx`.

| Column | Alias | Required |
|--------|-------|----------|
| `name` | `nombre` | **Yes** |
| `dni` | `dni` | No |
| `email` | `correo` | No |
| `phone_number` | `telefono` | No |
| `position` | `cargo` | No |
| `area` | `área` | No |
| `work_schedule` | `horario` | No |
| `student_class` | `clase` | No |

All imported rows are auto-authorized and receive a generated QR code. Rows missing `name` and rows with duplicate emails are skipped with a warning.

---

## Architecture

### ML Pipeline (per frame)

```
cap.read() → frame (original, unflipped)
    │
    ├─► _decode_qr(frame)              QR: resize→640px, raw gray → cv2.QRCodeDetector
    │         └─► _handle_qr()         per-person 10s debounce + DB write
    │
    ├─► _detect_and_encode(rgb)         MTCNN detect → InceptionResnetV1 embed
    │         └─► _recognize()          L2 distance vs cached embeddings (validated)
    │                   └─► _handle_face()  stability buffer (3 frames) → DB write
    │
    └─► cv2.flip(frame, 1)             Mirror for display only
              └─► bounding boxes        x coords remapped: mx = w - x
              └─► imencode → MJPEG queue
```

### Fotocheck pipeline

```
generate_all_fotocheck_assets(student)
    │
    ├─► generate_qr_with_logo()        qrcode (ERROR_CORRECT_H) + logo.jpeg overlay → media/qrcodes/
    ├─► save_face_crop()               MTCNN crop + circular mask → media/faces/
    ├─► generate_fotocheck_png()       Open plantilla.jpeg → erase template fields →
    │                                   paste face photo, write text, paste QR → media/fotochecks/
    └─► generate_fotocheck_pdf()       PNG → ReportLab canvas at 86×129 mm → media/fotochecks/
```

### Duplicate prevention layers

1. **Per-person debounce** (`_COOLDOWN_SECONDS = 10`): prevents DB writes within 10 s of the last event for that person
2. **Display throttle** (`_DISPLAY_THROTTLE = 5.0`): "ya fue registrado" feedback shown at most once per 5 s per person
3. **Checkout window** (configurable via System Config): check-out only allowed after N minutes
4. **Frontend throttle** (`_ALREADY_DONE_MS = 12000`): per-person card shown at most once per 12 s in the browser

### Embedding cache

- Rebuilt every 30 seconds (`_CACHE_TTL = 30.0`) or invalidated immediately on student changes
- **1 embedding per student** — multi-face photos use only the first detected face with a warning
- Corrupted or unreadable photos are skipped silently (logged as warnings)
- Length sanity check before caching prevents any index mismatch

---

## Troubleshooting

### Camera won't start

```
Error: Cannot open camera: <name>
```

- Verify the camera source index/URL in Camera Config
- Make sure no other process holds the camera (close browser tabs with camera access)
- For IP cameras, test the URL in VLC first

### Face not recognized

- Ensure the person is **authorized** (`authorized=True`) in the admin panel
- Lighting matters — even frontal lighting works best
- Lower the recognition threshold in Camera Config or System Config (e.g., `0.6` → `0.5`)
- The embedding cache refreshes every 30 s; wait after authorizing a new person
- Check Django logs for `WARNING: No face detected in photo for student` — the registration photo may be unusable; re-register with a clear solo portrait

### Fotocheck PNG/PDF not generated

- Check `media/fotochecks/` exists and is writable
- Run `python manage.py check` to verify the application configuration
- Run `from app1.fotocheck import validate_assets; print(validate_assets())` in the Django shell — should return `(True, 'Assets OK')`
- If the template file is missing, copy `plantilla.jpeg` and `logo.jpeg` to `app1/static/app1/fotocheck_assets/`

### PostgreSQL connection refused

```
django.db.utils.OperationalError: connection refused
```

- Verify PostgreSQL is running: `systemctl status postgresql`
- Check `.env` values for `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
- For Docker: the `web` service waits for the `db` healthcheck; check `docker compose logs db`

### pygame / audio errors on headless server

```
pygame.error: No available audio device
```

Set the SDL audio driver to null before starting:

```bash
export SDL_AUDIODRIVER=dummy
python manage.py runserver
```

Or set `SDL_AUDIODRIVER=dummy` in your `.env` file.

### Python 3.14 — no compatible wheel

Run `bash install_314.sh` instead of `pip install -r requirements.txt`. The script handles Python 3.14-specific wheel selection and compiles Pygame from source.

### `facenet-pytorch` numpy conflict

```bash
pip install --no-deps facenet-pytorch==2.6.0
```

The `--no-deps` flag prevents pip from downgrading numpy to satisfy a stale `<2.0` constraint declared in the package metadata.

### Docker — camera device not found

```
Error response from daemon: error gathering device information: no such file or directory
```

The host doesn't have `/dev/video0`. Either:
- Comment out the `devices` block in `docker-compose.yml` if running without a camera
- Verify the camera is connected: `ls /dev/video*`
- Use the correct device path if it's `/dev/video1` or higher

### Docker — pygame audio error

```
pygame.error: No available audio device
```

Add to your `.env`:

```
SDL_AUDIODRIVER=dummy
SDL_VIDEODRIVER=dummy
```

These are already set in `.env.example`. The kiosk uses browser-side Web Audio API for chimes; the server-side pygame beep is optional.

### Docker — OpenCV import error

```
ImportError: libGL.so.1: cannot open shared object file
```

The `libgl1` system package is missing. Rebuild the image:

```bash
docker compose build --no-cache
```

If the problem persists, verify the Dockerfile installs `libgl1` in the `apt-get` block.

### Import fails with encoding error

CSV files must be saved as **UTF-8** or **UTF-8 BOM** (the default for Excel-exported CSVs). The template downloadable from the import page uses UTF-8 BOM.

---

## How to clone and run on another machine

```bash
# 1. Clone
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia

# 2. Configure environment
cp .env.example .env
# Edit .env: set DB_PASSWORD (and optionally DB_ENGINE=sqlite3 for dev)

# Option A — Docker (recommended, no Python install needed)
docker compose build
docker compose up
docker compose exec web python manage.py createsuperuser

# Option B — Local Python 3.14 (Arch Linux)
python3.14 -m venv venv
source venv/bin/activate
bash install_314.sh
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# 3. Open the kiosk
# http://localhost:8000/
```

The institutional template assets (`plantilla.jpeg`, `logo.jpeg`) are versioned in the repository under `app1/static/app1/fotocheck_assets/` — no manual copying required after cloning.

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## Author

**Wil-1302**
- GitHub: [@Wil-1302](https://github.com/Wil-1302)
- Email: travezanorodriguezjonh@gmail.com

---

*Built with Django 6, PyTorch 2.11, OpenCV 4.13, ReportLab 4.5, and Python 3.14.*
