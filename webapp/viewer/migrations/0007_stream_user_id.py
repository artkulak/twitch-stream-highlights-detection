# Generated by Django 3.1.3 on 2021-04-14 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0006_auto_20210413_1708'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='user_id',
            field=models.CharField(default=0, max_length=200),
            preserve_default=False,
        ),
    ]