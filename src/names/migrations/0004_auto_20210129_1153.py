# Generated by Django 3.1.5 on 2021-01-29 19:53

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('names', '0003_auto_20210129_1150'),
    ]

    operations = [
        migrations.CreateModel(
            name='Revision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset', models.CharField(max_length=30)),
                ('pseudoid', models.CharField(max_length=30, verbose_name='Pseudo ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('username', models.CharField(max_length=255)),
                ('note', models.CharField(blank=1, max_length=255)),
                ('diff', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='farrecord',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
