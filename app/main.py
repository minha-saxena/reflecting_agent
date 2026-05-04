from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db.seed import get_connection  # warm up DB on startup
from app.core.config import settings

app = FastAPI(
    title="SQL Reflection Agent",
    description="LangGraph-powered reflection agent for natural language SQL queries",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def startup():
    get_connection()  # initialise in-memory SQLite
    print(f"✓ DB seeded")
    print(f"✓ Model: {settings.OLLAMA_MODEL} @ {settings.OLLAMA_BASE_URL}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
