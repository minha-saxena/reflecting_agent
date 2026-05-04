# SQL Reflection Agent

A LangGraph-powered reflection agent that translates natural language questions into SQL queries, executes them against a SQLite database, and **reflects on its own errors** to self-correct — looping until it gets it right or hits the max attempt limit.

```
[Generate SQL] → [Execute] → success → [Done]
                     ↓ error
                 [Reflect]
                     ↓
               [Generate SQL]  ← retries with reflection context
               (max 3 attempts)
```

## Stack

| Layer | Tech |
|---|---|
| Agent framework | LangGraph + LangChain |
| LLM | Ollama (qwen2.5-coder / mistral:7b) |
| Backend API | FastAPI + SSE streaming |
| Frontend | Streamlit |
| Database | SQLite in-memory |

---

## Project Structure

```
sql_reflection_agent/
├── app/
│   ├── agent/
│   │   ├── graph.py      # LangGraph graph — reflection loop
│   │   ├── nodes.py      # generate_sql, execute_sql, reflect, done nodes
│   │   ├── state.py      # AgentState TypedDict
│   │   └── tools.py      # SQL execution tool
│   ├── api/
│   │   └── routes.py     # FastAPI routes (/query, /query/stream, /schema, /health)
│   ├── core/
│   │   └── config.py     # Settings via pydantic-settings + .env
│   ├── db/
│   │   └── seed.py       # SQLite in-memory setup + sample e-commerce data
│   └── main.py           # FastAPI app entrypoint
├── streamlit_app/
│   └── app.py            # Streamlit UI
├── .env.example
├── requirements.txt
├── run.py                # Single-command launcher
└── README.md
```

---

## Quickstart

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running

### 2. Pull a model

```bash
ollama pull qwen2.5-coder   # recommended for SQL
# or
ollama pull mistral:7b 
```

### 3. Start Ollama with CORS enabled

```bash
OLLAMA_ORIGINS="*" ollama serve
```

### 4. Clone and set up

```bash
git clone <your-repo>
cd sql_reflection_agent

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 5. Configure environment

```bash
cp .env.example .env
# Defaults work out of the box — edit only if your Ollama setup differs
```

### 6. Run

```bash
python run.py
```

- Streamlit UI → http://localhost:8501
- FastAPI docs → http://localhost:8000/docs

Press `Ctrl+C` to stop both servers.

---

## API Endpoints

### `GET /api/health`
Returns service status and configured model.

### `GET /api/schema`
Returns the database schema as JSON.

### `POST /api/query`
Blocking endpoint. Runs the full agent and returns the complete result.

```json
{
  "question": "Top 5 customers by total spend",
  "max_attempts": 3
}
```

Response:
```json
{
  "success": true,
  "sql": "SELECT ...",
  "columns": ["name", "total"],
  "rows": [["Alice", 1329.98], ...],
  "attempts": 1,
  "step_log": [...]
}
```

### `POST /api/query/stream`
Streaming SSE endpoint. Emits each agent step in real-time as the agent runs.

Each event is one of:
- `{"type": "step", "step": {...}}` — a new step in the agent loop
- `{"type": "result", "success": true, "columns": [...], "rows": [...]}` — final result
- `{"type": "done"}` — stream complete

---

## How the Reflection Loop Works

The agent is built as a **LangGraph StateGraph** with 4 nodes:

1. **`generate_sql`** — calls Ollama with the question + schema (+ reflection notes if retrying). Extracts SQL from the response.
2. **`execute_sql`** — runs the SQL against SQLite. On error, sets `error` in state.
3. **`reflect`** — if there was an error, calls Ollama again asking it to explain what went wrong and how to fix it. Stores the reflection in state.
4. **`done`** — logs the final success step.

The **conditional edge** after `execute_sql` decides:
- `success=True` → go to `done`
- `error` + `attempt < max_attempts` → go to `reflect` → back to `generate_sql`
- `error` + `attempt >= max_attempts` → go to `END` (give up)

The key insight: on retry, `generate_sql` receives **both the original error AND the LLM's own reflection** about what went wrong — this is what makes it a reflection agent, not just a retry loop.

---

## Sample Data

The in-memory SQLite DB is seeded with e-commerce data on startup:

- **customers** — 8 records (name, email, city, joined_date)
- **products** — 10 records across Electronics, Furniture, Stationery
- **orders** — 18 records with status: completed / pending / cancelled

---

## Changing the Model

Edit `.env`:

```env
OLLAMA_MODEL=llama3.2
```

Restart with `python run.py`.

---

## Extending the POC

Some ideas to take this further:

- **Connect a real DB** — swap `seed.py` for a PostgreSQL/MySQL connection string
- **Add memory** — use LangGraph's checkpointing to remember past queries in a session
- **Multi-agent** — add a validator agent that checks SQL before execution
- **Tool calling** — expose `execute_sql` as a proper LangChain tool and let the LLM decide when to call it
- **Evaluation** — log all attempts + reflections to a file to measure model accuracy