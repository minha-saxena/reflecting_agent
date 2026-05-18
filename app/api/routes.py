import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agent.graph import reflection_graph
from app.db.seed import get_schema_info, get_connection
from app.core.config import settings
from app.agent.tools import sanitize_question
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    max_attempts: int = 3


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok", "model": settings.OLLAMA_MODEL}


# ── Schema ────────────────────────────────────────────────────────────────────

@router.get("/schema")
def schema():
    conn = get_connection()
    cursor = conn.cursor()
    tables = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (table,) in cursor.fetchall():
        cursor.execute(f"PRAGMA table_info({table})")
        tables[table] = [
            {"name": row[1], "type": row[2], "pk": bool(row[5])}
            for row in cursor.fetchall()
        ]
    return {"tables": tables, "schema_info": get_schema_info()}


# ── Query (streaming SSE) ─────────────────────────────────────────────────────

@router.post("/query/stream")
async def query_stream(request: QueryRequest):
    question, warnings = sanitize_question(request.question)

    if warnings:
        for w in warnings:
            logger.warning("Input sanitization warning: %s", w)

    logger.info(
        "Streaming query | question=%s | max_attempts=%d",
        question, request.max_attempts,
    )

    async def event_generator():
        initial_state = {
            "question": question,
            "schema_info": get_schema_info(),
            "sql": None,
            "result_columns": [],
            "result_rows": [],
            "error": None,
            "reflection": None,
            "attempt": 0,
            "max_attempts": request.max_attempts,
            "step_log": [],
            "success": False,
        }

        seen_steps = 0
        last_valid_state = initial_state

        try:
            async for state in reflection_graph.astream(initial_state):
                for node_name, node_state in state.items():
                    if not node_state:
                        continue

                    last_valid_state = node_state
                    step_log = node_state.get("step_log", [])

                    while seen_steps < len(step_log):
                        step = step_log[seen_steps]
                        yield f"data: {json.dumps({'type': 'step', 'step': step})}\n\n"
                        seen_steps += 1
                        await asyncio.sleep(0)

        except Exception as e:
            logger.error("Agent error during streaming: %s", str(e))
            yield f"data: {json.dumps({'type': 'step', 'step': {'step': 'error', 'title': 'Agent error', 'error': str(e)}})}\n\n"

        result = {
            "type": "result",
            "success": last_valid_state.get("success", False),
            "columns": last_valid_state.get("result_columns", []),
            "rows": last_valid_state.get("result_rows", []),
            "attempts": last_valid_state.get("attempt", 0) + 1,
            "sql": last_valid_state.get("sql"),
        }
        logger.info(
            "Stream complete | success=%s | rows=%d | attempts=%d",
            result["success"], len(result["rows"]), result["attempts"],
        )
        yield f"data: {json.dumps(result)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Query (non-streaming) ─────────────────────────────────────────────────────

@router.post("/query")
async def query(request: QueryRequest):
    question, warnings = sanitize_question(request.question)

    if warnings:
        for w in warnings:
            logger.warning("Input sanitization warning: %s", w)

    logger.info("Blocking query | question=%s | max_attempts=%d", question, request.max_attempts)

    initial_state = {
        "question": question,
        "schema_info": get_schema_info(),
        "sql": None,
        "result_columns": [],
        "result_rows": [],
        "error": None,
        "reflection": None,
        "attempt": 0,
        "max_attempts": request.max_attempts,
        "step_log": [],
        "success": False,
    }

    final_state = await reflection_graph.ainvoke(initial_state)

    logger.info(
        "Blocking query complete | success=%s | attempts=%d",
        final_state["success"], final_state["attempt"] + 1,
    )

    return {
        "success": final_state["success"],
        "question": final_state["question"],
        "sql": final_state["sql"],
        "columns": final_state["result_columns"],
        "rows": final_state["result_rows"],
        "attempts": final_state["attempt"] + 1,
        "step_log": final_state["step_log"],
        "error": final_state.get("error"),
    }