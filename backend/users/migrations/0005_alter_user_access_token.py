# Generated by Django 5.1.6 on 2025-04-07 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_access_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='access_token',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
