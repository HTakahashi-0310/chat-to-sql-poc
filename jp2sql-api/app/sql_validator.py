from __future__ import annotations
import re
from typing import List, Tuple
import sqlparse
from .config import settings

# 1文のみ/SELECTのみ/$1形式/LIMIT必須/セミコロン禁止 などをチェック

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|CALL|DO|EXECUTE|COPY|VACUUM|ANALYZE)\b",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"\$(\d+)")
LIMIT_CLAUSE = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)

class SqlValidationError(ValueError):
    pass

def validate_sql(sql: str, params: List) -> str:
    if not sql or not sql.strip():
        raise SqlValidationError("SQLが空です。")

    # セミコロン禁止（複文防止）
    if ";" in sql.strip():
        raise SqlValidationError("SQLにセミコロンは使用できません（1文のみ）。")

    # 1文のみ判定（sqlparse）
    stmts = [s for s in sqlparse.parse(sql) if s.tokens]
    if len(stmts) != 1:
        raise SqlValidationError("SQLは単一文のみ許可です。")

    # SELECTのみ
    first_token = stmts[0].token_first(skip_cm=True)
    if not first_token or first_token.value.upper() != "SELECT":
        raise SqlValidationError("SELECT 文のみ実行可能です。")

    # 禁止キーワード
    if FORBIDDEN.search(sql):
        raise SqlValidationError("禁止されたキーワードが含まれています。")

    # LIMIT 必須 + 上限
    m = LIMIT_CLAUSE.search(sql)
    if not m:
        raise SqlValidationError("LIMIT 句が必須です。")
    try:
        limit_val = int(m.group(1))
        if limit_val < 1 or limit_val > settings.max_limit:
            raise SqlValidationError(f"LIMIT の値は 1〜{settings.max_limit} の範囲で指定してください。")
    except ValueError:
        raise SqlValidationError("LIMIT の数値が不正です。")

    # $1.. の連番整合性
    placeholders = sorted(int(n) for n in PLACEHOLDER.findall(sql))
    if placeholders:
        if placeholders[0] != 1 or placeholders != list(range(1, placeholders[-1] + 1)):
            raise SqlValidationError("プレースホルダ $1..$N は連番である必要があります。")
        if len(params) != placeholders[-1]:
            raise SqlValidationError("params の個数がプレースホルダ数と一致しません。")
    else:
        if len(params) != 0:
            raise SqlValidationError("プレースホルダがないのに params が渡されています。")

    return sql
