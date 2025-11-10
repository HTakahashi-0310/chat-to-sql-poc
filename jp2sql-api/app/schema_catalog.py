from __future__ import annotations
import asyncio
import asyncpg
from typing import Dict, List
from .config import settings

# DBスキーマ（テーブル/カラム/型）をカタログ化して LLM に渡すための文字列を作る
# - 起動時にロードし、必要に応じて更新（本雛形では起動時のみ）
# - 読み取り専用ユーザでOK

SCHEMA_SQL = """
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  a.attname AS column_name,
  pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
WHERE a.attnum > 0
  AND NOT a.attisdropped
  AND c.relkind IN ('r','p','v','m')           -- table/partition/view/materialized view
  AND n.nspname = ANY($1::text[])
ORDER BY n.nspname, c.relname, a.attnum;
"""

async def load_schema_text(pool: asyncpg.pool.Pool) -> str:
    async with pool.acquire() as con:
        rows = await con.fetch(SCHEMA_SQL, settings.schemas)

    # スキーマ文字列（プロンプトに渡す簡潔な形式）
    # 例:
    # schema public:
    #   table customers(id:int, name:text, created_at:timestamp)
    #   table orders(id:int, customer_id:int, total:numeric, created_at:timestamp)
    lines: List[str] = []
    current = {}
    for r in rows:
        key = (r["schema_name"], r["table_name"])
        current.setdefault(key, []).append((r["column_name"], r["data_type"]))

    by_schema: Dict[str, List[str]] = {}
    for (schema, table), cols in current.items():
        coltxt = ", ".join(f"{c}:{t}" for c, t in cols)
        by_schema.setdefault(schema, []).append(f"  table {table}({coltxt})")

    for schema, tables in by_schema.items():
        lines.append(f"schema {schema}:")
        lines.extend(tables)

    return "\n".join(lines)
