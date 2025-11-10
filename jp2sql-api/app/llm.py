from __future__ import annotations
import json
from typing import Any, Dict, Tuple
from tenacity import retry, stop_after_attempt, wait_fixed
import google.generativeai as genai
from .config import settings

# Gemini 1.5 Flash を JSON 固定スキーマで呼び出し
# 出力は必ず {"sql": str, "params": list, "clarification": str} の application/json

SYSTEM_INSTRUCTION = """
あなたはPostgreSQL用のSQLライターです。
必ず以下ルールを守って出力してください。

# 出力仕様（重要）
- レスポンスは `application/json` 形式のオブジェクトのみを返す。
- キーは "sql", "params", "clarification" の3つのみ。
- "sql" は単一の SELECT 文（1文のみ）。$1, $2 ... の位置プレースホルダを使用。
- LIMIT 句を必ず付与（上限は指示された MAX_LIMIT 以下）。
- "params" は配列で、$1, $2 ... に対応する値を順に入れる（型は推論）。
- 情報不足時は "clarification" に日本語で追加質問を書く。十分なら空文字 "" を入れる。

# 制約（厳守）
- SELECT 以外（INSERT/UPDATE/DELETE/DDL/DO/;複文/コメント注入など）は禁止。
- サブクエリやJOINは可。ただし必ず LIMIT を付ける。
- スキーマ名・テーブル名・列名は与えられたカタログに一致させる。
- 曖昧な語は推測しない。曖昧なら "clarification" を埋める。

# 例（形式のみの例）
入力: 「直近30日の注文を金額降順で上位50件」
出力(JSON):
{"sql":"SELECT id, total FROM orders WHERE created_at >= now() - INTERVAL '30 days' ORDER BY total DESC LIMIT 50","params":[],"clarification":""}
""".strip()

def _build_prompt(user_query: str, schema_text: str, max_limit: int) -> str:
    return f"""
# ユーザー質問（日本語）
{user_query}

# 使用可能なDBスキーマ
{schema_text}

# 制約
- LIMIT は {max_limit} 以下にすること
- $1, $2 ... のプレースホルダを使い、パラメタは "params" で返すこと
""".strip()

genai.configure(api_key=settings.google_api_key)

model = genai.GenerativeModel(
    model_name=settings.gemini_model,
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config={
        "temperature": settings.gemini_temperature,
        "response_mime_type": "application/json",
        "max_output_tokens": settings.gemini_max_output_tokens,
    },
)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def ask_gemini(user_query: str, schema_text: str) -> Dict[str, Any]:
    prompt = _build_prompt(user_query, schema_text, settings.max_limit)
    resp = model.generate_content(prompt)
    # SDKは text にJSON文字列が入る
    data = json.loads(resp.text)
    # 安全のためキー補正
    return {
        "sql": data.get("sql", ""),
        "params": data.get("params", []),
        "clarification": data.get("clarification", ""),
    }
