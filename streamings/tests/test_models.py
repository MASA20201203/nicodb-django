from datetime import timedelta

import pytest
from django.utils import timezone

from streamings.models import Streamer, Streaming


class TestStreamerModelStr:
    """Streamer モデルの __str__ メソッドのテストクラス"""

    def test_streamer_str(self) -> None:
        """
        Streamer の __str__() が配信者名を返すことをテスト
        """
        # Given: 配信者インスタンスを作成
        streamer = Streamer(streamer_id=123, name="Test Streamer")

        # When: __str__() を呼び出し
        result = str(streamer)

        # Then: 配信者名が返る
        expected = "Test Streamer"
        assert result == expected


@pytest.mark.django_db
class TestGetLatestName:
    """
    Streamer モデルの get_latest_name メソッドのテストクラス。
    """

    def test_get_latest_name_existing_streamer(self):
        """
        既存の配信者の最新の名前を取得するテスト。
        """
        # Given: 1 人の配信者を作成
        Streamer.objects.create(streamer_id=12345, name="配信者A")

        # When: `get_latest_name()` を実行
        latest_name = Streamer.get_latest_name(12345)

        # Then: 期待する配信者名が返る
        assert latest_name == "配信者A"

    def test_get_latest_name_multiple_names(self):
        """
        複数の名前が登録されている配信者の最新の名前を取得するテスト。
        """
        # Given: `streamer_id=12345` の配信者を2回登録（名前変更履歴）
        Streamer.objects.create(
            streamer_id=12345, name="配信者A", created_at=timezone.now() - timedelta(days=1)
        )
        latest_streamer = Streamer.objects.create(
            streamer_id=12345, name="配信者B", created_at=timezone.now()
        )

        # When: `get_latest_name()` を実行
        latest_name = Streamer.get_latest_name(12345)

        # Then: 最新の名前 "配信者B" が返る
        assert latest_name == latest_streamer.name

    def test_get_latest_name_non_existing_streamer(self):
        """
        存在しない配信者の名前を取得するテスト。
        """
        # When: `get_latest_name()` を実行（存在しない `streamer_id`）
        latest_name = Streamer.get_latest_name(99999)

        # Then: 存在しない配信者メッセージが返る
        assert latest_name == "存在しない配信者です。"


class TestStreamingModelStr:
    """Streaming モデルの __str__ メソッドのテストクラス"""

    def test_streaming_str(self) -> None:
        """
        Streaming の __str__() が配信タイトルを返すことをテスト
        """
        # Given: 配信者と配信インスタンスを作成
        streamer = Streamer(streamer_id=123, name="Test Streamer")
        streaming = Streaming(
            streaming_id=456,
            title="Test Streaming",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            duration_time=timedelta(hours=1),
            status="live",
            streamer=streamer,
        )

        # When: __str__() を呼び出し
        result = str(streaming)

        # Then: 配信タイトルが返る
        expected = "Test Streaming"
        assert result == expected
