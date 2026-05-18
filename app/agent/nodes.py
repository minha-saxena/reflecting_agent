import re
import time
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import AgentState
from app.agent.tools import execute_sql
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


#  LLM with retry 

def _get_llm():
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.2,
    )


def _invoke_llm_with_retry(messages: list) -> str:
    """
    Invoke the LLM with retry logic.
    Retries up to OLLAMA_MAX_RETRIES times with OLLAMA_RETRY_DELAY seconds apart.
    Raises RuntimeError if all retries are exhausted.
    """
    last_error = None

    for attempt in range(1, settings.OLLAMA_MAX_RETRIES + 1):
        try:
            llm = _get_llm()
            response = llm.invoke(messages)
            if attempt > 1:
                logger.info("Ollama responded successfully on attempt %d.", attempt)
            return response.content

        except Exception as e:
            last_error = e
            logger.warning(
                "Ollama unreachable — attempt %d/%d. Error: %s",
                attempt, settings.OLLAMA_MAX_RETRIES, str(e),
            )
            if attempt < settings.OLLAMA_MAX_RETRIES:
                time.sleep(settings.OLLAMA_RETRY_DELAY)

    logger.error(
        "Ollama failed after %d attempt(s). Is Ollama running at %s? "
        "Start it with: OLLAMA_ORIGINS='*' ollama serve",
        settings.OLLAMA_MAX_RETRIES,
        settings.OLLAMA_BASE_URL,
    )
    raise RuntimeError(
        f"Ollama is not responding at {settings.OLLAMA_BASE_URL} "
        f"after {settings.OLLAMA_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


#  Helpers ─

def _extract_sql(text: str) -> str:
    """Pull SQL out of markdown code blocks or raw text."""
    m = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _log(state: AgentState, step: str, title: str, **kwargs) -> list:
    log = list(state.get("step_log", []))
    log.append({
        "step": step,
        "title": title,
        "attempt": state.get("attempt", 0),
        **kwargs,
    })
    return log


#  Node 1: Generate SQL 

def node_generate_sql(state: AgentState) -> AgentState:
    attempt = state.get("attempt", 0)
    last_error = state.get("error")
    reflection = state.get("reflection")

    logger.info("Node: generate_sql | attempt=%d | question=%s", attempt, state["question"])

    system_prompt = f"""You are a SQLite SQL expert.
Given the database schema and a user question, write a correct SQLite SQL query.
Return ONLY the SQL inside a ```sql``` block. No explanation, no prose.

Schema:
{state['schema_info']}"""

    if reflection:
        system_prompt += f"""

Previous attempt failed or was flagged for revision.
Error: {last_error or 'No execution error — query was logically incorrect.'}
Reflection: {reflection}

Using ONLY the tables and columns in the schema above, fix the query based on the reflection."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["question"]),
    ]

    content = _invoke_llm_with_retry(messages)
    sql = _extract_sql(content)

    reasoning = (
        f'Translating: "{state["question"]}"'
        if attempt == 0
        else f"Revised SQL after reflection on: {last_error or 'logical review'}"
    )

    logger.info("Generated SQL: %s", sql.replace("\n", " ").strip())

    return {
        **state,
        "sql": sql,
        "error": None,
        "step_log": _log(state, "generate", "Generated SQL", reasoning=reasoning, sql=sql),
    }


#  Node 2: Execute SQL ─

def node_execute_sql(state: AgentState) -> AgentState:
    logger.info("Node: execute_sql | attempt=%d", state.get("attempt", 0))

    result = execute_sql(state["sql"])

    if result["error"]:
        logger.warning("Execution failed: %s", result["error"])
        return {
            **state,
            "result_columns": [],
            "result_rows": [],
            "error": result["error"],
            "success": False,
            "needs_revision": True,
            "step_log": _log(
                state, "error", "Execution failed",
                sql=state["sql"],
                error=result["error"],
            ),
        }

    logger.info("Execution succeeded — %d row(s) returned.", len(result["rows"]))
    return {
        **state,
        "result_columns": result["columns"],
        "result_rows": result["rows"],
        "error": None,
        "success": True,
        "needs_revision": True,
        "step_log": _log(
            state, "execute",
            f"Executed — {len(result['rows'])} row(s) returned",
            sql=state["sql"],
        ),
    }


#  Node 3: Reflect ─

def node_reflect(state: AgentState) -> AgentState:
    logger.info(
        "Node: reflect | attempt=%d | has_error=%s",
        state.get("attempt", 0),
        bool(state.get("error")),
    )

    if state.get("error"):
        prompt = (
            "You are a SQL debugging assistant.\n\n"
            f"Schema:\n{state['schema_info']}\n\n"
            f"Question:\n{state['question']}\n\n"
            f"SQL:\n{state['sql']}\n\n"
            f"Error:\n{state['error']}\n\n"
            "Using ONLY the tables and columns in the schema above, explain briefly "
            "why the query failed and provide corrected SQL.\n"
            "Return exactly:\n"
            "REFLECTION: ...\n"
            "SQL: ```sql ... ```"
        )
    else:
        prompt = (
            "You are an extremely strict senior SQL reviewer.\n"
            "Assume the query is wrong unless you can prove it satisfies every requirement.\n\n"
            f"Schema:\n{state['schema_info']}\n\n"
            f"User question:\n{state['question']}\n\n"
            f"Generated SQL:\n```sql\n{state['sql']}\n```\n\n"
            f"Returned columns:\n{state['result_columns']}\n\n"
            f"Sample rows:\n{state['result_rows'][:5]}\n\n"
            "Using ONLY the tables and columns in the schema above, review the SQL carefully.\n"
            "You must verify:\n"
            "1. Every filter mentioned in the question is present\n"
            "2. The correct aggregation is used (SUM vs COUNT vs AVG)\n"
            "3. Grouping and ordering are correct\n"
            "4. Ranking/limits are applied correctly\n"
            "5. Date conditions are correct\n"
            "6. The query is not missing joins or HAVING clauses\n"
            "7. The SQL matches the meaning of the question, not just part of it\n\n"
            "If ANY requirement is missing, even slightly, the query is incorrect.\n\n"
            "Return EXACTLY in this format:\n\n"
            "REFLECTION: <one short sentence explaining what is wrong or 'Query is correct'>\n"
            "SQL:\n```sql\n<correct SQL>\n```"
        )

    content = _invoke_llm_with_retry([HumanMessage(content=prompt)])
    content = content.strip()

    reflection_match = re.search(
        r"REFLECTION:\s*(.*?)(?=SQL:)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    reflection = reflection_match.group(1).strip() if reflection_match else content
    new_sql = _extract_sql(content)

    query_is_correct = "query is correct" in reflection.lower()
    needs_revision = (
        not query_is_correct
        and new_sql.strip().lower() != state["sql"].strip().lower()
    )

    logger.info(
        "Reflection complete | query_is_correct=%s | needs_revision=%s",
        query_is_correct, needs_revision,
    )

    return {
        **state,
        "reflection": reflection,
        "sql": new_sql if needs_revision else state["sql"],
        "needs_revision": needs_revision,
        "success": not needs_revision and state.get("error") is None,
        "attempt": state.get("attempt", 0) + 1,
        "step_log": _log(
            state,
            "reflect",
            "Reflection",
            reasoning=reflection,
            sql=new_sql if needs_revision else state["sql"],
        ),
    }


#  Node 4: Done 

def node_done(state: AgentState) -> AgentState:
    rows = state.get("result_rows", [])
    logger.info(
        "Node: done | success=%s | rows=%d | attempts=%d",
        state.get("success"), len(rows), state.get("attempt", 0),
    )
    return {
        **state,
        "step_log": _log(
            state, "done",
            f"Done — {len(rows)} row(s) returned",
            sql=state["sql"],
        ),
    }