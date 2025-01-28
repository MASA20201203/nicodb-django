import os
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from streamings.services.get_streaming_data import (
    build_url,
    extract_data_props,
    fetch_html,
    get_default_headers,
    parse_html,
)

load_dotenv()


def test_build_url():
    """
    build_url関数が正しいURLを生成するかをテスト
    """
    # Given 配信IDが 123456789 であり、環境変数 STREAMING_URL が設定されており、
    streaming_id = 123456789
    streaming_url = os.getenv("STREAMING_URL")

    # When build_url 関数を呼び出した時、
    url = build_url(streaming_id, streaming_url)

    # Then 正しいURL "https://live.nicovideo.jp/watch/123456789" が生成される。
    assert url == "https://live.nicovideo.jp/watch/lv123456789"


def test_get_default_headers():
    """
    get_default_headers関数がデフォルトのリクエストヘッダーを返すかをテスト
    """
    # When get_default_headers 関数を呼び出した時、
    headers = get_default_headers()

    # Then ヘッダーに "User-Agent" が含まれる。
    assert "User-Agent" in headers


@patch("get_streaming_data.requests.get")
def test_fetch_html(mock_get):
    """
    fetch_html関数が正しいHTMLデータを取得するかをテスト
    """
    # Given: URLが "https://live.nicovideo.jp/watch/lv123456789"、
    #        レスポンスがステータス200とHTML "<html><body>Test</body></html>"
    url = "https://live.nicovideo.jp/watch/lv123456789"
    headers = {"User-Agent": "test"}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test</body></html>"
    mock_get.return_value = mock_response

    # When: fetch_html 関数を呼び出した時、
    html_content = fetch_html(url, headers)

    # Then: HTMLデータ "<html><body>Test</body></html>" が返される
    assert html_content == "<html><body>Test</body></html>"
    mock_get.assert_called_once_with(url, headers=headers, timeout=10)


def test_parse_html():
    """
    parse_html関数が特定のスクリプトタグを正しく取得するかをテスト。
    """
    # Given: HTMLにスクリプトタグを含むデータ
    html_content = """
    <html>
        <script id="embedded-data" data-props='{&quot;akashic&quot;:'></script>
    </html>
    """

    # When: parse_html 関数を呼び出す
    result = parse_html(html_content)

    # Then: スクリプトタグが正しく取得され、data-props属性に '{"key": "value"}' を持つ
    assert result.get("data-props") == "{&quot;akashic&quot;:"


def test_extract_data_props():
    """
    extract_data_props関数がJSONデータを正しく抽出するかをテスト。
    """
    # Given: スクリプトタグに data-props 属性 '{&quot;akashic&quot;:' を含む
    from bs4 import Tag

    mock_tag = MagicMock(spec=Tag)
    mock_tag.get.return_value = "{&quot;akashic&quot;:"

    # When: extract_data_props 関数を呼び出す
    result = extract_data_props(mock_tag)

    # Then: 正しいJSONデータ {"key": "value"} が返される
    assert result == {"key": "value"}
