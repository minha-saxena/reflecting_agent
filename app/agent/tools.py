import sqlite3
from typing import Optional
from app.db.seed import get_connection


def execute_sql(sql: str) -> dict:
    """
    Execute a SQL query against the in-memory SQLite DB.
    Returns { columns, rows, error }.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in cursor.fetchall()]
        return {"columns": columns, "rows": rows, "error": None}
    except Exception as e:
        return {"columns": [], "rows": [], "error": str(e)}
