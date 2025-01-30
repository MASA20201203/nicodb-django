# アーキテクチャ

## 言語等

- プログラム言語: Python 3.13
- Webフレームワーク: Django 5.1.5
- テストフレームワーク: pytest 8.3.4
- リンター:
  - black 24.10.0（PEP8 自動フォーマット）
  - ruff 0.9.2（import文をソート、コーディング規約チェック）
  - mypy 1.14.1（型チェック）
  - tox 4.23.2（一括実行）

## インフラ

- Docker 26.1.3
- PostgreSQL 17.2

## VPS

- OS: CentOS Stream 8
- Webサーバー: Nginx 1.14.1

## システム構成

```plaintext
+-----------+        +-------------------+        +-------------+
|  Client   | -----> |  Django Backend   | -----> | PostgreSQL  |
+-----------+        +-------------------+        +-------------+
      |                      |
      v                      v
+-----------+        +-----------------+
|  Nginx    | -----> | Docker Container|
+-----------+        +-----------------+
```

## CI/CD

```mermaid
graph TD;
  開発者 -->|push| GitHub;
  GitHub -->|CI/CD| Docker Build;
  Docker Build -->|Deploy| 本番環境;
```
