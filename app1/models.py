import uuid
from django.db import models
from django.utils import timezone


class Student(models.Model):
    # ── Identity ──────────────────────────────────────────────────────
    unique_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        help_text="Persistent ID encoded in the student's QR code"
    )
    name          = models.CharField(max_length=255)
    email         = models.EmailField(max_length=255)
    phone_number  = models.CharField(max_length=15)
    student_class = models.CharField(max_length=100)
    position      = models.CharField(max_length=150, blank=True, default='')
    area          = models.CharField(max_length=150, blank=True, default='')
    work_schedule = models.CharField(max_length=100, blank=True, default='')

    # ── Identity document ─────────────────────────────────────────────
    dni = models.CharField(
        max_length=20, blank=True, default='',
        help_text="DNI / national ID number printed on the fotocheck"
    )

    # ── Face / QR ─────────────────────────────────────────────────────
    image     = models.ImageField(upload_to='students/')
    authorized = models.BooleanField(default=False)
    qr_code   = models.ImageField(
        upload_to='qrcodes/', blank=True, null=True,
        help_text="Auto-generated QR image (UUID encoded) with institutional logo"
    )
    qr_active = models.BooleanField(
        default=True,
        help_text="Disable to block this student's QR from marking attendance"
    )

    # ── Fotocheck assets ──────────────────────────────────────────────
    face_crop     = models.ImageField(
        upload_to='faces/', blank=True, null=True,
        help_text="Circular face crop (auto-generated from photo)"
    )
    fotocheck_png = models.ImageField(
        upload_to='fotochecks/', blank=True, null=True,
        help_text="Institutional ID card — 86×54 mm @ 300 DPI PNG"
    )
    fotocheck_pdf = models.FileField(
        upload_to='fotochecks/', blank=True, null=True,
        help_text="Institutional ID card — print-ready PDF 86×54 mm"
    )

    def __str__(self):
        return self.name


class Attendance(models.Model):
    student       = models.ForeignKey(Student, on_delete=models.CASCADE)
    date          = models.DateField()
    check_in_time  = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} - {self.date}"

    def mark_checked_in(self):
        self.check_in_time = timezone.now()
        self.save()

    def mark_checked_out(self):
        if self.check_in_time:
            self.check_out_time = timezone.now()
            self.save()
        else:
            raise ValueError("Cannot mark check-out without check-in.")

    def calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            h, rem = divmod(int(delta.total_seconds()), 3600)
            m, s   = divmod(rem, 60)
            return f"{h}h {m}m {s}s"
        return None

    def save(self, *args, **kwargs):
        if not self.pk:
            self.date = timezone.localdate()
        super().save(*args, **kwargs)


class CameraConfiguration(models.Model):
    name          = models.CharField(max_length=100, unique=True)
    camera_source = models.CharField(max_length=255)
    threshold     = models.FloatField(default=0.6)

    def __str__(self):
        return self.name


class SystemConfig(models.Model):
    """Singleton — always use SystemConfig.get() to read/write."""
    face_recognition_enabled  = models.BooleanField(default=True)
    qr_enabled                = models.BooleanField(default=True)
    checkout_delay_minutes    = models.PositiveIntegerField(default=10)
    display_throttle_seconds  = models.PositiveIntegerField(default=5)
    recognition_threshold     = models.FloatField(default=0.6)

    class Meta:
        verbose_name = 'System Configuration'

    def __str__(self):
        return 'System Configuration'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
