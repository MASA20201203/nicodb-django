from django.db import models

from streamings.constants import StreamingStatus


class Streamer(models.Model):
    """配信者テーブル"""

    streamer_id = models.BigIntegerField(verbose_name="配信者ID")
    name = models.CharField(max_length=16, verbose_name="配信者名")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.name

    @staticmethod
    def get_latest_name(streamer_id: int) -> str:
        """
        指定した `streamer_id` の最新の名前を取得する。

        Args:
            streamer_id (int): 取得したい配信者のID。

        Returns:
            str: 最新の配信者名。該当する配信者がいない場合は "不明" を返す。
        """
        latest_streamer = (
            Streamer.objects.filter(streamer_id=streamer_id).order_by("-created_at").first()
        )
        return latest_streamer.name if latest_streamer else "存在しない配信者です。"


class Streaming(models.Model):
    """配信テーブル"""

    streaming_id = models.BigIntegerField(verbose_name="配信ID")
    title = models.CharField(max_length=100, verbose_name="配信タイトル")
    start_time = models.DateTimeField(verbose_name="配信開始時間")
    end_time = models.DateTimeField(verbose_name="配信終了時間")
    duration_time = models.DurationField(verbose_name="配信時間")
    status = models.IntegerField(
        choices=[(s.value, s.name) for s in StreamingStatus],
        verbose_name="配信ステータス",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    streamer = models.ForeignKey(Streamer, on_delete=models.CASCADE, verbose_name="配信者ID")

    def __str__(self):
        return self.title
