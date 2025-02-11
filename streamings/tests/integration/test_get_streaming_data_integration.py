import pytest
from django.core.management import call_command

from streamings.models import Streamer, Streaming


@pytest.mark.django_db
def test_handle_integration():
    """
    `handle()` の結合テスト: 実際に DB にデータを保存し、処理が成功することを確認
    """
    # Given: テスト用の streaming_id
    streaming_id = "346883570"

    # When: `handle()` を実行（Django の `call_command()` を使用）
    call_command("get_streaming_data", streaming_id)

    # Then: StreamingデータがDBに保存されていることを確認
    streaming = Streaming.objects.filter(streaming_id="346883570").first()
    assert streaming is not None  # 配信データが保存されているか？
    assert streaming.title == "ドライブ配信"  # タイトルが正しく保存されているか？
    assert streaming.status == "ENDED"  # ステータスが正しく保存されているか？

    # Then: StreamerデータがDBに保存されていることを確認
    streamer = Streamer.objects.filter(id=streaming.streamer.id).first()
    assert streamer is not None  # 配信者データが保存されているか？
    assert streamer.name == "3時サブ垢"  # 配信者名が正しく保存されているか？
