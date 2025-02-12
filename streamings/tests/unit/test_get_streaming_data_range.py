from unittest.mock import patch

import pytest
from django.core.management import CommandError

from streamings.management.commands.get_streaming_data_range import Command


class TestValidateIds:
    """
    validate_ids のユニットテスト。
    """

    def test_valid_range(self) -> None:
        """
        開始ID < 終了ID の場合、正しくタプル (start_id, end_id) を返すことを確認。
        """
        # When: start_id < end_id で引数が与えられた時、
        start_id, end_id = Command.validate_ids(100, 200)

        # Then: それぞれの値が正しいことを確認
        assert start_id == 100
        assert end_id == 200

    def test_same_start_and_end_id(self) -> None:
        """
        終了IDが None の場合、開始IDと同じ値が返されることを確認。
        """
        # When: 終了IDが None の場合、
        start_id, end_id = Command.validate_ids(150, None)

        # Then: 開始IDと終了IDが同じ値になることを確認
        assert start_id == 150
        assert end_id == 150  # None の場合は start_id と同じ値になる

    def test_invalid_range_raises_error(self) -> None:
        """
        開始ID > 終了ID の場合、CommandError が発生することを確認。
        """
        # When & Then: 開始ID > 終了ID の場合、エラーが発生することを確認
        with pytest.raises(CommandError, match="開始IDは終了IDより小さい値にしてください。"):
            Command.validate_ids(300, 200)  # 開始IDが終了IDより大きいケース


class TestFetchStreamingDataRange:
    """
    Command.fetch_streaming_data_range のユニットテスト。
    """

    @patch.object(Command, "fetch_and_save_streaming_data")
    def test_fetch_streaming_data_range_calls_fetch_and_save(self, mock_fetch_and_save) -> None:
        """
        指定された範囲内で fetch_and_save_streaming_data が正しく呼ばれることを確認。
        """
        # Given: start_id = 100, end_id = 102 の範囲で
        start_id = 100
        end_id = 102

        # When: fetch_streaming_data_range を呼び出した時、
        Command.fetch_streaming_data_range(start_id, end_id)

        # Then: 呼び出し回数と呼び出しIDが正しいことを確認
        # fetch_and_save_streaming_data が (end_id - start_id + 1) 回 呼び出されているか
        assert mock_fetch_and_save.call_count == (end_id - start_id + 1)

        # それぞれの ID で呼び出されているか
        expected_calls = [((streaming_id,),) for streaming_id in range(start_id, end_id + 1)]
        mock_fetch_and_save.assert_has_calls(expected_calls, any_order=False)


class TestFetchAndSaveStreamingData:
    """
    `fetch_and_save_streaming_data` メソッドのテストクラス
    """

    @patch("django.core.management.call_command")
    def test_fetch_and_save_streaming_data_success(self, mock_call_command):
        """
        正常系: `call_command` が正しく呼び出されることを確認。
        """
        # Given: 配信IDが 12345 の場合、
        streaming_id = 12345

        # When: fetch_and_save_streaming_data を呼び出した時、
        Command.fetch_and_save_streaming_data(streaming_id)

        # Then: `call_command` が正しく呼び出されることを確認
        mock_call_command.assert_called_once_with("get_streaming_data", str(streaming_id))

    @patch("django.core.management.call_command")
    @patch("streamings.management.commands.get_streaming_data_range.logger")
    def test_fetch_and_save_streaming_data_failure(self, mock_logger, mock_call_command):
        """
        異常系: `call_command` が例外を発生させた場合に、エラーログが出力されることを確認。
        """
        # Given: 配信IDが 12345 で、`call_command` が例外を発生させる場合
        streaming_id = 12345
        mock_call_command.side_effect = Exception("テスト用のエラー")

        # When: fetch_and_save_streaming_data を呼び出した時、
        Command.fetch_and_save_streaming_data(streaming_id)

        # Then: エラーログが正しく出力されることを確認
        mock_logger.error.assert_called_once_with(
            f"配信データ取得失敗: 配信ID={streaming_id}, エラー=テスト用のエラー",
            exc_info=True,
        )
