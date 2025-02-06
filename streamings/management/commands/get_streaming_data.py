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

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.core.management.base import BaseCommand


@dataclass
class StreamingData:
    """
    配信データを格納するデータクラス。
    """

    id: str
    title: str
    time_begin: str
    time_end: str
    time_duration: str
    status: str
    streamer_id: str
    streamer_name: str


class Command(BaseCommand):
    help = "指定された配信IDを用いて配信データを取得する"

    def add_arguments(self, parser):  # pragma: no cover
        """
        コマンドライン引数を追加する
        """
        parser.add_argument("streaming_id", type=str, help="配信ID（例: 346883570）")

    def handle(self, *args, **options):
        """
        コマンドのメイン処理
        """
        try:
            streaming_id = options["streaming_id"]
            url = self.build_streaming_url(streaming_id)
            headers = self.get_default_headers()
            html_content = self.fetch_html(url, headers)
            script_tag_with_data_props = self.find_script_tag_with_data_props(html_content)
            data_props_dict = self.parse_data_props_to_dict(script_tag_with_data_props)
            extracted_streaming_data = self.extract_streaming_data(data_props_dict)
            self.print_streamng_data(extracted_streaming_data)
        except Exception as e:
            print(f"予期しないエラー: {e}")

    @classmethod
    def build_streaming_url(cls, streaming_id: str) -> str:
        """
        配信IDから配信URLを生成する。

        Args:
            streaming_id (str): 配信ID。

        Returns:
            streaming_url（str）: 配信URL。
        """
        # 環境変数からベースURLを取得
        streaming_base_url = settings.STREAMING_BASE_URL
        streaming_url = f"{streaming_base_url}{streaming_id}"
        return streaming_url

    @staticmethod
    def get_default_headers() -> dict:
        """
        デフォルトのリクエストヘッダーを返す。

        Returns:
            dict: ヘッダー情報。
        """
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
        }

    @staticmethod
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
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"HTTPリクエストエラー: {e}") from e

    @classmethod
    def find_script_tag_with_data_props(cls, html_content: str) -> Tag:
        """
        HTMLを解析し、data_props属性を持っているスクリプトタグを取得する。

        Args:
            html_content (str): 解析対象のHTMLデータ。

        Returns:
            Tag: data-props属性を含むスクリプトタグ。

        Raises:
            Exception: data_props属性を含むスクリプトタグが見つからなかった場合。
        """
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag_with_data_props = soup.find("script", attrs={"data-props": True})
        if not isinstance(script_tag_with_data_props, Tag):
            raise Exception("data_props属性を含むスクリプトタグが見つかりませんでした。")
        return script_tag_with_data_props

    @classmethod
    def parse_data_props_to_dict(cls, script_tag_with_embedded_data: Tag) -> dict:
        """
        スクリプトタグのdata-props属性の値をパース（json -> dict に変換）して、Pythonで扱えるようにする。

        Args:
            script_tag_with_embedded_data (Tag): data-props属性を含むスクリプトタグ。

        Returns:
            dict: 辞書型にパースされたJSONデータ。

        Raises:
            Exception: data-props属性の値が空の場合。
        """
        data_props = str(script_tag_with_embedded_data["data-props"])
        if data_props.strip() == "":
            raise ValueError("data-props属性の値が空です。")

        try:
            data_props_dict = json.loads(data_props)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"data-props属性のJSONデコードに失敗しました: {e.msg}", e.doc, e.pos
            ) from e

        return data_props_dict

    @staticmethod
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

    @staticmethod
    def calculate_duration(start_time: int, end_time: int) -> str:
        """
        配信開始時間と終了時間の差を計算し、配信時間を取得する。

        Args:
            start_time (int): 配信開始時間のUnixタイムスタンプ。
            end_time (int): 配信終了時間のUnixタイムスタンプ。

        Returns:
            str: 配信時間（例: "HH:MM:SS"）。
        """
        if end_time < start_time:
            raise ValueError("終了時間は開始時間より後である必要があります。")

        duration_seconds = end_time - start_time
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    @classmethod
    def extract_streaming_data(cls, json_data: dict) -> StreamingData:
        """
        JSONデータから配信情報を抽出する。

        Args:
            json_data (dict): 抽出対象のJSONデータ。

        Returns:
            StreamingData: 配信情報（タイトル、配信者名、配信IDなど）。

        Raises:
            Exception: 必須データが見つからなかった場合。
        """

        try:
            program = json_data["program"]
            supplier = program["supplier"]

            streaming_data = {
                "id": program["nicoliveProgramId"].removeprefix("lv"),
                "title": program["title"],
                "time_begin": program["beginTime"],
                "time_end": program["endTime"],
                "status": program["status"],
                "streamer_id": supplier["programProviderId"],
                "streamer_name": supplier["name"],
            }
        except KeyError as e:
            raise ValueError(f"必須データが見つかりませんでした: {e.args[0]}") from e

        # UnixタイムスタンプをJSTに変換
        streaming_data["time_begin"] = cls.convert_unix_to_jst(streaming_data["time_begin"])
        streaming_data["time_end"] = cls.convert_unix_to_jst(streaming_data["time_end"])

        # 配信時間を計算
        streaming_data["time_duration"] = cls.calculate_duration(
            program["beginTime"], program["endTime"]
        )

        return StreamingData(**streaming_data)

    @classmethod
    def print_streamng_data(
        cls, extracted_streaming_data: StreamingData
    ) -> None:  # pragma: no cover
        """
        抽出した配信データを表示する。

        Args:
            extracted_streaming_data (StreamingData): 抽出した配信データ。
        """
        for key, value in extracted_streaming_data.__dict__.items():
            print(f"{key}: {value}")
