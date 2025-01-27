"""配信データを取得する処理"""

import html
import json

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

# 取得したいURL
# url = "https://live.nicovideo.jp/watch/lv346868715"
url = "https://live.nicovideo.jp/watch/lv346883457"  # BANされた配信URL

# リクエストヘッダーを設定（ブラウザでアクセスしているように見せる）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# HTMLデータを取得
response = requests.get(url, headers=headers)
print(f"ステータスコード: {response.status_code}")

# ステータスコードを確認
if response.status_code == 200:
    # HTMLソースコードを取得
    html_content = response.text

    # BeautifulSoupを使用してHTMLを解析
    soup = BeautifulSoup(html_content, "html.parser")

    # 特定のスクリプトタグを抽出
    script_tag = soup.find("script", id="embedded-data")
    if isinstance(script_tag, Tag):
        # data-props属性を取得
        raw_data = script_tag.get("data-props")

        if raw_data is not None:
            # エスケープ文字をデコード
            decoded_data = html.unescape(str(raw_data))
            # JSON文字列を辞書に変換
            json_data = json.loads(decoded_data)
            # 整形して出力
            # print(json.dumps(json_data, indent=4, ensure_ascii=False))
            # タイトルを抽出
            title = json_data.get("program", {}).get("title")
            if title:
                print(f"配信タイトル: {title}")
            else:
                print("タイトルが見つかりませんでした。")
        else:
            print("data-props属性が見つかりませんでした。")
    else:
        print("指定されたスクリプトタグが見つかりませんでした。")
else:
    print("データを取得できませんでした。")
