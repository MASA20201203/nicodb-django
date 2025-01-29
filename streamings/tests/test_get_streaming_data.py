import json

import pytest
import requests
from bs4 import Tag
from requests_mock import Mocker

from streamings.services.get_streaming_data import (
    build_streaming_url,
    convert_unix_to_jst,
    fetch_html,
    find_script_tag_with_data_props,
    get_default_headers,
    parse_data_props_to_dict,
)


def test_build_streaming_url(monkeypatch) -> None:
    """
    build_streaming_url関数が配信IDから正しいURLを生成するかをテスト
    """
    # Given: 環境変数 "STREAMING_BASE_URL" が設定されており、配信IDが 123456789
    streaming_base_url = "https://live.nicovideo.jp/watch/lv"
    monkeypatch.setenv("STREAMING_BASE_URL", streaming_base_url)
    streaming_id = "123456789"

    # When: build_streaming_url 関数を呼び出す
    result = build_streaming_url(streaming_id)

    # Then: 正しい配信URL（https://live.nicovideo.jp/watch/lv123456789）が生成される
    excepted_streaming_url = "https://live.nicovideo.jp/watch/lv123456789"
    assert result == excepted_streaming_url


def test_get_default_headers() -> None:
    """
    get_default_headers関数が正しいヘッダーを返すかをテスト
    """
    # Given: なし

    # When: get_default_headers 関数を呼び出す
    result = get_default_headers()

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
        result = fetch_html(self.url, self.headers)

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
            fetch_html(self.url, self.headers)

    def test_request_exception(self, requests_mock: Mocker) -> None:
        """
        fetch_html関数がリクエスト例外を処理する場合のテスト
        """
        # Given: リクエスト例外をモック
        requests_mock.get(self.url, exc=requests.exceptions.ConnectionError("Connection refused"))

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: Connection refused"):
            fetch_html(self.url, self.headers)


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
        result = find_script_tag_with_data_props(valid_html)

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
        result = find_script_tag_with_data_props(multiple_script_tags_html)

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
            Exception, match="data_props属性を持つスクリプトタグが見つかりませんでした。"
        ):
            find_script_tag_with_data_props(invalid_html)


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
        script_tag_with_data_props = find_script_tag_with_data_props(html_content)

        # When: parse_data_props_to_dictを実行
        result = parse_data_props_to_dict(script_tag_with_data_props)

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
        script_tag_with_data_props = find_script_tag_with_data_props(html_content)

        # When & Then: `ValueError` が発生
        with pytest.raises(ValueError, match="data-props属性の値が空です。"):
            parse_data_props_to_dict(script_tag_with_data_props)

    def test_invalid_json(self) -> None:
        """
        スクリプトタグのdata-props属性が無効なJSON形式の場合のテスト。
        """
        # Given: 無効なJSONデータ（value が "" で囲まれていない）を含むスクリプトタグ
        html_content = """
        <script id="embedded-data" data-props='{"key": value}'></script>
        """
        script_tag_with_embedded_data = find_script_tag_with_data_props(html_content)

        # When & Then: 無効なJSONの場合はjson.JSONDecodeErrorが発生
        with pytest.raises(json.JSONDecodeError):
            parse_data_props_to_dict(script_tag_with_embedded_data)


class TestConvertUnixToJST:
    """
    convert_unix_to_jst 関数のテストクラス。
    """

    def test_valid_timestamp(self) -> None:
        """
        Unixタイムスタンプを日本時間に変換するテスト
        """
        # Given: 2025-01-29 06:00:00 UTC（JSTでは+9時間で15:00:00）
        unix_time = 1738130400

        # When: 関数を実行
        result = convert_unix_to_jst(unix_time)

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
        result = convert_unix_to_jst(unix_time)

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
        result = convert_unix_to_jst(unix_time)

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
        result = convert_unix_to_jst(unix_time)

        # Then: 期待するJSTの日時が返る
        assert result == expected_jst

    def test_leap_year(self) -> None:
        """
        閏年のUnixタイムスタンプを日本時間に変換するテスト。
        """
        # Given: 2028-02-29 00:00:00 UTC（JSTでは+9時間で09:00:00）
        unix_time = 1835395200

        # When: convert_unix_to_jst関数を実行
        result = convert_unix_to_jst(unix_time)

        # Then: 正しい日本時間の日時が返される
        expected_time = "2028-02-29 09:00:00"
        assert result == expected_time
