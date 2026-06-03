# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0003_doctordocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctorprofile',
            name='session_duration',
            field=models.IntegerField(default=30),
        ),
    ]
