# flowchart

```mermaid


flowchart TD
    A[配信IDから配信URLを生成する] --> B[リクエストヘッダーを作成する]
    B --> C[指定されたURLからHTMLデータを取得する]
    C --> D{HTTPステータスコード=200？}
    D -- No --> E[配信ID、配信ステータスを配信データに設定して、DBへの保存処理を呼びだす]
    E ----> M
    D -- Yes --> F[HTMLを解析し、data_props属性を持っているスクリプトタグを取得する]
    F --> G[スクリプトタグのdata-props属性の値をパース（json -> dict に変換）して、Pythonで扱えるようにする]
    G --> H[data_props から配信データを抽出する]
    H --> I{配信タイプは？}
    I -- community --> J[配信者情報を抽出する]
    I -- channel or official --> L[チャンネル情報を抽出する]
    J --> M[取得した配信データをデータベースに保存する]
    L --> M


```
