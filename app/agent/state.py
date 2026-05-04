from typing import TypedDict, Optional
from dataclasses import dataclass, field


@dataclass
class StepLog:
    step: str          # "generate" | "execute" | "reflect" | "done" | "error"
    title: str
    reasoning: Optional[str] = None
    sql: Optional[str] = None
    error: Optional[str] = None
    attempt: int = 0


class AgentState(TypedDict):
    question: str                   # original user question
    schema_info: str                # DB schema string
    sql: Optional[str]              # last generated SQL
    result_columns: list            # column names from execution
    result_rows: list               # rows from execution
    error: Optional[str]            # last execution error
    reflection: Optional[str]       # LLM's reflection on the error
    attempt: int                    # current attempt number
    max_attempts: int               # max retries allowed
    step_log: list[dict]            # list of StepLog dicts for UI
    needs_revision: bool
    success: bool                   # did agent succeed?
