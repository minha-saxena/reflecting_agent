import re
import sqlite3
from app.db.seed import get_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── SQL safety ────────────────────────────────────────────────────────────────

_BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "REPLACE", "CREATE", "ATTACH", "DETACH",
}

_QUESTION_RISK_KEYWORDS = {
    "drop", "delete", "remove", "truncate", "update",
    "insert", "alter", "modify", "destroy", "wipe",
}

MAX_QUESTION_LENGTH = 500


def sanitize_question(question: str) -> tuple[str, list[str]]:
    """
    Sanitize the user's natural language question.
    Returns (sanitized_question, list_of_warnings).
    """
    warnings = []

    if len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH]
        warnings.append(f"Question truncated to {MAX_QUESTION_LENGTH} characters.")

    found = [kw for kw in _QUESTION_RISK_KEYWORDS if kw in question.lower().split()]
    if found:
        warnings.append(
            f"Question contains potentially risky keywords: {found}. "
            "Only SELECT queries are allowed."
        )
        logger.warning("Risky keywords in question: %s | question=%s", found, question)

    return question.strip(), warnings


def _check_sql_safety(sql: str) -> str | None:
    """
    Returns an error message if SQL contains blocked statements.
    Returns None if safe to execute.
    """
    # Strip comments before checking
    cleaned = re.sub(r"--[^\n]*", "", sql)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    tokens = [t.upper() for t in cleaned.split() if t.strip()]

    if not tokens:
        return "Empty SQL statement."

    if tokens[0] != "SELECT":
        return f"Only SELECT statements are allowed. Got: '{tokens[0]}'."

    blocked_found = [kw for kw in _BLOCKED_KEYWORDS if kw in tokens]
    if blocked_found:
        return f"SQL contains blocked keyword(s): {blocked_found}. Only SELECT is permitted."

    return None


# ── SQL execution ─────────────────────────────────────────────────────────────

def execute_sql(sql: str) -> dict:
    """
    Execute a SQL query against the in-memory SQLite DB.
    Blocks non-SELECT statements before execution.
    Returns { columns, rows, error }.
    """
    logger.info("Executing SQL: %s", sql.replace("\n", " ").strip())

    safety_error = _check_sql_safety(sql)
    if safety_error:
        logger.warning("SQL blocked by safety check: %s", safety_error)
        return {"columns": [], "rows": [], "error": f"[Safety] {safety_error}"}

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in cursor.fetchall()]
        logger.info("SQL executed successfully — %d row(s) returned.", len(rows))
        return {"columns": columns, "rows": rows, "error": None}

    except sqlite3.OperationalError as e:
        logger.warning("SQL operational error: %s", str(e))
        return {"columns": [], "rows": [], "error": str(e)}

    except Exception as e:
        logger.error("Unexpected SQL execution error: %s", str(e))
        return {"columns": [], "rows": [], "error": str(e)}