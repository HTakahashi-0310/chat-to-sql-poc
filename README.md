# chat-to-sql-poc

本リポジトリは、LLM との対話を通じて自然言語から SQL を生成し、  
データベースに対してクエリを実行し、その結果をユーザーに返す仕組みの PoC（Proof of Concept）です。

## 🎯 目的
- ユーザーの自然言語入力を LLM が SQL に変換できるか検証する
- SQL 実行結果を自然言語で返す対話 UI の検証
- JSON 列を持つ DBMS（例: PostgreSQL / MySQL 8 / SQLite JSON1）での挙動確認
- セキュリティ（SQLインジェクション・危険クエリ制御）の課題洗い出し

## 🛠 技術スタック（例）
- Backend: Python (FastAPI) / Node.js (Express) など任意
- LLM API: OpenAI API or Azure OpenAI API
- DBMS: PostgreSQL（推奨）または MySQL / SQLite
- ORM: SQLAlchemy / Prisma / Knex など任意
- UI: 簡易チャット画面（optional）

## 📦 実装内容
1. Chat 形式の自然言語入力を受け取るエンドポイント
2. LLM にスキーマ情報を渡して SQL を生成させる
3. SQL 実行前に安全チェックを行う
4. DB に問い合わせて結果を取得
5. 結果を自然言語で整形し返却
6. 実行ログを残す

## 🚧 PoC の範囲
- CRUD のうち SELECT を中心に検証
- DB スキーマは簡易的なサンプル
- LLM はプロンプトベースの制御を試すだけ（RAG は本 PoC では任意）

## 📁 ディレクトリ構成（案）

