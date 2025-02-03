from datetime import timedelta

from django.utils.timezone import now

from streamings.models import Streamer, Streaming


def test_streamer_str() -> None:
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


def test_streaming_str() -> None:
    """
    Streaming の __str__() が配信タイトルを返すことをテスト
    """
    # Given: 配信者と配信インスタンスを作成
    streamer = Streamer(streamer_id=123, name="Test Streamer")
    streaming = Streaming(
        streaming_id=456,
        title="Test Streaming",
        start_time=now(),
        end_time=now() + timedelta(hours=1),
        duration_time=timedelta(hours=1),
        status="live",
        streamer_id=streamer,
    )

    # When: __str__() を呼び出し
    result = str(streaming)

    # Then: 配信タイトルが返る
    expected = "Test Streaming"
    assert result == expected
