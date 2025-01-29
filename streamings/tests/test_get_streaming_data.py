import json

import pytest
import requests
from bs4 import Tag
from requests_mock import Mocker

from streamings.services.get_streaming_data import (
    build_streaming_url,
    extract_data_props_to_json,
    fetch_html,
    find_script_tag_with_embedded_data,
    get_default_headers,
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
    streaming_url = build_streaming_url(streaming_id)

    # Then: 正しい配信URL（https://live.nicovideo.jp/watch/lv123456789）が生成される
    assert streaming_url == "https://live.nicovideo.jp/watch/lv123456789"


def test_get_default_headers() -> None:
    """
    get_default_headers関数が正しいヘッダーを返すかをテスト
    """
    # Given: 期待されるヘッダー情報
    expected_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
    }

    # When: get_default_headers 関数を呼び出す
    headers = get_default_headers()

    # Then: 期待されるヘッダー情報が返される
    assert headers == expected_headers


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
        self.expected_html = "<html><body><h1>Test Page</h1></body></html>"

    def test_success(self, requests_mock: Mocker) -> None:
        """
        fetch_html関数が正常にHTMLデータを取得する場合のテスト
        """
        # Given: 正常なレスポンスをモック
        requests_mock.get(self.url, text=self.expected_html, status_code=200)

        # When: fetch_html関数を呼び出す
        response_text = fetch_html(self.url, self.headers)

        # Then: 正しいHTMLデータが返される
        assert response_text == self.expected_html

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


class TestFindScriptTagWithEmbeddedData:
    """
    find_script_tag_with_embedded_data 関数のテストクラス。
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

        # When: find_script_tag_with_embedded_data関数を実行
        script_tag = find_script_tag_with_embedded_data(valid_html)

        # Then: 戻り値がTagオブジェクトで、正しい属性を持つ
        assert isinstance(script_tag, Tag)
        assert script_tag["id"] == "embedded-data"
        assert script_tag["data-props"] == '{"akashic":{'

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

        # When: find_script_tag_with_embedded_data関数を実行
        script_tag = find_script_tag_with_embedded_data(multiple_script_tags_html)

        # Then: 取得したスクリプトタグのid属性が"embedded-data"であることを確認
        assert script_tag["id"] == "embedded-data"

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
            Exception, match='id="embedded-data"属性を持つスクリプトタグが見つかりませんでした。'
        ):
            find_script_tag_with_embedded_data(invalid_html)


class TestExtractDataPropsToJson:
    """
    extract_data_props_to_json 関数のテストクラス。
    """

    def test_success(self) -> None:
        """
        スクリプトタグのdata-props属性が正常なJSON形式で取得できる場合のテスト。
        """
        # Given: 正常なHTML
        html_content = """
        <script id="embedded-data" data-props='{"key": "value"}'></script>
        """
        script_tag_with_embedded_data = find_script_tag_with_embedded_data(html_content)

        # When: extract_data_props_to_jsonを実行
        result = extract_data_props_to_json(script_tag_with_embedded_data)

        # Then: 正しいJSONデータが辞書型で返される
        assert isinstance(result, dict)
        assert result == {"key": "value"}

    def test_missing_data_props(self) -> None:
        """
        スクリプトタグのdata-props属性が存在しない場合のテスト。
        """
        # Given: data-props属性がないHTML
        html_content = """
        <script id="embedded-data"></script>
        """
        script_tag_with_embedded_data = find_script_tag_with_embedded_data(html_content)

        # When & Then: data-propsがない場合はExceptionが発生
        with pytest.raises(ValueError, match="data-props属性が不正です。"):
            extract_data_props_to_json(script_tag_with_embedded_data)

    def test_empty_data_props(self) -> None:
        """
        `data-props` が空文字の場合、ValueError が発生することを確認。
        """
        # Given: `data-props=""` のスクリプトタグ
        html_content = """
        <script id="embedded-data" data-props=""></script>
        """
        script_tag_with_embedded_data = find_script_tag_with_embedded_data(html_content)

        # When & Then: `ValueError` が発生
        with pytest.raises(ValueError, match="data-props属性が不正です。"):
            extract_data_props_to_json(script_tag_with_embedded_data)

        # When & Then: `ValueError` が発生
        with pytest.raises(ValueError, match="data-props属性が不正です。"):
            extract_data_props_to_json(script_tag_with_embedded_data)

    def test_invalid_json(self) -> None:
        """
        スクリプトタグのdata-props属性が無効なJSON形式の場合のテスト。
        """
        # Given: 無効なJSONデータを含むHTML（value が "" で囲まれていない）
        html_content = """
        <script id="embedded-data" data-props='{"key": value}'></script>
        """
        script_tag_with_embedded_data = find_script_tag_with_embedded_data(html_content)

        # When & Then: 無効なJSONの場合はjson.JSONDecodeErrorが発生
        with pytest.raises(json.JSONDecodeError):
            extract_data_props_to_json(script_tag_with_embedded_data)
