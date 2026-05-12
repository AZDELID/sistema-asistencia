"""
Management command: python manage.py download_rembg_model

Downloads the U2Net ONNX model required by rembg for background removal.
Run this once after deployment so the first fotocheck generation is fast.

Usage:
    python manage.py download_rembg_model
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Pre-download the rembg U2Net model for automatic background removal."

    def handle(self, *args, **options):
        self.stdout.write("Downloading rembg U2Net model (~170 MB)…")
        try:
            from rembg import new_session
            session = new_session("u2net")
            self.stdout.write(self.style.SUCCESS(
                "✓ Model downloaded and cached. Background removal is ready."
            ))
        except ImportError:
            self.stdout.write(self.style.ERROR(
                "rembg is not installed. Run: pip install rembg"
            ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Download failed: {exc}"))