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
