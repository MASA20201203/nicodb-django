from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest
from django.core.management import call_command
from django.utils import timezone

from streamings.management.commands.get_streaming_data import Command, StreamingData
from streamings.models import Streamer, Streaming


@pytest.mark.django_db
class TestSaveOrGetStreamerIntegration:
    """Streamer.save_or_get_streamer 関数のテストクラス"""

    def test_create_new_streamer(self):
        """
        配信者が存在しない場合、新規作成されることを確認。
        """
        # `save_or_get_streamer()` を実行（新規作成）
        streamer = Command.save_or_get_streamer(12345, "配信者A")

        # 作成された配信者を検証
        assert streamer.streamer_id == 12345
        assert streamer.name == "配信者A"
        assert Streamer.objects.count() == 1  # DB に 1 レコードのみ存在することを確認

    def test_get_existing_streamer_same_name(self):
        """
        既存の配信者の `streamer_id` があり、名前が同じ場合、既存のレコードを取得する。
        """
        # 事前に配信者を作成
        existing_streamer = Streamer.objects.create(streamer_id=12345, name="配信者A")

        # `save_or_get_streamer()` を実行
        streamer = Command.save_or_get_streamer(12345, "配信者A")

        # 既存のレコードが取得されることを検証
        assert streamer.id == existing_streamer.id
        assert streamer.streamer_id == existing_streamer.streamer_id
        assert streamer.name == existing_streamer.name
        assert Streamer.objects.count() == 1  # 新規作成されていないことを確認

    def test_create_new_streamer_when_name_changes(self):
        """
        `streamer_id` が存在するが、`streamer_name` が異なる場合、新規レコードが作成されるテスト。
        """
        # 既存の配信者を作成
        old_streamer = Streamer.objects.create(
            streamer_id=12345, name="配信者A", created_at=timezone.now() - timedelta(days=1)
        )

        # `save_or_get_streamer()` を実行（名前変更）
        new_streamer = Command.save_or_get_streamer(12345, "配信者B")

        # 新規レコードが作成されたことを検証
        assert new_streamer.id != old_streamer.id  # ID が異なる（新規作成）
        assert new_streamer.streamer_id == old_streamer.streamer_id  # 同じ `streamer_id`
        assert new_streamer.name == "配信者B"  # 新しい名前が適用されている
        assert new_streamer.created_at > old_streamer.created_at  # 新レコードの作成日の方が新しい
        assert Streamer.objects.count() == 2  # 2 レコードが存在することを確認


@pytest.mark.django_db
class TestSaveOrUpdateStreamingIntegration:
    """
    Command クラスの save_or_update_streaming メソッドのテストクラス。
    """

    def test_save_or_update_streaming_create(self):
        """
        新規の配信データを作成するテスト。
        """
        # Given: 配信者と配信データを作成
        streamer = Streamer.objects.create(streamer_id=12345, name="Test Streamer")
        streaming_data = StreamingData(
            id="123456789",
            title="Test Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status="ENDED",
            streamer_id=streamer.streamer_id,
            streamer_name=streamer.name,
        )

        # When: メソッドを呼び出して配信データを保存
        Command.save_or_update_streaming(streaming_data, streamer)

        # Then: 配信データが作成されたことを確認
        streaming = Streaming.objects.get(streaming_id=streaming_data.id)
        assert streaming.title == streaming_data.title
        assert streaming.start_time == streaming_data.start_time
        assert streaming.end_time == streaming_data.end_time
        assert streaming.duration_time == streaming_data.duration_time
        assert streaming.status == streaming_data.status
        assert streaming.streamer == streamer

    def test_update_existing_streaming(self):
        """
        既存の配信データがある場合、更新されることを確認
        """
        # Given: 配信者 (Streamer) 、既存の配信データ (Streaming) を作成
        streamer = Streamer.objects.create(streamer_id=12345, name="Test Streamer")

        # 既存の Streaming レコードを作成
        Streaming.objects.create(
            streaming_id=67890,
            title="Old Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status="ON_AIR",
            streamer=streamer,
        )

        # 更新用の配信データ (StreamingData)
        updated_streaming_data = StreamingData(
            id=67890,  # 同じ streaming_id なので更新されるはず
            title="Updated Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 16, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status="ENDED",
            streamer_id=streamer.streamer_id,
            streamer_name=streamer.name,
        )

        # When: `save_or_update_streaming` を実行
        Command.save_or_update_streaming(updated_streaming_data, streamer)

        # Then: 既存の Streaming レコードが更新されていることを確認
        streaming = Streaming.objects.get(streaming_id=67890)
        assert streaming.title == updated_streaming_data.title
        assert streaming.start_time == updated_streaming_data.start_time
        assert streaming.end_time == updated_streaming_data.end_time
        assert streaming.duration_time == updated_streaming_data.duration_time
        assert streaming.status == updated_streaming_data.status
        assert streaming.streamer == streamer  # Streamer は変更なし


@pytest.mark.django_db
class TestSaveStreamingDataIntegration:
    """
    Command クラスの save_streaming_data メソッドのテストクラス。
    """

    def test_save_new_streaming_data(self):
        """
        配信データが存在しない場合、新規作成されることを確認
        """
        # Given: 配信データを作成
        streaming_data = StreamingData(
            id="123",
            title="Test Streaming",
            start_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 16, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status="ENDED",
            streamer_id="456",
            streamer_name="Test Streamer",
        )

        # When: メソッドを呼び出して配信データを保存
        Command.save_streaming_data(streaming_data)

        # Then: 配信者と配信データが作成されたことを確認
        streamer = Streamer.objects.get(streamer_id=int(streaming_data.streamer_id))
        assert streamer.name == streaming_data.streamer_name

        streaming = Streaming.objects.get(streaming_id=streaming_data.id)
        assert streaming.title == streaming_data.title
        assert streaming.start_time == streaming_data.start_time
        assert streaming.end_time == streaming_data.end_time
        assert streaming.duration_time == streaming_data.duration_time
        assert streaming.status == streaming_data.status
        assert streaming.streamer == streamer

    def test_update_existing_streaming_data(self):
        """
        既存の配信データがある場合、更新されることを確認
        """
        # Given: 既存の配信者 (Streamer) を作成
        streamer = Streamer.objects.create(streamer_id=12345, name="Test Streamer")

        # Given: 既存の配信データ (Streaming) を作成
        Streaming.objects.create(
            streaming_id=67890,
            title="Old Streaming",
            start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 10, 13, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status="ON_AIR",
            streamer=streamer,
        )

        # Given: 更新用の配信データ
        updated_streaming_data = StreamingData(
            id=67890,
            title="Updated Streaming",
            start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status="ENDED",
            streamer_id=12345,
            streamer_name="Test Streamer",
        )

        # When: `save_streaming_data` を実行
        Command.save_streaming_data(updated_streaming_data)

        # Then: Streaming のデータが更新されていることを確認
        streaming = Streaming.objects.get(streaming_id=updated_streaming_data.id)
        assert streaming.title == updated_streaming_data.title
        assert streaming.start_time == updated_streaming_data.start_time
        assert streaming.end_time == updated_streaming_data.end_time
        assert streaming.duration_time == updated_streaming_data.duration_time
        assert streaming.status == updated_streaming_data.status
        assert streaming.streamer == streamer  # Streamer は変更されていない


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
