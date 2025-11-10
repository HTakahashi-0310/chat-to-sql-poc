# JP → SQL (SELECT only) API

LLM（Google Gemini 1.5 Flash）を使用し、日本語の質問 → SQL生成 → PostgreSQL 実行（SELECTのみ） を行う安全設計の API です。

- 日本語入力のみでデータ検索
- LLM が SQL を生成・パラメタ化（$1 形式）
- すべての SQL をバリデーションして安全に実行
- PostgreSQL の読み取り専用ロールで実行
- LIMIT 必須（上限あり）

## ✅ 特徴

- Gemini 1.5 Flash を application/json 固定スキーマ で呼び出し
→ LLM 出力は "sql", "params", "clarification" のみ
- SELECT 以外の SQL を完全禁止（sqlparse によるチェック＋キーワード拒否）
- LIMIT 強制・最大行数キャップ
- $1 形式プレースホルダのみ許可
- 読み取り専用ロール + セッション READ ONLY
- スキーマカタログを LLM に渡して hallucination を抑制

## 📁 ディレクトリ構成
```
jp2sql-api/
├─ app/
│  ├─ config.py
│  ├─ schema_catalog.py
│  ├─ llm.py
│  ├─ sql_validator.py
│  └─ main.py
├─ .env.example
├─ requirements.txt
└─ README.md
```

## 🚀 セットアップ
1. 依存インストール
``` bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. ```.env``` を設定
``` bash
cp .env.example .env
```

以下を編集：
``` dotenv
GOOGLE_API_KEY=your_google_api_key
DATABASE_URL=postgresql://readonly_user:password@localhost:5432/sampledb
GEMINI_MODEL=gemini-1.5-flash
MAX_LIMIT=1000
SCHEMAS=public
```

3. PostgreSQL 側の準備（必須）

読み取り専用ロールを作成：
``` sql
CREATE ROLE readonly_user LOGIN PASSWORD 'password';
GRANT CONNECT ON DATABASE sampledb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;
```

4. サーバ起動
``` bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## ✅ API 仕様
```POST /query```

日本語の質問を SQL に変換し、PostgreSQL に実行して結果を返します。

入力
``` json
{
  "question": "直近30日の注文を金額降順で上位50件表示して"
}
```

出力
``` json
{
  "executed_sql": "SELECT id, total FROM orders WHERE created_at >= now() - INTERVAL '30 days' ORDER BY total DESC LIMIT 50",
  "params": [],
  "rows": [
    { "id": 123, "total": "999.99" }
  ],
  "row_count": 1,
  "clarification": ""
}
``` 

```clarification``` とは？
- LLM が情報不足と判断した場合、日本語で 追加の質問 を入れます
- 空文字の場合は十分な情報がある意味

```GET /healthz```

単純なヘルスチェック。

## 🧪 例：curl テスト
``` bash
curl -s -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "顧客テーブルから名前とメールを50件"}' | jq .
```

## 🔐 安全設計（セキュリティ）

本 API は「自然言語 → SQL」を安全に行うために、複数のガードレールを実装済みです。

### ✅ SQL バリデーション

- SELECT 以外を拒否
- セミコロン禁止（複文禁止）
- $1, $2… のプレースホルダのみ
- LIMIT 必須（.env の MAX_LIMIT 以下）
- 禁止キーワード（INSERT/UPDATE/DELETE/DDL など）拒否
- パラメタ数とプレースホルダ整合性チェック

### ✅ DB 保護

- 読み取り専用ロール（PostgreSQL 側）
- セッションごとに SET TRANSACTION READ ONLY
- LLM が hallucinate しないよう スキーマカタログ を限定提供

### ✅ LLM 側ガード

- 出力は JSON 固定フォーマット
- 不正なテキスト混入を防止
- 十分な情報がなければ clarification を要求し勝手に SQL を作らない

## 🔧 拡張ポイント

- SQL AST 解析（sqlglot）の導入
- 列レベル・行レベルセキュリティ（RLS）
- 結果セットサイズのバイト制限
- キャッシュ（SQL → 結果）
- ```/translate``` エンドポイント（SQL生成のみ）
- スキーマカタログの自動更新機能
- メタデータAPI追加（スキーマ一覧取得など）

## 📝 ライセンス

MIT（必要に応じて変更してください）