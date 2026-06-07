from __future__ import annotations

from typing import Any


def normalize_tables(structured: dict[str, Any]) -> list[dict[str, Any]]:
    tables = structured.get("tables")
    return tables if isinstance(tables, list) else []

