import pytest
import requests
from requests_mock import Mocker

from streamings.services.get_streaming_data import (
    build_url,
    fetch_html,
    get_default_headers,
)


def test_build_url(monkeypatch) -> None:
    """
    build_url関数が配信IDから正しいURLを生成するかをテスト。
    """
    # Given: 環境変数 "STREAMING_BASE_URL" が設定されており、配信IDが 123456789
    streaming_base_url = "https://live.nicovideo.jp/watch/lv"
    monkeypatch.setenv("STREAMING_BASE_URL", streaming_base_url)
    streaming_id = "123456789"

    # When: build_url 関数を呼び出す
    streaming_url = build_url(streaming_id)

    # Then: 正しい配信URL（https://live.nicovideo.jp/watch/lv123456789）が生成される
    assert streaming_url == "https://live.nicovideo.jp/watch/lv123456789"


def test_get_default_headers() -> None:
    """
    get_default_headers関数が正しいヘッダーを返すかをテスト。
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
        fetch_html関数が正常にHTMLデータを取得する場合のテスト。
        """
        # Given: 正常なレスポンスをモック
        requests_mock.get(self.url, text=self.expected_html, status_code=200)

        # When: fetch_html関数を呼び出す
        response_text = fetch_html(self.url, self.headers)

        # Then: 正しいHTMLデータが返される
        assert response_text == self.expected_html

    def test_http_error(self, requests_mock: Mocker) -> None:
        """
        fetch_html関数がHTTPエラーを処理する場合のテスト。
        """
        # Given: HTTPエラーをモック
        requests_mock.get(self.url, status_code=403)

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: 403 Client Error"):
            fetch_html(self.url, self.headers)

    def test_request_exception(self, requests_mock: Mocker) -> None:
        """
        fetch_html関数がリクエスト例外を処理する場合のテスト。
        """
        # Given: リクエスト例外をモック
        requests_mock.get(self.url, exc=requests.exceptions.ConnectionError("Connection refused"))

        # When & Then: fetch_html関数が例外を投げることを確認
        with pytest.raises(Exception, match="HTTPリクエストエラー: Connection refused"):
            fetch_html(self.url, self.headers)
