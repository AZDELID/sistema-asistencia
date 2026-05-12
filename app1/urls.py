from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('capture_student/', views.capture_student, name='capture_student'),
    path('selfie-success/', views.selfie_success, name='selfie_success'),

    # Personal kiosk (non-admin attendance terminal)
    path('kiosk/', views.attendance_kiosk, name='attendance_kiosk'),

    # Camera streaming & control
    path('camera/start/',  views.camera_start,  name='camera_start'),
    path('camera/stop/',   views.camera_stop,   name='camera_stop'),
    path('camera/status/', views.camera_status, name='camera_status'),
    path('camera/stream/', views.camera_stream, name='camera_stream'),
    path('capture-and-recognize/', views.capture_and_recognize, name='capture_and_recognize'),

    # Attendance records + export
    path('students/attendance/',              views.student_attendance_list, name='student_attendance_list'),
    path('students/attendance/export/csv/',   views.export_attendance_csv,   name='export_attendance_csv'),
    path('students/attendance/export/excel/', views.export_attendance_excel,  name='export_attendance_excel'),

    # Import personnel
    path('import/', views.import_students, name='import_students'),

    # System config
    path('config/', views.system_config_view, name='system_config'),

    # Student management (admin only)
    path('students/',                        views.student_list,           name='student-list'),
    path('students/<int:pk>/',               views.student_detail,         name='student-detail'),
    path('students/<int:pk>/authorize/',     views.student_authorize,      name='student-authorize'),
    path('students/<int:pk>/delete/',        views.student_delete,         name='student-delete'),
    path('students/<int:pk>/regenerate-qr/', views.student_regenerate_qr,           name='student-regenerate-qr'),
    path('students/<int:pk>/qr/',            views.student_qr_download,             name='student-qr-download'),
    path('students/<int:pk>/credential/',    views.student_credential,              name='student-credential'),
    path('students/<int:pk>/fotocheck/png/', views.student_fotocheck_download_png,  name='student-fotocheck-png'),
    path('students/<int:pk>/fotocheck/pdf/', views.student_fotocheck_download_pdf,  name='student-fotocheck-pdf'),
    path('students/<int:pk>/fotocheck/regen/', views.student_regenerate_fotocheck,  name='student-fotocheck-regen'),

    # Bulk credentials panel
    path('credentials/',          views.credentials_list,           name='credentials-list'),
    path('credentials/generate/', views.credentials_bulk_generate,  name='credentials-bulk-generate'),

    # Auth
    path('login/',  views.user_login,  name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Camera config CRUD
    path('camera-config/',                    views.camera_config_create, name='camera_config_create'),
    path('camera-config/list/',               views.camera_config_list,   name='camera_config_list'),
    path('camera-config/update/<int:pk>/',    views.camera_config_update, name='camera_config_update'),
    path('camera-config/delete/<int:pk>/',    views.camera_config_delete, name='camera_config_delete'),
]
