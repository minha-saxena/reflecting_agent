# import streamlit as st
# import requests
# import json
# import pandas as pd
# import time
# from app.core.config import settings

# API_BASE = settings.API_BASE

# st.set_page_config(
#     page_title="SQL Reflection Agent",
#     page_icon="⟳",
#     layout="wide",
# )

# # Styles 
# st.markdown("""
# <style>
# .node-row { display: flex; gap: 12px; align-items: center; margin: 12px 0; }
# .node-box {
#     padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
#     border: 1.5px solid #333; color: #888; background: #1a1a1f;
#     text-align: center; min-width: 130px;
# }
# .node-box.active { border-color: #00d4a0; color: #00d4a0; background: #001a14; }
# .node-box.done   { border-color: #40d080; color: #40d080; background: #001a0d; }
# .node-box.error  { border-color: #f04060; color: #f04060; background: #1a0010; }
# .arrow { color: #444; font-size: 18px; }
# .step-gen     { border-left: 3px solid #00d4a0; padding-left: 10px; }
# .step-execute { border-left: 3px solid #40d080; padding-left: 10px; }
# .step-reflect { border-left: 3px solid #f0a500; padding-left: 10px; }
# .step-error   { border-left: 3px solid #f04060; padding-left: 10px; }
# .step-done    { border-left: 3px solid #40d080; padding-left: 10px; }
# .badge {
#     display: inline-block; padding: 2px 8px; border-radius: 4px;
#     font-size: 11px; font-weight: 600; margin-left: 8px;
# }
# .badge-gen     { background: #001a14; color: #00d4a0; border: 1px solid #00d4a080; }
# .badge-execute { background: #001a0d; color: #40d080; border: 1px solid #40d08080; }
# .badge-reflect { background: #1a1000; color: #f0a500; border: 1px solid #f0a50080; }
# .badge-error   { background: #1a0010; color: #f04060; border: 1px solid #f0406080; }
# .badge-done    { background: #001a0d; color: #40d080; border: 1px solid #40d08080; }
# </style>
# """, unsafe_allow_html=True)


# # Header 
# st.markdown("## SQL Reflection Agent")
# st.markdown("LangGraph · LangChain · Ollama · SQLite")
# st.divider()

# # Sidebar 
# with st.sidebar:
#     st.markdown("### Config")
#     max_attempts = st.slider("Max reflection attempts", 1, 5, 3)

#     st.markdown("### Schema")
#     try:
#         schema_resp = requests.get(f"{API_BASE}/schema", timeout=3)
#         if schema_resp.ok:
#             schema_data = schema_resp.json()
#             for table, cols in schema_data["tables"].items():
#                 with st.expander(f" {table}"):
#                     for col in cols:
#                         pk = " 🔑" if col["pk"] else ""
#                         st.code(f"{col['name']}  {col['type']}{pk}", language=None)
#     except Exception:
#         st.warning("API not reachable. Start FastAPI first.")

#     st.markdown("### Try these")
#     suggestions = [
#         "Calculate total revenue for each product category.",
#         "Rank customers by number of orders, show their rank and total spend",
#         "For each order, show customer's previous order date.",
#         "Get orders where quantity is greater than average quantity of that product",
#         "Average order value by category",
#         "Customers who never placed an order",
#     ]
#     for s in suggestions:
#         if st.button(s, use_container_width=True, key=f"sug_{s}"):
#             st.session_state["question"] = s

#     st.markdown("---")
#     st.markdown("### Ollama")
#     st.code("OLLAMA_ORIGINS='*' ollama serve", language="bash")

# # Main input
# question = st.text_area(
#     "Ask a question about the database",
#     value=st.session_state.get("question", ""),
#     placeholder="e.g. Show me top 5 customers by total order value",
#     height=80,
#     key="question_input",
# )

# run_col, _ = st.columns([1, 5])
# run_clicked = run_col.button("▶ Run Agent", type="primary", use_container_width=True)

# # Node graph UI 
# st.markdown("### Agent Loop")
# node_cols = st.columns([3, 1, 3, 1, 3, 1, 3])
# node_placeholders = {
#     "generate": node_cols[0].empty(),
#     "execute":  node_cols[2].empty(),
#     "reflect":  node_cols[4].empty(),
#     "done":     node_cols[6].empty(),
# }
# node_cols[1].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)
# node_cols[3].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)
# node_cols[5].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)

# def render_node(placeholder, label, subtitle, state="idle"):
#     placeholder.markdown(
#         f'<div class="node-box {state}">{label}<br/>'
#         f'<span style="font-size:10px;font-weight:400;opacity:0.7">{subtitle}</span></div>',
#         unsafe_allow_html=True,
#     )

# def reset_nodes():
#     render_node(node_placeholders["generate"], "Generate SQL",  "NL → SQL")
#     render_node(node_placeholders["execute"],  "Execute",       "Run in SQLite")
#     render_node(node_placeholders["reflect"],  "Reflect",       "Analyse error")
#     render_node(node_placeholders["done"],     "Done",          "Return results")

# reset_nodes()

# NODE_MAP = {
#     "generate": "generate",
#     "execute":  "execute",
#     "error":    "execute",
#     "reflect":  "reflect",
#     "done":     "done",
# }

# # Step log + results placeholders 
# st.markdown("### Step Log")
# timeline_placeholder = st.empty()

# st.markdown("### Results")
# results_placeholder = st.empty()

# # Run agent
# if run_clicked and question.strip():
#     steps = []
#     result_data = None

#     reset_nodes()
#     timeline_placeholder.info("Agent running…")
#     results_placeholder.empty()

#     active_nodes = set()

#     try:
#         with requests.post(
#             f"{API_BASE}/query/stream",
#             json={"question": question.strip(), "max_attempts": max_attempts},
#             stream=True,
#             timeout=120,
#         ) as resp:

#             for line in resp.iter_lines():
#                 if not line:
#                     continue
#                 if isinstance(line, bytes):
#                     line = line.decode()
#                 if not line.startswith("data: "):
#                     continue

#                 payload = json.loads(line[6:])

#                 if payload["type"] == "step":
#                     step = payload["step"]
#                     steps.append(step)
#                     step_type = step.get("step", "")

#                     # Update node graph
#                     node_key = NODE_MAP.get(step_type)
#                     if node_key:
#                         # Mark previous as done
#                         for k in list(active_nodes):
#                             render_node(
#                                 node_placeholders[k],
#                                 k.capitalize(),
#                                 {"generate":"NL → SQL","execute":"Run in SQLite","reflect":"Analyse error","done":"Return results"}.get(k,""),
#                                 "done" if step_type != "error" else "error",
#                             )
#                         active_nodes = {node_key}
#                         render_node(
#                             node_placeholders[node_key],
#                             node_key.capitalize(),
#                             {"generate":"NL → SQL","execute":"Run in SQLite","reflect":"Analyse error","done":"Return results"}.get(node_key,""),
#                             "active",
#                         )

#                     # Render step log
#                     with timeline_placeholder.container():
#                         for i, s in enumerate(steps):
#                             stype = s.get("step", "generate")
#                             badge_map = {
#                                 "generate": ("badge-gen",     "GENERATE"),
#                                 "execute":  ("badge-execute", "EXECUTE"),
#                                 "reflect":  ("badge-reflect", "REFLECT"),
#                                 "error":    ("badge-error",   "ERROR"),
#                                 "done":     ("badge-done",    "DONE"),
#                             }
#                             badge_cls, badge_label = badge_map.get(stype, ("badge-gen", stype.upper()))
#                             with st.expander(
#                                 f"{str(i+1).zfill(2)}  {s.get('title','')}",
#                                 expanded=(i == len(steps) - 1),
#                             ):
#                                 if s.get("reasoning"):
#                                     st.markdown(f"**Reasoning:** {s['reasoning']}")
#                                 if s.get("sql"):
#                                     st.code(s["sql"], language="sql")
#                                 if s.get("error"):
#                                     st.error(s["error"])

#                 elif payload["type"] == "result":
#                     result_data = payload

#                 elif payload["type"] == "done":
#                     break

#     except requests.exceptions.ConnectionError:
#         st.error("Cannot reach FastAPI. Run: `uvicorn app.main:app --reload`")
#     except Exception as e:
#         st.error(f"Error: {e}")

#     # Final node states
#     if result_data:
#         for k in active_nodes:
#             render_node(
#                 node_placeholders[k],
#                 k.capitalize(),
#                 {"generate":"NL → SQL","execute":"Run in SQLite","reflect":"Analyse error","done":"Return results"}.get(k,""),
#                 "done" if result_data.get("success") else "error",
#             )
#         if result_data.get("success"):
#             render_node(node_placeholders["done"], "Done", "Return results", "done")

#     # Render results
#     if result_data and result_data.get("success"):
#         cols = result_data.get("columns", [])
#         rows = result_data.get("rows", [])
#         attempts = result_data.get("attempts", 1)

#         with results_placeholder.container():
#             m1, m2, m3 = st.columns(3)
#             m1.metric("Rows", len(rows))
#             m2.metric("Columns", len(cols))
#             m3.metric("Attempts", attempts)

#             if cols and rows:
#                 df = pd.DataFrame(rows, columns=cols)
#                 st.dataframe(df, use_container_width=True)
#             else:
#                 st.info("Query executed successfully — no rows returned.")

#             with st.expander("Final SQL"):
#                 st.code(result_data.get("sql", ""), language="sql")
#     elif result_data:
#         results_placeholder.error(f"Agent failed after {result_data.get('attempts',1)} attempt(s).")

# elif run_clicked:
#     st.warning("Please enter a question.")





import streamlit as st
import requests
import json
import pandas as pd
import time
from dotenv import load_dotenv
import os

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(
    page_title="SQL Reflection Agent",
    page_icon="⟳",
    layout="wide",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.node-row { display: flex; gap: 12px; align-items: center; margin: 12px 0; }
.node-box {
    padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    border: 1.5px solid #333; color: #888; background: #1a1a1f;
    text-align: center; min-width: 130px;
}
.node-box.active { border-color: #00d4a0; color: #00d4a0; background: #001a14; }
.node-box.done   { border-color: #40d080; color: #40d080; background: #001a0d; }
.node-box.error  { border-color: #f04060; color: #f04060; background: #1a0010; }
.arrow { color: #444; font-size: 18px; }
.step-gen     { border-left: 3px solid #00d4a0; padding-left: 10px; }
.step-execute { border-left: 3px solid #40d080; padding-left: 10px; }
.step-reflect { border-left: 3px solid #f0a500; padding-left: 10px; }
.step-error   { border-left: 3px solid #f04060; padding-left: 10px; }
.step-done    { border-left: 3px solid #40d080; padding-left: 10px; }
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600; margin-left: 8px;
}
.badge-gen     { background: #001a14; color: #00d4a0; border: 1px solid #00d4a080; }
.badge-execute { background: #001a0d; color: #40d080; border: 1px solid #40d08080; }
.badge-reflect { background: #1a1000; color: #f0a500; border: 1px solid #f0a50080; }
.badge-error   { background: #1a0010; color: #f04060; border: 1px solid #f0406080; }
.badge-done    { background: #001a0d; color: #40d080; border: 1px solid #40d08080; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🤖 SQL Reflection Agent")
st.markdown("LangGraph · LangChain · Ollama · SQLite")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Config")
    max_attempts = st.slider("Max reflection attempts", 1, 5, 3)

    st.markdown("### 🗄️ Schema")
    try:
        schema_resp = requests.get(f"{API_BASE}/schema", timeout=3)
        if schema_resp.ok:
            schema_data = schema_resp.json()
            for table, cols in schema_data["tables"].items():
                with st.expander(f"📋 {table}"):
                    for col in cols:
                        pk = " 🔑" if col["pk"] else ""
                        st.code(f"{col['name']}  {col['type']}{pk}", language=None)
    except Exception:
        st.warning("API not reachable. Start FastAPI first.")

    st.markdown("### 💡 Try these")
    suggestions = [
        "Calculate total revenue for each product category.",
        "Rank customers by number of orders, show their rank and total spend",
        "For each order, show customer's previous order date.",
        "Get orders where quantity is greater than average quantity of that product",
        "Average order value by category",
        "Customers who never placed an order",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s}"):
            st.session_state["question"] = s

    st.markdown("---")
    st.markdown("### 🔧 Ollama")
    st.code("OLLAMA_ORIGINS='*' ollama serve", language="bash")

# ── Main input ────────────────────────────────────────────────────────────────
question = st.text_area(
    "Ask a question about the database",
    value=st.session_state.get("question", ""),
    placeholder="e.g. Show me top 5 customers by total order value",
    height=80,
    key="question_input",
)

run_col, _ = st.columns([1, 5])
run_clicked = run_col.button("▶ Run Agent", type="primary", use_container_width=True)

# ── Node graph UI ─────────────────────────────────────────────────────────────
st.markdown("### Agent Loop")
node_cols = st.columns([3, 1, 3, 1, 3, 1, 3])
node_placeholders = {
    "generate": node_cols[0].empty(),
    "execute":  node_cols[2].empty(),
    "reflect":  node_cols[4].empty(),
    "done":     node_cols[6].empty(),
}
node_cols[1].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)
node_cols[3].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)
node_cols[5].markdown("<div style='text-align:center;font-size:20px;padding-top:8px'>→</div>", unsafe_allow_html=True)

def render_node(placeholder, label, subtitle, state="idle"):
    placeholder.markdown(
        f'<div class="node-box {state}">{label}<br/>'
        f'<span style="font-size:10px;font-weight:400;opacity:0.7">{subtitle}</span></div>',
        unsafe_allow_html=True,
    )

def reset_nodes():
    render_node(node_placeholders["generate"], "Generate SQL",  "NL → SQL")
    render_node(node_placeholders["execute"],  "Execute",       "Run in SQLite")
    render_node(node_placeholders["reflect"],  "Reflect",       "Analyse error")
    render_node(node_placeholders["done"],     "Done",          "Return results")

reset_nodes()

NODE_MAP = {
    "generate": "generate",
    "execute":  "execute",
    "error":    "execute",
    "reflect":  "reflect",
    "done":     "done",
}

# ── Step log + results placeholders ──────────────────────────────────────────
st.markdown("### Step Log")
timeline_placeholder = st.empty()

st.markdown("### Results")
results_placeholder = st.empty()

# ── Run agent ─────────────────────────────────────────────────────────────────
if run_clicked and question.strip():
    steps = []
    result_data = None

    reset_nodes()
    timeline_placeholder.info("Agent running…")
    results_placeholder.empty()

    active_nodes = set()

    # Check API is reachable before streaming
    try:
        requests.get(f"{API_BASE}/health", timeout=3)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach FastAPI. Run: `python run.py`")
        st.stop()

    # Stream agent execution
    try:
        with requests.post(
            f"{API_BASE}/query/stream",
            json={"question": question.strip(), "max_attempts": max_attempts},
            stream=True,
            timeout=360,
        ) as resp:
            for raw_line in resp.iter_content(chunk_size=None):
                if not raw_line:
                    continue

                # iter_content returns bytes; split on newlines manually
                for line in raw_line.decode("utf-8").splitlines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue

                    try:
                        payload = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    if payload["type"] == "step":
                        step = payload["step"]
                        steps.append(step)
                        step_type = step.get("step", "")

                        node_key = NODE_MAP.get(step_type)
                        if node_key:
                            for k in list(active_nodes):
                                render_node(
                                    node_placeholders[k],
                                    k.capitalize(),
                                    {"generate": "NL → SQL", "execute": "Run in SQLite",
                                     "reflect": "Analyse error", "done": "Return results"}.get(k, ""),
                                    "done" if step_type != "error" else "error",
                                )
                            active_nodes = {node_key}
                            render_node(
                                node_placeholders[node_key],
                                node_key.capitalize(),
                                {"generate": "NL → SQL", "execute": "Run in SQLite",
                                 "reflect": "Analyse error", "done": "Return results"}.get(node_key, ""),
                                "active",
                            )

                        with timeline_placeholder.container():
                            for i, s in enumerate(steps):
                                stype = s.get("step", "generate")
                                badge_map = {
                                    "generate": ("badge-gen",     "GENERATE"),
                                    "execute":  ("badge-execute", "EXECUTE"),
                                    "reflect":  ("badge-reflect", "REFLECT"),
                                    "error":    ("badge-error",   "ERROR"),
                                    "done":     ("badge-done",    "DONE"),
                                }
                                badge_cls, badge_label = badge_map.get(stype, ("badge-gen", stype.upper()))
                                with st.expander(
                                    f"{str(i+1).zfill(2)}  {s.get('title', '')}",
                                    expanded=(i == len(steps) - 1),
                                ):
                                    if s.get("reasoning"):
                                        st.markdown(f"**Reasoning:** {s['reasoning']}")
                                    if s.get("sql"):
                                        st.code(s["sql"], language="sql")
                                    if s.get("error"):
                                        st.error(s["error"])

                    elif payload["type"] == "result":
                        result_data = payload

                    elif payload["type"] == "done":
                        break

    except Exception as e:
        st.error(f"Streaming error: {e}")

    # ── Final node states ─────────────────────────────────────────────────────
    if result_data:
        for k in active_nodes:
            render_node(
                node_placeholders[k],
                k.capitalize(),
                {"generate": "NL → SQL", "execute": "Run in SQLite",
                 "reflect": "Analyse error", "done": "Return results"}.get(k, ""),
                "done" if result_data.get("success") else "error",
            )
        if result_data.get("success"):
            render_node(node_placeholders["done"], "Done", "Return results", "done")

    # ── Render results ────────────────────────────────────────────────────────
    if result_data and result_data.get("success"):
        cols = result_data.get("columns", [])
        rows = result_data.get("rows", [])
        attempts = result_data.get("attempts", 1)

        with results_placeholder.container():
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows", len(rows))
            m2.metric("Columns", len(cols))
            m3.metric("Attempts", attempts)

            if cols and rows:
                df = pd.DataFrame(rows, columns=cols)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Query executed successfully — no rows returned.")

            with st.expander("Final SQL"):
                st.code(result_data.get("sql", ""), language="sql")

    elif result_data:
        results_placeholder.error(f"Agent failed after {result_data.get('attempts', 1)} attempt(s).")

    elif not result_data and steps:
        results_placeholder.warning("Stream ended without a result. Check terminal for errors.")

elif run_clicked:
    st.warning("Please enter a question.")