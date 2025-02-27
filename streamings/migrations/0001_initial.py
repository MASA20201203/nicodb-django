# Generated by Django 5.1.5 on 2025-02-06 06:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Streamer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("streamer_id", models.BigIntegerField(verbose_name="配信者ID")),
                ("name", models.CharField(max_length=16, verbose_name="配信者名")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新日時")),
            ],
        ),
        migrations.CreateModel(
            name="Streaming",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("streaming_id", models.BigIntegerField(verbose_name="配信ID")),
                ("title", models.CharField(max_length=100, verbose_name="配信タイトル")),
                ("start_time", models.DateTimeField(verbose_name="配信開始時間")),
                ("end_time", models.DateTimeField(verbose_name="配信終了時間")),
                ("duration_time", models.DurationField(verbose_name="配信時間")),
                ("status", models.CharField(max_length=8, verbose_name="配信ステータス")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新日時")),
                (
                    "streamer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="streamings.streamer",
                        verbose_name="配信者ID",
                    ),
                ),
            ],
        ),
    ]
