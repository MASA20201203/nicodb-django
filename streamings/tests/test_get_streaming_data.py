import json
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
import requests
from bs4 import Tag
from django.conf import settings
from django.utils import timezone

from streamings.management.commands.get_streaming_data import Command, StreamingData
from streamings.models import Streamer, Streaming


def test_build_streaming_url(monkeypatch):
    """
    build_streaming_url関数が配信IDから正しいURLを生成するかをテスト
    """
    # Given: 環境変数 "STREAMING_BASE_URL" が設定されており、配信IDが 123456789
    streaming_base_url = "https://live.nicovideo.jp/watch/lv"
    monkeypatch.setattr(settings, "STREAMING_BASE_URL", streaming_base_url)
    streaming_id = "123456789"

    # When: build_streaming_url 関数を呼び出す
    result = Command.build_streaming_url(streaming_id)

    # Then: 正しい配信URL（https://live.nicovideo.jp/watch/lv123456789）が生成される
    expected_streaming_url = "https://live.nicovideo.jp/watch/lv123456789"
    assert result == expected_streaming_url


def test_get_default_headers():
    """
    get_default_headers関数が正しいヘッダーを返すかをテスト
    """
    # Given: なし

    # When: get_default_headers 関数を呼び出す
    result = Command.get_default_headers()

    # Then: 期待されるヘッダー情報が返される
    expected_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
    }
    assert result == expected_headers


class TestFetchHtml:
    """
    fetch_html 関数のテストクラス。
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        共通データのセットアップ。
        """
        self.url = "https://live.nicovideo.jp/watch/lv123456789"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
        }

    def test_success(self, requests_mock):
        """
        fetch_html関数が正常にHTMLデータを取得する場合のテスト
        """
        # Given: 正常なレスポンスをモック
        given_html = "<html><body><h1>Test Page</h1></body></html>"
        requests_mock.get(self.url, [{"text": given_html, "status_code": 200}])

        # When: fetch_html関数を呼び出す
        result = Command.fetch_html(self.url, self.headers)

        # Then: 正しいHTMLデータが返される
        expected_html = "<html><body><h1>Test Page</h1></body></html>"
        assert result == expected_html

    def test_http_error(self, requests_mock):
        """
        fetch_html関数がHTTPエラーを処理する場合のテスト
        """
        # Given: HTTPエラーをモック
        requests_mock.get(self.url, status_code=403)

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: 403 Client Error"):
            Command.fetch_html(self.url, self.headers)

    def test_request_exception(self, requests_mock):
        """
        fetch_html関数がリクエスト例外を処理する場合のテスト
        """
        # Given: リクエスト例外をモック
        requests_mock.get(self.url, exc=requests.exceptions.ConnectionError("Connection refused"))

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: Connection refused"):
            Command.fetch_html(self.url, self.headers)


class TestFindScriptTagWithDataProps:
    """
    find_script_tag_with_data_props 関数のテストクラス。
    """

    def test_success(self):
        """
        正しいスクリプトタグがHTML内に存在する場合のテスト
        """
        # Given: 正しいスクリプトタグを含むHTML
        valid_html = """
        <html>
            <body>
                <script id="embedded-data" data-props='{&quot;akashic&quot;:{'></script>
            </body>
        </html>
        """

        # When: find_script_tag_with_data_props関数を実行
        result = Command.find_script_tag_with_data_props(valid_html)

        # Then: 戻り値がTagオブジェクトで、正しい属性を持つ
        assert isinstance(result, Tag)
        assert "data-props" in result.attrs

    def test_multiple_script_tags(self):
        """
        複数のスクリプトタグがHTML内に存在する場合のテスト
        """

        # Given: 複数のスクリプトタグを含むHTML
        multiple_script_tags_html = """
        <html>
            <body>
                <script id="other-data"></script>
                <script id="embedded-data" data-props='{&quot;akashic&quot;:{'></script>
            </body>
        </html>
        """

        # When: find_script_tag_with_data_props関数を実行
        result = Command.find_script_tag_with_data_props(multiple_script_tags_html)

        # Then: 取得したスクリプトタグのid属性が"embedded-data"であることを確認
        assert isinstance(result, Tag)
        assert result["id"] == "embedded-data"
        assert "data-props" in result.attrs

    def test_script_tag_not_found(self):
        """
        スクリプトタグがHTML内に存在しない場合のテスト
        """
        # Given: スクリプトタグが存在しないHTML
        invalid_html = """
        <html>
            <body>
                <div id="other-data"></div>
            </body>
        </html>
        """

        # When & Then: 例外が発生することを確認
        with pytest.raises(
            Exception, match="data_props属性を含むスクリプトタグが見つかりませんでした。"
        ):
            Command.find_script_tag_with_data_props(invalid_html)


class TestParseDataPropsToDict:
    """
    parse_data_props_to_dict 関数のテストクラス。
    """

    def test_success(self):
        """
        スクリプトタグのdata-props属性が正常なJSON形式で取得できる場合のテスト。
        """
        # Given: 正常なJSONデータを含むスクリプトタグ
        html_content = """
        <script id="embedded-data" data-props='{"key": "value"}'></script>
        """
        script_tag_with_data_props = Command.find_script_tag_with_data_props(html_content)

        # When: parse_data_props_to_dictを実行
        result = Command.parse_data_props_to_dict(script_tag_with_data_props)

        # Then: 正しいJSONデータが辞書型で返される
        assert isinstance(result, dict)
        expected_data_props_dict = {"key": "value"}
        assert result == expected_data_props_dict

    def test_empty_data_props(self):
        """
        `data-props` が空文字の場合、ValueError が発生することを確認。
        """
        # Given: `data-props=""` のスクリプトタグ
        html_content = """
        <script id="embedded-data" data-props=""></script>
        """
        script_tag_with_data_props = Command.find_script_tag_with_data_props(html_content)

        # When & Then: `ValueError` が発生
        with pytest.raises(ValueError, match="data-props属性の値が空です。"):
            Command.parse_data_props_to_dict(script_tag_with_data_props)

    def test_invalid_json(self):
        """
        スクリプトタグのdata-props属性が無効なJSON形式の場合のテスト。
        """
        # Given: 無効なJSONデータ（value が "" で囲まれていない）を含むスクリプトタグ
        html_content = """
        <script id="embedded-data" data-props='{"key": value}'></script>
        """
        script_tag_with_embedded_data = Command.find_script_tag_with_data_props(html_content)

        # When & Then: 無効なJSONの場合はjson.JSONDecodeErrorが発生
        with pytest.raises(json.JSONDecodeError):
            Command.parse_data_props_to_dict(script_tag_with_embedded_data)


class TestConvertUnixToDatetime:
    """
    convert_unix_to_datetime 関数のテストクラス。
    """

    def test_convert_unix_to_datetime(self):
        """
        Unixタイムスタンプを UTC の datetime に変換するテスト。
        """
        # Given: テスト用の Unix タイムスタンプ（2025-02-07 11:00:00 UTC）
        unix_time = 1738926000

        # When: メソッドを呼び出して結果を取得
        result_dt = Command.convert_unix_to_datetime(unix_time)

        # Then: 結果が期待される結果と一致することを確認
        expected_datetime = datetime(2025, 2, 7, 11, 0, 0, tzinfo=dt_timezone.utc)

        assert result_dt == expected_datetime


class TestCalculateDuration:
    """
    calculate_duration 関数のテストクラス。
    """

    def test_standard_duration(self):
        """
        時間、分、秒を含む場合のテスト。
        """
        # Given: 開始時間と終了時間のUnixタイムスタンプ
        start_time = 1738137600  # 2025-01-29 17:00:00 JST
        end_time = 1738142755  # 2025-01-29 18:25:55 JST

        # When: 関数を実行
        result = Command.calculate_duration(start_time, end_time)

        # Then: 期待する出力と一致
        expected_duration = "01:25:55"
        assert result == expected_duration

    def test_short_duration(self):
        """
        分、秒のみを含む短い場合のテスト。
        """
        # Given: 配信開始時間と終了時間のUnixタイムスタンプ
        start_time = 1738142755  # 2025-01-29 18:25:55 JST
        end_time = 1738143201  # 2025-01-29 18:33:21 JST

        # When: calculate_duration関数を実行
        result = Command.calculate_duration(start_time, end_time)

        # Then: 正しい配信時間が返される
        expected_duration = "00:07:26"
        assert result == expected_duration

    def test_exact_hour_duration(self):
        """
        ちょうど2時間の場合のテスト。
        """
        # Given: 2時間
        start_time = 1738141200  # 2025-01-29 18:00:00 JST
        end_time = 1738148400  # 2025-01-29 20:00:00 JST

        # When: 関数を実行
        result = Command.calculate_duration(start_time, end_time)

        # Then: 期待する出力と一致
        excepted_duration = "02:00:00"
        assert result == excepted_duration

    def test_no_duration(self):
        """
        配信開始時間と終了時間が同じ場合のテスト。
        """
        # Given: 配信開始時間と終了時間のUnixタイムスタンプが同じ
        start_time = 1738148400  # 2025-01-29 20:00:00 JST
        end_time = 1738148400  # 2025-01-29 20:00:00 JST

        # When: calculate_duration関数を実行
        result = Command.calculate_duration(start_time, end_time)

        # Then: 配信時間が "00:00:00" であることを確認
        expected_duration = "00:00:00"
        assert result == expected_duration

    def test_negative_duration(self):
        """
        `end_time` が `start_time` よりも前の場合、ValueError が発生することを確認。
        """
        # Given: 異常なデータ（開始時間が終了時間よりも後）
        start_time = 1700000100
        end_time = 1700000000  # 100秒前

        # When & Then: `ValueError` を発生させる
        with pytest.raises(ValueError, match="終了時間は開始時間より後である必要があります。"):
            Command.calculate_duration(start_time, end_time)


class TestExtractStreamingData:
    """
    extract_streaming_data 関数のテストクラス。
    """

    @pytest.fixture
    def valid_dict_data(self) -> dict:
        """入力となる配信データ（辞書型）を返すフィクスチャ"""
        return {
            "program": {
                "nicoliveProgramId": "lv346883570",
                "title": "ドライブ配信",
                "supplier": {"name": "3時サブ垢", "programProviderId": "52053485"},
                "beginTime": 1737936000,  # 2025-01-27 00:00:00 UTC
                "endTime": 1737950400,  # 2025-01-27 04:00:00 UTC
                "status": "ENDED",
            }
        }

    def test_valid_dict_data(self, valid_dict_data):
        """
        正常な辞書データを渡した場合に StreamingData オブジェクトが正しく生成されることを確認。
        """
        # Given: 正常な辞書データ（fixture で作成ずみ)

        # When: 関数を実行
        result = Command.extract_streaming_data(valid_dict_data)

        # Then: 期待する StreamingData オブジェクトが生成される
        expected_start_time = datetime(2025, 1, 27, 0, 0, 0, tzinfo=dt_timezone.utc)
        expected_end_time = datetime(2025, 1, 27, 4, 0, 0, tzinfo=dt_timezone.utc)

        assert isinstance(result, StreamingData)
        assert result.id == "346883570"  # "lv" が削除されている
        assert result.title == "ドライブ配信"
        assert result.start_time == expected_start_time  # 2025-01-27 00:00:00 UTC
        assert result.end_time == expected_end_time  # 2025-01-27 04:00:00 UTC
        assert result.duration_time == "04:00:00"
        assert result.status == "ENDED"
        assert result.streamer_id == "52053485"
        assert result.streamer_name == "3時サブ垢"

    @pytest.mark.parametrize(
        "missing_field",
        [
            ("nicoliveProgramId", "必須データが見つかりませんでした: nicoliveProgramId"),
            ("title", "必須データが見つかりませんでした: title"),
            ("beginTime", "必須データが見つかりませんでした: beginTime"),
            ("endTime", "必須データが見つかりませんでした: endTime"),
            ("status", "必須データが見つかりませんでした: status"),
            ("programProviderId", "必須データが見つかりませんでした: programProviderId"),
            ("name", "必須データが見つかりませんでした: name"),
        ],
    )
    def test_missing_required_fields(self, valid_dict_data, missing_field):
        """
        必須フィールドが欠落している場合に例外が発生することを確認。
        """
        # Given: 必須フィールドを削除
        field_name, expected_message = missing_field
        program_or_supplier = valid_dict_data["program"]

        # supplier の場合
        if field_name in ["programProviderId", "name"]:
            program_or_supplier = program_or_supplier["supplier"]

        # フィールドを削除
        del program_or_supplier[field_name]

        # When & Then: 例外が発生することを確認
        with pytest.raises(ValueError, match=expected_message):
            Command.extract_streaming_data(valid_dict_data)


@pytest.mark.django_db
class TestSaveOrGetStreamer:
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
class TestSaveOrUpdateStreaming:
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
class TestSaveStreamingData:
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

    @patch.object(Command, "save_or_get_streamer")
    @patch.object(Command, "save_or_update_streaming")
    def test_exception_handling(self, mock_save_or_update_streaming, mock_save_or_get_streamer):
        """
        例外が発生した場合にエラーメッセージが出力されることを確認
        """
        # Given: モックをセットアップして例外を発生させる
        mock_save_or_get_streamer.side_effect = Exception("DB error")

        # Given: 保存対象の配信データ
        streaming_data = StreamingData(
            id=67890,
            title="Test Streaming",
            start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status="ENDED",
            streamer_id=12345,
            streamer_name="Test Streamer",
        )

        # When & Then: `print` の出力をキャプチャしてエラーメッセージを確認
        with pytest.raises(Exception, match="DB error"):
            Command.save_streaming_data(streaming_data)
