from django.db import migrations


class Migration(migrations.Migration):
    """
    Ensures app1_systemconfig exists in databases where 0001_initial was
    applied before SystemConfig was added to the model (migration-squash
    side-effect). Uses IF NOT EXISTS so it is safe for clean installs too.
    """

    dependencies = [
        ('app1', '0002_add_missing_student_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS app1_systemconfig (
                id                       bigserial    PRIMARY KEY,
                face_recognition_enabled boolean      NOT NULL DEFAULT TRUE,
                qr_enabled               boolean      NOT NULL DEFAULT TRUE,
                checkout_delay_minutes   integer      NOT NULL DEFAULT 10,
                display_throttle_seconds integer      NOT NULL DEFAULT 5,
                recognition_threshold    double precision NOT NULL DEFAULT 0.6
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS app1_systemconfig;",
        ),
    ]
