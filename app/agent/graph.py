from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    node_generate_sql,
    node_execute_sql,
    node_reflect,
    node_done,
)


def _should_reflect_or_end(state: AgentState) -> str:
    """After execute: always reflect unless max attempts reached."""
    if state.get("attempt", 0) >= state.get("max_attempts", 3):
        return "done"
    # always go to reflect — even on success, for one review pass
    return "reflect"


def _after_reflect(state: AgentState) -> str:
    """
    After reflect:
    - Query verified correct (no revision needed) → done
    - Query needs fixing → regenerate (if attempts remain)
    - Max attempts hit → end
    """
    if state.get("attempt", 0) >= state.get("max_attempts", 3):
        return "end"
    if not state.get("needs_revision", False):
        return "done"
    return "generate"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("execute_sql",  node_execute_sql)
    graph.add_node("reflect",      node_reflect)
    graph.add_node("done",         node_done)

    graph.set_entry_point("generate_sql")

    graph.add_edge("generate_sql", "execute_sql")

    # After execute: reflect or end (no more direct-to-done)
    graph.add_conditional_edges(
        "execute_sql",
        _should_reflect_or_end,
        {
            "reflect": "reflect",
            "done":    "done",
        },
    )

    # After reflect: done / regenerate / end
    graph.add_conditional_edges(
        "reflect",
        _after_reflect,
        {
            "done":     "done",
            "generate": "generate_sql",
            "end":      END,
        },
    )

    graph.add_edge("done", END)

    return graph.compile()


reflection_graph = build_graph()