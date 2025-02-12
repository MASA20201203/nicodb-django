"""
指定された配信ID（または範囲）で配信データを取得する Django 管理コマンド。

## 使用例:
単一の配信データを取得:
    python manage.py get_streaming_data 346883570

指定した範囲の配信データを取得:
    python manage.py get_streaming_data 346883570 346883580
"""

import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("streamings")


class Command(BaseCommand):
    """
    指定された配信ID（または範囲）で配信データを取得する Django 管理コマンド。

    - 1つの配信IDを指定した場合、その配信データのみを取得。
    - 2つの配信ID（開始IDと終了ID）を指定した場合、範囲内の全ての配信データを取得。
    - IDの順番が逆の場合（開始ID > 終了ID）、エラーを出力し処理を中断。
    """

    help = "指定された配信ID（または範囲）で配信データを取得する"

    def add_arguments(self, parser):
        """
        コマンドライン引数を定義する。

        Args:
            parser (ArgumentParser): コマンドライン引数のパーサー。
        """
        parser.add_argument(
            "start_id",
            type=int,
            help="取得する配信データの開始ID（必須）",
        )
        parser.add_argument(
            "end_id",
            type=int,
            nargs="?",
            default=None,
            help="取得する配信データの終了ID（省略可能）。省略した場合は start_id と同じ値になる。",
        )

    def handle(self, *args, **options):
        """
        コマンドのメイン処理。

        - コマンドライン引数のバリデーションを行う。
        - 指定された範囲の配信データ取得処理を実行する。
        - ログを出力し、処理の開始・終了を明確にする。

        Args:
            *args: 任意の引数（使用しない）。
            **options: コマンドラインオプションを含む辞書。

        Raises:
            CommandError: IDの順序が不正な場合（開始ID > 終了ID）。
        """
        start_id, end_id = self.validate_ids(options["start_id"], options["end_id"])

        self.log_start(start_id, end_id)
        self.fetch_streaming_data_range(start_id, end_id)
        self.log_end(start_id, end_id)

    def validate_ids(self, start_id: int, end_id: int | None) -> tuple[int, int]:
        """
        開始IDと終了IDのバリデーションを行う。

        - end_id が None の場合、start_id と同じ値をセット。
        - start_id > end_id の場合、エラーを発生させる。

        Args:
            start_id (int): 取得対象の開始配信ID。
            end_id (int | None): 取得対象の終了配信ID（None の場合は start_id に統一）。

        Returns:
            tuple[int, int]: (開始ID, 終了ID) のタプル。

        Raises:
            CommandError: IDの順序が不正な場合（開始ID > 終了ID）。
        """
        end_id = end_id or start_id  # end_id が None の場合は start_id と同じにする

        if start_id > end_id:
            raise CommandError("開始IDは終了IDより小さい値にしてください。")

        return start_id, end_id

    def log_start(self, start_id: int, end_id: int):
        """
        処理開始時にログを出力する。

        Args:
            start_id (int): 取得対象の開始配信ID。
            end_id (int): 取得対象の終了配信ID。
        """
        logger.info(f"START 配信データ範囲取得を開始: ID範囲={start_id}〜{end_id}")

    def log_end(self, start_id: int, end_id: int):
        """
        処理終了時にログを出力する。

        Args:
            start_id (int): 取得対象の開始配信ID。
            end_id (int): 取得対象の終了配信ID。
        """
        logger.info(f"END   配信データ範囲取得が完了しました: ID範囲={start_id}〜{end_id}")

    def fetch_streaming_data_range(self, start_id: int, end_id: int):
        """
        指定された範囲の配信データを取得する。

        - 開始IDから終了IDまでループし、1件ずつ `fetch_and_save_streaming_data` を呼び出す。

        Args:
            start_id (int): 取得対象の開始配信ID。
            end_id (int): 取得対象の終了配信ID。
        """
        for streaming_id in range(start_id, end_id + 1):
            self.fetch_and_save_streaming_data(streaming_id)

    def fetch_and_save_streaming_data(self, streaming_id: int):
        """
        配信データを取得し、保存する処理。

        - `call_command` を使用して `get_streaming_data` コマンドを実行。
        - 取得・保存が成功した場合は `SUCCESS` ログを出力。
        - 取得に失敗した場合は `ERROR` ログを出力し、詳細なスタックトレースを記録。

        Args:
            streaming_id (int): 取得対象の配信ID。

        Raises:
            Exception: `get_streaming_data` の呼び出しに失敗した場合、エラーログを記録。
        """
        from django.core.management import call_command

        try:
            call_command("get_streaming_data", str(streaming_id))
        except Exception as e:
            logger.error(f"配信データ取得失敗: 配信ID={streaming_id}, エラー={e}", exc_info=True)
