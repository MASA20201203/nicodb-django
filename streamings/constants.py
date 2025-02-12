"""
配信データ取得処理で使用する定数を定義するモジュール。
"""

from enum import IntEnum


class StreamingStatus(IntEnum):
    """
    配信ステータスを表す列挙型。
    """

    RESERVED = 10
    ON_AIR = 20
    ENDED = 30
