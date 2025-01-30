from django.contrib import admin

from .models import Streamer, Streaming


@admin.register(Streamer)
class StreamerAdmin(admin.ModelAdmin):
    list_display = ("id", "streamer_id", "name")


@admin.register(Streaming)
class StreamingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "streaming_id",
        "title",
        "start_time",
        "end_time",
        "duration_time",
        "status",
        "streamer_id",
    )
