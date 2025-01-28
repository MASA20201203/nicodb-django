"""
配信データを取得・抽出し、表示するスクリプト。

このスクリプトは以下の手順で処理を行います:
1. 引数で指定された配信IDをもとにURLを生成。
2. 指定されたURLからHTMLデータを取得。
3. HTMLを解析して、特定のスクリプトタグを抽出。
4. 抽出したスクリプトタグ内のdata-props属性をデコードしてJSONデータを取得。
5. JSONデータから配信情報を抽出し、表示。

使用例:
    python get_streaming_data.py 346883570

依存関係:
    - requests
    - BeautifulSoup

エラー処理:
    - スクリプトは、ステータスコードが200でない場合や、特定の要素が見つからない場合に例外をスローします。
"""

import argparse
import html
import json
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup, Tag


def main():
    """
    配信データを取得し、配信情報を表示するメイン処理。
    """
    # 引数をパース
    args = parse_args()

    # 配信IDを使ってURLを生成
    streaming_id = args.streaming_id
    url = f"https://live.nicovideo.jp/watch/lv{streaming_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # 処理の流れ
        html_content = fetch_html(url, headers)  # データ取得
        script_tag = parse_html(html_content)  # HTML解析
        json_data = extract_data_props(script_tag)  # JSON解析
        program_info = extract_streaming_data(json_data)  # 配信情報抽出

        # 結果を出力
        for key, value in program_info.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"エラー: {e}")


def parse_args() -> argparse.Namespace:
    """
    コマンドライン引数を解析する。

    Returns:
        argparse.Namespace: コマンドライン引数の結果。
    """
    parser = argparse.ArgumentParser(description="配信データを取得するスクリプト")
    parser.add_argument(
        "streaming_id",
        type=str,
        help="配信ID（例: 346883570）",
    )
    return parser.parse_args()


def fetch_html(url: str, headers: dict) -> str:
    """
    指定されたURLからHTMLデータを取得する。

    Args:
        url (str): HTMLデータを取得する対象のURL。
        headers (dict): リクエストヘッダー。

    Returns:
        str: 取得したHTMLデータ。

    Raises:
        Exception: HTTPステータスコードが200以外の場合。
    """
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"{response.status_code}: データを取得できませんでした。")


def parse_html(html_content: str) -> Tag:
    """
    HTMLを解析し、特定のスクリプトタグを取得する。

    Args:
        html_content (str): 解析対象のHTMLデータ。

    Returns:
        Tag: data-props属性を含むスクリプトタグ。

    Raises:
        Exception: 対象のスクリプトタグが見つからなかった場合。
    """
    soup = BeautifulSoup(html_content, "html.parser")
    script_tag = soup.find("script", id="embedded-data")
    if not isinstance(script_tag, Tag):
        raise Exception("指定されたスクリプトタグ（embedded-data）が見つかりませんでした。")
    return script_tag


def extract_data_props(script_tag: Tag) -> dict:
    """
    スクリプトタグのdata-props属性をデコードし、JSONデータを取得する。

    Args:
        script_tag (Tag): data-props属性を含むスクリプトタグ。

    Returns:
        dict: デコードされたJSONデータ。

    Raises:
        Exception: data-props属性が見つからなかった場合。
    """
    raw_data = script_tag.get("data-props")
    if raw_data is None:
        raise Exception("data-props属性が見つかりませんでした。")
    decoded_data = html.unescape(str(raw_data))
    return json.loads(decoded_data)


def convert_unix_to_jst(unix_time: int) -> str:
    """
    Unixタイムスタンプを日本時間に変換する。

    Args:
        unix_time (int): Unixタイムスタンプ。

    Returns:
        str: 日本時間の日時（例: 2025-01-28 12:00:00）。
    """
    # タイムゾーンを日本時間（UTC+9）に設定
    jst = timezone(timedelta(hours=9))
    # Unixタイムスタンプを日本時間に変換
    dt = datetime.fromtimestamp(unix_time, jst)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def calculate_duration(start_time: int, end_time: int) -> str:
    """
    配信開始時間と終了時間の差を計算し、配信時間を取得する。

    Args:
        start_time (int): 配信開始時間のUnixタイムスタンプ。
        end_time (int): 配信終了時間のUnixタイムスタンプ。

    Returns:
        str: 配信時間（例: "HH:MM:SS"）。
    """
    duration_seconds = end_time - start_time
    duration = str(timedelta(seconds=duration_seconds))
    return duration


def extract_streaming_data(json_data: dict) -> dict:
    """
    JSONデータから配信情報を抽出する。

    Args:
        json_data (dict): 抽出対象のJSONデータ。

    Returns:
        dict: 配信情報（タイトル、配信者名、配信IDなど）。

    Raises:
        Exception: 必須データが見つからなかった場合。
    """
    program = json_data.get("program", {})
    supplier = program.get("supplier", {})

    streaming_id = program.get("nicoliveProgramId")
    streaming_title = program.get("title")
    streamer_id = supplier.get("programProviderId")
    streamer_name = supplier.get("name")
    streaming_time_begin = program.get("beginTime")
    streaming_time_end = program.get("endTime")
    streaming_status = program.get("status")

    # 必須データが不足している場合は例外をスロー
    if not streaming_id:
        raise Exception("配信IDが見つかりませんでした。")
    if not streaming_title:
        raise Exception("配信タイトルが見つかりませんでした。")
    if not streamer_id:
        raise Exception("配信者IDが見つかりませんでした。")
    if not streamer_name:
        raise Exception("配信者名が見つかりませんでした。")
    if streaming_time_begin is None:
        raise Exception("配信開始時間が見つかりませんでした。")
    if streaming_time_end is None:
        raise Exception("配信終了時間が見つかりませんでした。")
    if not streaming_status:
        raise Exception("配信終了ステータスが見つかりませんでした。")

    # 配信IDから "lv" を取り除く
    streaming_id = streaming_id.removeprefix("lv")

    # Unixタイムスタンプを日本標準時（JST）に変換
    streaming_time_begin_jst = convert_unix_to_jst(streaming_time_begin)
    streaming_time_end_jst = convert_unix_to_jst(streaming_time_end)

    # 配信時間を計算
    streaming_time_duration = calculate_duration(streaming_time_begin, streaming_time_end)

    # データを辞書型で返す
    return {
        "streaming_id": streaming_id,
        "streaming_title": streaming_title,
        "streamer_id": streamer_id,
        "streamer_name": streamer_name,
        "streaming_time_begin": streaming_time_begin_jst,
        "streaming_time_end": streaming_time_end_jst,
        "streaming_time_duration": streaming_time_duration,
        "streaming_status": streaming_status,
    }


if __name__ == "__main__":
    main()
