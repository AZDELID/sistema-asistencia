from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='position',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='student',
            name='area',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='student',
            name='work_schedule',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='student',
            name='dni',
            field=models.CharField(
                blank=True, default='',
                help_text='DNI / national ID number printed on the fotocheck',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='face_crop',
            field=models.ImageField(
                blank=True, null=True,
                help_text='Circular face crop (auto-generated from photo)',
                upload_to='faces/',
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='fotocheck_png',
            field=models.ImageField(
                blank=True, null=True,
                help_text='Institutional ID card — 86×54 mm @ 300 DPI PNG',
                upload_to='fotochecks/',
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='fotocheck_pdf',
            field=models.FileField(
                blank=True, null=True,
                help_text='Institutional ID card — print-ready PDF 86×54 mm',
                upload_to='fotochecks/',
            ),
        ),
    ]
