from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from streamings.management.commands.get_streaming_data import (
    Command,
    StreamingData,
    StreamingStatus,
    StreamingType,
)
from streamings.models import Channel, Streamer, Streaming


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
        channel = Channel.objects.create(
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
        )
        streaming_data = StreamingData(
            id="123456789",
            title="Test Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status=StreamingStatus.ENDED.value,
            streamer_id=streamer.streamer_id,
            streamer_name=streamer.name,
            type=StreamingType.USER.value,
            channel_id=channel.channel_id,
            channel_name=channel.name,
            company_name=channel.company_name,
        )

        # When: メソッドを呼び出して配信データを保存
        Command.save_or_update_streaming(streaming_data, streamer, channel)

        # Then: 配信データが作成されたことを確認
        streaming = Streaming.objects.get(streaming_id=streaming_data.id)
        assert streaming.title == "Test Streaming"
        assert streaming.start_time == datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.end_time == datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.duration_time == timedelta(hours=1)
        assert streaming.status == 30
        assert streaming.type == 10
        assert streaming.streamer.streamer_id == 12345
        assert streaming.streamer.name == "Test Streamer"
        assert streaming.channel.channel_id == 0
        assert streaming.channel.name == "-- 存在しないチャンネル --"
        assert streaming.channel.company_name == "-- 存在しない企業 --"

    def test_update_existing_streaming(self):
        """
        既存の配信データがある場合、更新されることを確認
        """
        # Given: 配信者 (Streamer) 、既存の配信データ (Streaming) を作成
        streamer = Streamer.objects.create(streamer_id=12345, name="Test Streamer")
        channel = Channel.objects.create(
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
        )

        # 既存の Streaming レコードを作成
        Streaming.objects.create(
            streaming_id=67890,
            title="Old Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status=StreamingStatus.ON_AIR.value,
            streamer=streamer,
            channel=channel,
            type=StreamingType.USER.value,
        )

        # 更新用の配信データ (StreamingData)
        updated_streaming_data = StreamingData(
            id=67890,  # 同じ streaming_id なので更新されるはず
            title="Updated Streaming",
            start_time=datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 16, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status=StreamingStatus.ENDED.value,
            streamer_id=streamer.streamer_id,
            streamer_name=streamer.name,
            channel_id=channel.channel_id,
            channel_name=channel.name,
            company_name=channel.company_name,
            type=StreamingType.USER.value,
        )

        # When: `save_or_update_streaming` を実行
        Command.save_or_update_streaming(updated_streaming_data, streamer, channel)

        # Then: 既存の Streaming レコードが更新されていることを確認
        streaming = Streaming.objects.get(streaming_id=67890)
        assert streaming.title == "Updated Streaming"
        assert streaming.start_time == datetime(2025, 2, 7, 14, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.end_time == datetime(2025, 2, 7, 16, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.duration_time == timedelta(hours=2)
        assert streaming.status == 30
        assert streaming.streamer == streamer  # Streamer は変更なし
        assert streaming.channel == channel  # Channel は変更なし
        assert streaming.type == 10


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
            status=StreamingStatus.ENDED.value,
            streamer_id="456",
            streamer_name="Test Streamer",
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            channel_name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
            type=StreamingType.USER.value,
        )

        # When: メソッドを呼び出して配信データを保存
        Command.save_streaming_data(streaming_data)

        # Then: 配信者、チャンネル、配信データが作成されたことを確認
        streamer = Streamer.objects.get(streamer_id=int(streaming_data.streamer_id))
        assert streamer.name == "Test Streamer"

        channel = Channel.objects.get(channel_id=int(streaming_data.channel_id))
        assert channel.name == "-- 存在しないチャンネル --"
        assert channel.company_name == "-- 存在しない企業 --"

        streaming = Streaming.objects.get(streaming_id=streaming_data.id)
        assert streaming.title == "Test Streaming"
        assert streaming.start_time == datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.end_time == datetime(2025, 2, 7, 16, 0, 0, tzinfo=dt_timezone.utc)
        assert streaming.duration_time == timedelta(hours=1)
        assert streaming.status == 30
        assert streaming.streamer == streamer
        assert streaming.channel == channel
        assert streaming.type == 10

    def test_update_existing_streaming_data(self):
        """
        既存の配信データがある場合、更新されることを確認
        """
        # Given: 既存の配信者 (Streamer) を作成
        streamer = Streamer.objects.create(streamer_id=12345, name="Test Streamer")
        channel = Channel.objects.create(
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
        )

        # Given: 既存の配信データ (Streaming) を作成
        Streaming.objects.create(
            streaming_id=67890,
            title="Old Streaming",
            start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 10, 13, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=1),
            status=StreamingStatus.ON_AIR.value,
            streamer=streamer,
            channel=channel,
            type=StreamingType.USER.value,
        )

        # Given: 更新用の配信データ
        updated_streaming_data = StreamingData(
            id=67890,
            title="Updated Streaming",
            start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status=StreamingStatus.ENDED.value,
            streamer_id=12345,
            streamer_name="Test Streamer",
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            channel_name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
            type=StreamingType.USER.value,
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
        assert streaming.channel == channel  # Channel は変更されていない
        assert streaming.type == 10


@pytest.mark.django_db
class TestCreateOrUpdateChannelIntegration:
    """Channel.create_or_update_channel メソッドのテストクラス"""

    def test_create_new_channel(self):
        """
        チャンネルが存在しない場合、新規作成されることを確認。
        """
        # Given: テストデータ
        test_channel_id = 12345
        test_channel_name = "テストチャンネル"
        test_company_name = "テスト企業"

        # When: create_or_update_channel を実行
        channel = Command.create_or_update_channel(
            channel_id=test_channel_id,
            channel_name=test_channel_name,
            company_name=test_company_name,
        )

        # Then: 新規作成されたチャンネルを検証
        assert channel.channel_id == 12345
        assert channel.name == "テストチャンネル"
        assert channel.company_name == "テスト企業"
        assert Channel.objects.count() == 1  # DB に 1 レコードのみ存在することを確認

    def test_update_existing_channel(self):
        """
        既存のチャンネルがある場合、情報が更新されることを確認。
        """
        # Given: 既存のチャンネルを作成
        existing_channel = Channel.objects.create(
            channel_id=12345,
            name="古いチャンネル名",
            company_name="古い企業名",
        )

        # When: チャンネル情報を更新
        updated_channel = Command.create_or_update_channel(
            channel_id=12345,
            channel_name="新しいチャンネル名",
            company_name="新しい企業名",
        )

        # Then: チャンネル情報が更新されていることを確認
        assert updated_channel.id == existing_channel.id  # 同じレコードが更新されている
        assert updated_channel.channel_id == 12345
        assert updated_channel.name == "新しいチャンネル名"
        assert updated_channel.company_name == "新しい企業名"
        assert Channel.objects.count() == 1  # 新規作成されていないことを確認

    def test_update_channel_partial_info(self):
        """
        チャンネル名のみを更新する場合のテスト。
        """
        # Given: 既存のチャンネルを作成
        existing_channel = Channel.objects.create(
            channel_id=12345,
            name="古いチャンネル名",
            company_name="テスト企業",
        )

        # When: チャンネル名のみを更新
        updated_channel = Command.create_or_update_channel(
            channel_id=12345,
            channel_name="新しいチャンネル名",
            company_name="テスト企業",  # 同じ企業名
        )

        # Then: チャンネル名のみが更新されていることを確認
        assert updated_channel.id == existing_channel.id
        assert updated_channel.channel_id == 12345
        assert updated_channel.name == "新しいチャンネル名"
        assert updated_channel.company_name == "テスト企業"  # 企業名は変更されていない


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
    assert streaming.status == StreamingStatus.ENDED.value  # ステータスが正しく保存されているか？

    # Then: StreamerデータがDBに保存されていることを確認
    streamer = Streamer.objects.filter(id=streaming.streamer.id).first()
    assert streamer is not None  # 配信者データが保存されているか？
    assert streamer.name == "3時サブ垢"  # 配信者名が正しく保存されているか？
