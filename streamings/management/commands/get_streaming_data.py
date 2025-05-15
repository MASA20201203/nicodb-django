"""
配信データを取得・抽出し、DBに保存するコマンド。

このスクリプトは以下の手順で処理を行います:
1. 引数で指定された配信IDをもとにURLを生成。
2. 指定されたURLからHTMLデータを取得。
3. HTMLを解析して、特定のスクリプトタグを抽出。
4. 抽出したスクリプトタグ内のdata-props属性のJSONデータをデコードしてを辞書型データに変換。
5. 辞書型データから必要な配信データを抽出
6. 配信者情報を保存または取得
7. 配信データを保存または更新

使用例:
    python manage.py get_streaming_data 346883570

依存関係:
    - requests
    - BeautifulSoup

エラー処理:
    - スクリプトは、ステータスコードが200でない場合や、特定の要素が見つからない場合に例外をスローします。
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from streamings.constants import StreamingStatus, StreamingType
from streamings.models import Channel, Streamer, Streaming

logger = logging.getLogger("streamings")


@dataclass
class StreamingData:
    """
    配信データを格納するデータクラス。
    """

    id: int
    type: int
    title: str
    start_time: datetime
    end_time: datetime
    duration_time: timedelta
    status: int
    streamer_id: int
    streamer_name: str
    channel_id: int
    channel_name: str
    company_name: str


class Command(BaseCommand):
    help = "指定された配信IDを用いて配信データを取得する"

    def add_arguments(self, parser: CommandParser) -> None:  # pragma: no cover
        """
        コマンドライン引数を追加する

        Args:
            parser (CommandParser): コマンドライン引数を解析するためのパーサー
        """
        parser.add_argument("streaming_id", type=str, help="配信ID（例: 346883570）")

    def handle(self, **options: dict[str, Any]) -> None:
        """
        コマンドのメイン処理。
        配信データを取得し、データベースに保存する。

        Args:
            options (dict[str, Any]): コマンドライン引数（streaming_id など）。
        """
        try:
            streaming_id = str(options["streaming_id"])
            logger.info(f"START 配信データ取得を開始: 配信ID={streaming_id}")
            url = self.build_streaming_url(streaming_id)
            headers = self.get_default_headers()
            html_content = self.fetch_html(url, headers)
            if not html_content:
                logger.info(f"END   配信ページが見つかりませんでした: 配信ID={streaming_id}")
                return
            script_tag_with_data_props = self.find_script_tag_with_data_props(html_content)
            data_props_dict = self.parse_data_props_to_dict(script_tag_with_data_props)
            extracted_streaming_data = self.extract_streaming_data(data_props_dict)
            self.save_streaming_data(extracted_streaming_data)
            logger.info(f"END   配信データを正常に保存しました: 配信ID={streaming_id}")
        except Exception as e:
            logger.error(f"予期せぬエラー: {e}", exc_info=True)
            raise Exception(f"予期せぬエラー: {e}") from e

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
    def extract_streaming_id(url: str) -> int:
        """
        配信URLから配信IDを抽出する。

        Args:
            url (str): 配信ページのURL。

        Returns:
            int: 配信ID。

        Raises:
            ValueError: URL に配信IDが含まれていない場合。
        """
        match = re.search(r"lv(\d+)", url)  # "lv" の後に数字がある部分を抽出
        if not match:
            raise ValueError(f"URLから配信IDを取得できませんでした: {url}")
        return int(match.group(1))  # 抽出した ID を整数に変換

    @classmethod
    def save_streaming_with_http_error(cls, status_code: int, streaming_id: int) -> None:
        """
        HTTPステータスコードが200以外の場合、配信IDとHTTPステータスコードを設定して、DBに保存する

        Args:
            status_code (int): HTTPステータスコード。
            streaming_id (int): 取得できなかった配信ID。
        """
        streaming_data = StreamingData(
            id=streaming_id,
            type=StreamingType.UNKNOWN.value,
            title=settings.UNKNOWN_STREAMING_TITLE,
            start_time=datetime(2007, 12, 25, tzinfo=timezone.utc),
            end_time=datetime(2007, 12, 25, tzinfo=timezone.utc),
            duration_time=timedelta(0),
            status=status_code,
            streamer_id=settings.UNKNOWN_STREAMER_ID,
            streamer_name=settings.UNKNOWN_STREAMER_NAME,
            channel_id=settings.UNKNOWN_CHANNEL_ID,
            channel_name=settings.UNKNOWN_CHANNEL_NAME,
            company_name=settings.UNKNOWN_COMPANY_NAME,
        )
        cls.save_streaming_data(streaming_data)

    @classmethod
    def fetch_html(cls, url: str, headers: dict) -> str | None:
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
            if response.status_code == 200:
                return response.text
            else:
                streaming_id = cls.extract_streaming_id(url)
                cls.save_streaming_with_http_error(response.status_code, streaming_id)
                return None
        except requests.RequestException as e:
            logging.error(f"HTTPリクエストエラー: {e}", exc_info=True)
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
            logging.error("data_props属性を含むスクリプトタグが見つかりませんでした。")
            raise Exception("data_props属性を含むスクリプトタグが見つかりませんでした。")
        return script_tag_with_data_props

    @classmethod
    def parse_data_props_to_dict(cls, script_tag_with_data_props: Tag) -> dict:
        """
        スクリプトタグのdata-props属性の値をパース（json -> dict に変換）して、Pythonで扱えるようにする。

        Args:
            script_tag_with_data_props (Tag): data-props属性を含むスクリプトタグ。

        Returns:
            dict: 辞書型にパースされたJSONデータ。

        Raises:
            Exception: data-props属性の値が空の場合。
        """
        data_props = str(script_tag_with_data_props["data-props"])
        if data_props.strip() == "":
            logging.error("data-props属性の値が空です。")
            raise ValueError("data-props属性の値が空です。")

        try:
            data_props_dict = json.loads(data_props)
        except json.JSONDecodeError as e:
            logging.error(f"data-props属性のJSONデコードに失敗しました: {e.msg}", exc_info=True)
            raise json.JSONDecodeError(
                f"data-props属性のJSONデコードに失敗しました: {e.msg}", e.doc, e.pos
            ) from e

        return data_props_dict

    @staticmethod
    def convert_unix_to_datetime(unix_time: int) -> datetime:
        """
        Unixタイムスタンプを UTC の datetime に変換する。

        Args:
            unix_time (int): Unixタイムスタンプ。

        Returns:
            datetime: タイムゾーン付きの `aware datetime`（UTC）。
        """
        # Unixタイムスタンプを UTC の datetime に変換して返す
        return datetime.fromtimestamp(unix_time, timezone.utc)

    @classmethod
    def convert_streaming_status_to_code(cls, status: str) -> int:
        """
        配信ステータスをコードに変換する。

        Args:
            status (str): 配信ステータス (例: "RESERVED", "ON_AIR", "ENDED")

        Returns:
            int: 変換後のステータスコード

        Raises:
            ValueError: 未知のステータスが渡された場合
        """
        try:
            return StreamingStatus[status].value
        except KeyError as e:
            logging.error(f"未知の配信ステータス: {status}")
            raise ValueError(f"未知の配信ステータス: {status}") from e

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
            logging.error("終了時間は開始時間より後である必要があります。")
            raise ValueError("終了時間は開始時間より後である必要があります。")

        duration_seconds = end_time - start_time
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    @classmethod
    def extract_streaming_data(cls, data_props_dict: dict) -> StreamingData:
        """
        data_props から配信データを抽出する。

        Args:
            json_data (dict): 抽出対象のJSONデータ。

        Returns:
            StreamingData: 配信データ（タイトル、配信者名、配信IDなど）。

        Raises:
            Exception: 必須データが見つからなかった場合。
        """

        try:
            program = data_props_dict["program"]
            supplier = program.get("supplier", {})
            provider_type = program["providerType"]

            # 共通項目のセット
            common_data = {
                "id": program["nicoliveProgramId"].removeprefix("lv"),
                "title": program["title"],
                "start_time": cls.convert_unix_to_datetime(program["beginTime"]),
                "end_time": cls.convert_unix_to_datetime(program["endTime"]),
                "status": cls.convert_streaming_status_to_code(program["status"]),
            }

            # `providerType` に基づく設定
            if provider_type == "community":
                provider_data = {
                    "type": StreamingType.USER.value,
                    "streamer_id": supplier.get("programProviderId", settings.UNKNOWN_STREAMER_ID),
                    "streamer_name": supplier.get("name", settings.UNKNOWN_STREAMER_NAME),
                    "channel_id": settings.UNKNOWN_CHANNEL_ID,
                    "channel_name": settings.UNKNOWN_CHANNEL_NAME,
                    "company_name": settings.UNKNOWN_COMPANY_NAME,
                }
            elif provider_type == "channel":
                provider_data = {
                    "type": StreamingType.CHANNEL.value,
                    "streamer_id": settings.UNKNOWN_STREAMER_ID,
                    "streamer_name": settings.UNKNOWN_STREAMER_NAME,
                    "channel_id": data_props_dict["socialGroup"]["id"].removeprefix("ch"),
                    "channel_name": data_props_dict["socialGroup"]["name"],
                    "company_name": data_props_dict["socialGroup"]["companyName"],
                }
            elif provider_type == "official":
                provider_data = {
                    "type": StreamingType.COMPANY.value,
                    "streamer_id": settings.UNKNOWN_STREAMER_ID,
                    "streamer_name": settings.UNKNOWN_STREAMER_NAME,
                    "channel_id": data_props_dict["socialGroup"]["id"].removeprefix("ch"),
                    "channel_name": data_props_dict["socialGroup"]["name"],
                    "company_name": data_props_dict["socialGroup"]["companyName"],
                }
            else:
                logging.error(
                    f"未知の配信タイプです: 配信ID={common_data['id']}, タイプ={provider_type}"
                )
                raise ValueError(
                    f"未知の配信タイプです: 配信ID={common_data['id']}, タイプ={provider_type}"
                )
            # `common_data` に `provider_mapping` をマージ
            streaming_data = {**common_data, **provider_data}

        except KeyError as e:
            logging.error(f"必須データが見つかりませんでした: {e.args[0]}", exc_info=True)
            raise ValueError(f"必須データが見つかりませんでした: {e.args[0]}") from e

        # 配信時間を算出
        streaming_data["duration_time"] = cls.calculate_duration(
            program["beginTime"], program["endTime"]
        )

        return StreamingData(**streaming_data)

    @classmethod
    def save_or_get_streamer(cls, streamer_id: int, streamer_name: str) -> Streamer:
        """
        配信者情報を保存または取得する。

        - `streamer_id` が既に存在し、名前が同じ場合は既存のレコードを返す。
        - `streamer_id` が存在するが名前が異なる場合、新規レコードを作成して履歴を保持する。

        Args:
            streamer_id (int): 配信者ID
            streamer_name (str): 配信者名

        Returns:
            Streamer: 最新の配信者インスタンス
        """
        latest_streamer = (
            Streamer.objects.filter(streamer_id=streamer_id).order_by("-created_at").first()
        )

        # 配信者が存在しない または、名前が変更されていた場合、新規作成
        if not latest_streamer or latest_streamer.name != streamer_name:
            streamer = Streamer.objects.create(
                streamer_id=streamer_id,
                name=streamer_name,
            )
        else:
            streamer = latest_streamer  # 名前が変更されていなければ最新のレコードを使用

        return streamer

    @classmethod
    def save_or_update_streaming(
        cls, streaming_data: StreamingData, streamer: Streamer, channel: Channel
    ) -> None:
        """
        配信データを保存または更新する。

        - `streaming_id` が既に存在する場合は更新。
        - 存在しない場合は新規作成。

        Args:
            streaming_data (StreamingData): 保存対象の配信データ
            streamer (Streamer): 紐付ける配信者インスタンス
        """
        streaming, created = Streaming.objects.update_or_create(
            streaming_id=streaming_data.id,
            defaults={
                "type": streaming_data.type,
                "title": streaming_data.title,
                "start_time": streaming_data.start_time,
                "end_time": streaming_data.end_time,
                "duration_time": streaming_data.duration_time,
                "status": streaming_data.status,
                "streamer": streamer,  # Streamer のインスタンスを紐付け
                "channel": channel,
            },
        )

    @classmethod
    def save_streaming_data(cls, streaming_data: StreamingData) -> None:
        """
        取得した配信データをデータベースに保存する。

        - 配信者情報 (`Streamer`) を保存または取得する
        - 配信データ (`Streaming`) を保存または更新する

        Args:
            streaming_data (StreamingData): 保存対象の配信データ
        """
        try:
            # 配信者情報の保存・取得
            streamer = cls.save_or_get_streamer(
                streamer_id=int(streaming_data.streamer_id),
                streamer_name=streaming_data.streamer_name,
            )

            # チャンネル情報の保存・更新
            channel = cls.create_or_update_channel(
                channel_id=int(streaming_data.channel_id),
                channel_name=streaming_data.channel_name,
                company_name=streaming_data.company_name,
            )

            # 配信データの保存・更新
            cls.save_or_update_streaming(streaming_data, streamer, channel)

        except Exception as e:
            logging.error(f"データベース保存エラー: {e}", exc_info=True)
            raise Exception(f"データベース保存エラー: {e}") from e

    @classmethod
    def create_or_update_channel(
        cls, channel_id: int, channel_name: str, company_name: str
    ) -> Channel:
        """
        チャンネル情報を保存または取得する。

        - `channel_id` が既に存在する場合、チャンネル名と企業名を更新。
        - `channel_id` が存在しない場合、新規レコードを作成。

        Args:
            channel_id (int): チャンネルID
            channel_name (str): チャンネル名
            company_name (str): 企業名

        Returns:
            Channel: 保存または更新されたチャンネルインスタンス
        """
        channel, created = Channel.objects.update_or_create(
            channel_id=channel_id, defaults={"name": channel_name, "company_name": company_name}
        )
        return channel
