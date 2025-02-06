import json

import pytest
import requests
from bs4 import Tag
from django.conf import settings
from requests_mock import Mocker

from streamings.management.commands.get_streaming_data import Command, StreamingData


def test_build_streaming_url(monkeypatch) -> None:
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


def test_get_default_headers() -> None:
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
    def setup(self) -> None:
        """
        共通データのセットアップ。
        """
        self.url = "https://live.nicovideo.jp/watch/lv123456789"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
        }

    def test_success(self, requests_mock: Mocker) -> None:
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

    def test_http_error(self, requests_mock: Mocker) -> None:
        """
        fetch_html関数がHTTPエラーを処理する場合のテスト
        """
        # Given: HTTPエラーをモック
        requests_mock.get(self.url, status_code=403)

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: 403 Client Error"):
            Command.fetch_html(self.url, self.headers)

    def test_request_exception(self, requests_mock: Mocker) -> None:
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

    def test_success(self) -> None:
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

    def test_multiple_script_tags(self) -> None:
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

    def test_script_tag_not_found(self) -> None:
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

    def test_success(self) -> None:
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

    def test_empty_data_props(self) -> None:
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

    def test_invalid_json(self) -> None:
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


class TestConvertUnixToJST:
    """
    convert_unix_to_aware_datetime 関数のテストクラス。
    """

    def test_valid_timestamp(self) -> None:
        """
        Unixタイムスタンプを日本時間に変換するテスト
        """
        # Given: 2025-01-29 06:00:00 UTC（JSTでは+9時間で15:00:00）
        unix_time = 1738130400

        # When: 関数を実行
        result = Command.convert_unix_to_aware_datetime(unix_time)

        # Then: 期待するJSTの日時が返る
        expected_jst = "2025-01-29 15:00:00"
        assert result == expected_jst

    def test_zero_timestamp(self) -> None:
        """
        Unixタイムスタンプが `0`（1970-01-01 00:00:00 UTC）の場合、JSTの `1970-01-01 09:00:00` になることを確認。
        """
        # Given: Unix Epoch（1970-01-01 00:00:00 UTC）
        unix_time = 0

        # When: 関数を実行
        result = Command.convert_unix_to_aware_datetime(unix_time)

        # Then: JSTの09:00:00になる
        expected_jst = "1970-01-01 09:00:00"
        assert result == expected_jst

    def test_negative_timestamp(self) -> None:
        """
        負のUnixタイムスタンプ（1970年以前）を渡したときに正しくJSTに変換されることを確認。
        """
        # Given: 1969-12-31 00:00:00 UTC（JSTでは+9時間で09:00:00）
        unix_time = -86400  # 1日前（-1 * 60 * 60 * 24）

        # When: 関数を実行
        result = Command.convert_unix_to_aware_datetime(unix_time)

        # Then: JSTの08:00:00になる
        expected_jst = "1969-12-31 09:00:00"
        assert result == expected_jst

    def test_large_timestamp(self) -> None:
        """
        未来のUnixタイムスタンプ（2038年問題などの境界値 + 1秒）を渡したときに正しくJSTに変換されることを確認。
        """
        # Given: 2038-01-19 03:14:08 UTC（JSTでは+9時間で12:14:08）
        unix_time = 2147483648  # 2038年問題の境界値 + 1秒
        expected_jst = "2038-01-19 12:14:08"

        # When: 関数を実行
        result = Command.convert_unix_to_aware_datetime(unix_time)

        # Then: 期待するJSTの日時が返る
        assert result == expected_jst

    def test_leap_year(self) -> None:
        """
        閏年のUnixタイムスタンプを日本時間に変換するテスト。
        """
        # Given: 2028-02-29 00:00:00 UTC（JSTでは+9時間で09:00:00）
        unix_time = 1835395200

        # When: convert_unix_to_aware_datetime関数を実行
        result = Command.convert_unix_to_aware_datetime(unix_time)

        # Then: 正しい日本時間の日時が返される
        expected_time = "2028-02-29 09:00:00"
        assert result == expected_time


class TestCalculateDuration:
    """
    calculate_duration 関数のテストクラス。
    """

    def test_standard_duration(self) -> None:
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

    def test_short_duration(self) -> None:
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

    def test_exact_hour_duration(self) -> None:
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

    def test_no_duration(self) -> None:
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

    def test_negative_duration(self) -> None:
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
                "beginTime": 1737936000,
                "endTime": 1737950400,
                "status": "ENDED",
            }
        }

    def test_valid_dict_data(self, valid_dict_data) -> None:
        """
        正常な辞書データを渡した場合に StreamingData オブジェクトが正しく生成されることを確認。
        """
        # Given: 正常な辞書データ（fixture で作成ずみ)

        # When: 関数を実行
        result = Command.extract_streaming_data(valid_dict_data)

        # Then: 期待する StreamingData オブジェクトが生成される
        assert isinstance(result, StreamingData)
        assert result.id == "346883570"  # "lv" が削除されている
        assert result.title == "ドライブ配信"
        assert result.time_begin == "2025-01-27 09:00:00"
        assert result.time_end == "2025-01-27 13:00:00"
        assert result.time_duration == "04:00:00"
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
    def test_missing_required_fields(self, valid_dict_data, missing_field) -> None:
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
