from django.contrib import admin
from django.utils.html import format_html
from .models import Student, Attendance, CameraConfiguration


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'student_class', 'authorized', 'qr_active', 'unique_id_short', 'qr_preview']
    list_filter   = ['student_class', 'authorized', 'qr_active']
    search_fields = ['name', 'email']
    readonly_fields = ['unique_id', 'qr_preview_large']

    @admin.display(description='UUID (short)')
    def unique_id_short(self, obj):
        return str(obj.unique_id)[:8] + '…'

    @admin.display(description='QR')
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="48" height="48">', obj.qr_code.url)
        return '—'

    @admin.display(description='QR Code')
    def qr_preview_large(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="200" height="200"><br>'
                '<a href="{}" download>Download PNG</a>',
                obj.qr_code.url, obj.qr_code.url,
            )
        return 'No QR generated yet.'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'date', 'check_in_time', 'check_out_time']
    list_filter   = ['date']
    search_fields = ['student__name']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'date', 'check_in_time', 'check_out_time']
        return ['date', 'check_in_time', 'check_out_time']

    def save_model(self, request, obj, form, change):
        if change:
            existing = Attendance.objects.get(id=obj.id)
            obj.check_in_time  = existing.check_in_time
            obj.check_out_time = existing.check_out_time
        super().save_model(request, obj, form, change)


@admin.register(CameraConfiguration)
class CameraConfigurationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'camera_source', 'threshold']
    search_fields = ['name']
