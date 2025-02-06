from django.db import models


class Streamer(models.Model):
    """配信者テーブル"""

    streamer_id = models.BigIntegerField(verbose_name="配信者ID")
    name = models.CharField(max_length=16, verbose_name="配信者名")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.name


class Streaming(models.Model):
    """配信テーブル"""

    streaming_id = models.BigIntegerField(verbose_name="配信ID")
    title = models.CharField(max_length=100, verbose_name="配信タイトル")
    start_time = models.DateTimeField(verbose_name="配信開始時間")
    end_time = models.DateTimeField(verbose_name="配信終了時間")
    duration_time = models.DurationField(verbose_name="配信時間")
    status = models.CharField(max_length=8, verbose_name="配信ステータス")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    streamer = models.ForeignKey(Streamer, on_delete=models.CASCADE, verbose_name="配信者ID")

    def __str__(self):
        return self.title
