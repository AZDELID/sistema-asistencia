# ── Stage: runtime image ──────────────────────────────────────────────────────
# Python 3.14 slim (Debian bookworm-based, smallest official image with pip)
FROM python:3.14-slim

# Prevent .pyc files and enable unbuffered stdout/stderr for clean Docker logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Pygame headless: no display or audio device required inside the container.
    # The kiosk uses MJPEG streaming (browser renders the feed) so SDL is only
    # needed for the server-side audio chime — dummy driver silences the error.
    SDL_AUDIODRIVER=dummy \
    SDL_VIDEODRIVER=dummy

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# Installed in one layer to minimise image size; apt cache is purged at the end.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ── OpenCV headless runtime ─────────────────────────────────────────────
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    # ── FFmpeg (used internally by OpenCV for video decoding) ───────────────
    ffmpeg \
    # ── SDL2 runtime libs (pygame dummy-mode; no window or audio needed) ───
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    # ── V4L2 utilities (camera device access from host) ─────────────────────
    v4l-utils \
    # ── Build tools (needed to compile any C-extension wheels) ─────────────
    gcc \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so Docker caches this heavy layer separately from
# the project source. The layer is only rebuilt when a requirements file changes.

COPY requirements-docker.txt ./

# PyTorch is installed before the rest because it is the heaviest dependency.
# Remove the --index-url flag to pull the full CUDA build from PyPI instead
# (larger image, needed for GPU inference inside the container).
# NOTE: if Python 3.14 wheels are not yet available on the CPU index for your
# exact torch version, remove --index-url and install from PyPI (default).
RUN pip install --no-cache-dir \
        torch==2.11.0 \
        torchvision==0.26.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    || pip install --no-cache-dir \
        torch==2.11.0 \
        torchvision==0.26.0

# Install remaining project dependencies
RUN pip install --no-cache-dir -r requirements-docker.txt

# facenet-pytorch declares a stale numpy<2.0 constraint that would downgrade
# numpy 2.x if installed normally. --no-deps bypasses metadata resolution.
RUN pip install --no-cache-dir --no-deps facenet-pytorch==2.6.0

# ── Project source ────────────────────────────────────────────────────────────
# Copied last so code changes don't invalidate the heavy dependency layers.
COPY . .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
