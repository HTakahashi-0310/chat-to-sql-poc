from __future__ import annotations
import asyncio
from typing import Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import asyncpg

from .config import settings
from .schema_catalog import load_schema_text
from .llm import ask_gemini
from .sql_validator import validate_sql, SqlValidationError

app = FastAPI(title="JP→SQL (SELECT only) API", version="0.1.0")

# 共有リソース
pool: Optional[asyncpg.pool.Pool] = None
schema_text_cache: Optional[str] = None

class QueryIn(BaseModel):
    question: str = Field(..., description="日本語の問い合わせ文")

class QueryOut(BaseModel):
    executed_sql: str
    params: List[Any]
    rows: List[dict]
    row_count: int
    clarification: str

@app.on_event("startup")
async def on_startup():
    global pool, schema_text_cache
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=5)
    # スキーマをキャッシュ
    async with pool.acquire() as con:
        await con.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    schema_text_cache = await load_schema_text(pool)

@app.on_event("shutdown")
async def on_shutdown():
    global pool
    if pool:
        await pool.close()

@app.post("/query", response_model=QueryOut)
async def run_query(body: QueryIn) -> QueryOut:
    if not schema_text_cache:
        raise HTTPException(status_code=500, detail="スキーマ情報が未ロードです。")

    # 1) LLM で SQL 生成（JSON: sql, params, clarification）
    llm_resp = ask_gemini(user_query=body.question, schema_text=schema_text_cache)
    sql = llm_resp.get("sql", "")
    params = llm_resp.get("params", [])
    clarification = llm_resp.get("clarification", "")

    # 2) 検証（SELECTのみ / LIMIT必須 / $1形式 / セミコロン禁止 等）
    try:
        sql = validate_sql(sql, params)
    except SqlValidationError as e:
        raise HTTPException(status_code=400, detail=f"生成SQLが無効: {e}")

    # 3) 実行（読み取り専用接続）
    async with pool.acquire() as con:
        # 念のためセッション読み取り専用を設定（ロールがREAD ONLYでもダブルガード）
        await con.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
        rows = await con.fetch(sql, *params)

    # 4) 辞書へ
    dict_rows = [dict(r) for r in rows]
    return QueryOut(
        executed_sql=sql,
        params=params,
        rows=dict_rows,
        row_count=len(dict_rows),
        clarification=clarification or "",
    )

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
