import json
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
import requests
from bs4 import Tag
from django.conf import settings

from streamings.management.commands.get_streaming_data import (
    Command,
    StreamingData,
    StreamingStatus,
)


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


class TestConvertStreamingStatusToCode:
    """
    Command クラスの convert_streaming_status_to_code メソッドのテストクラス。
    """

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("RESERVED", StreamingStatus.RESERVED.value),
            ("ON_AIR", StreamingStatus.ON_AIR.value),
            ("ENDED", StreamingStatus.ENDED.value),
        ],
    )
    def test_valid_status(self, status, expected):
        """
        正しい配信ステータスが適切なコードに変換されることを確認する。
        """
        # When: convert_status_to_code を実行
        result = Command.convert_streaming_status_to_code(status)

        # Then: 期待するステータスコードが返る
        assert result == expected

    def test_invalid_status(self):
        """
        未知の配信ステータスが渡された場合に ValueError が発生することを確認する。
        """
        # Given: 存在しないステータス
        invalid_status = "UNKNOWN_STATUS"

        # When & Then: ValueError が発生することを確認
        with pytest.raises(ValueError, match=f"未知の配信ステータス: {invalid_status}"):
            Command.convert_streaming_status_to_code(invalid_status)


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
        assert result.status == StreamingStatus.ENDED.value
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


class TestSaveStreamingData:
    """
    Command クラスの save_streaming_data メソッドの例外テスト
    """

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


class TestHandleCommand:
    """
    Command クラスの handle メソッドのテストクラス。
    """

    @patch.object(Command, "build_streaming_url")
    @patch.object(Command, "get_default_headers")
    @patch.object(Command, "fetch_html")
    @patch.object(Command, "find_script_tag_with_data_props")
    @patch.object(Command, "parse_data_props_to_dict")
    @patch.object(Command, "extract_streaming_data")
    @patch.object(Command, "save_streaming_data")
    def test_handle_success(
        self,
        mock_save_streaming_data,
        mock_extract_streaming_data,
        mock_parse_data_props_to_dict,
        mock_find_script_tag_with_data_props,
        mock_fetch_html,
        mock_get_default_headers,
        mock_build_streaming_url,
    ):
        """
        handle メソッドが正常に動作する場合のテスト。
        """
        # Given: モックの設定
        options = {"streaming_id": "123456789"}
        mock_build_streaming_url.return_value = "https://live.nicovideo.jp/watch/lv123456789"
        mock_get_default_headers.return_value = {"User-Agent": "test-agent"}
        mock_fetch_html.return_value = "<html><body><script id='embedded-data' data-props='{\"key\": \"value\"}'></script></body></html>"
        mock_find_script_tag_with_data_props.return_value = (
            "<script id='embedded-data' data-props='{\"key\": \"value\"}'></script>"
        )
        mock_parse_data_props_to_dict.return_value = {
            "program": {
                "nicoliveProgramId": "lv123456789",
                "title": "Test Streaming",
                "supplier": {"name": "Test Streamer", "programProviderId": "12345"},
                "beginTime": 1738926000,
                "endTime": 1738933200,
                "status": "ENDED",
            }
        }
        mock_extract_streaming_data.return_value = StreamingData(
            id="123456789",
            title="Test Streaming",
            start_time=datetime(2025, 2, 7, 15, 0, 0, tzinfo=dt_timezone.utc),
            end_time=datetime(2025, 2, 7, 17, 0, 0, tzinfo=dt_timezone.utc),
            duration_time=timedelta(hours=2),
            status=StreamingStatus.ENDED.value,
            streamer_id="12345",
            streamer_name="Test Streamer",
        )

        # When: handle メソッドを呼び出す
        command = Command()
        command.handle(**options)

        # Then: 各メソッドが正しく呼び出されることを確認
        mock_build_streaming_url.assert_called_once_with("123456789")
        mock_get_default_headers.assert_called_once()
        mock_fetch_html.assert_called_once_with(
            "https://live.nicovideo.jp/watch/lv123456789", {"User-Agent": "test-agent"}
        )
        mock_find_script_tag_with_data_props.assert_called_once_with(
            "<html><body><script id='embedded-data' data-props='{\"key\": \"value\"}'></script></body></html>"
        )
        mock_parse_data_props_to_dict.assert_called_once_with(
            "<script id='embedded-data' data-props='{\"key\": \"value\"}'></script>"
        )
        mock_extract_streaming_data.assert_called_once_with(
            {
                "program": {
                    "nicoliveProgramId": "lv123456789",
                    "title": "Test Streaming",
                    "supplier": {"name": "Test Streamer", "programProviderId": "12345"},
                    "beginTime": 1738926000,
                    "endTime": 1738933200,
                    "status": "ENDED",
                }
            }
        )
        mock_save_streaming_data.assert_called_once_with(mock_extract_streaming_data.return_value)

    @patch.object(Command, "fetch_html")
    def test_handle_exception(self, mock_fetch_html):
        """
        handle メソッドが例外を正しく処理する場合のテスト。
        """
        # Given: モックの設定
        options = {"streaming_id": "123456789"}
        mock_fetch_html.side_effect = Exception("ネットワークエラー")

        # When & Then: handle メソッドが例外を発生させることを確認
        with pytest.raises(Exception, match="予期せぬエラー: ネットワークエラー"):
            command = Command()
            command.handle(**options)
