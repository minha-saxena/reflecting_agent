import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db.seed import get_connection
from app.core.config import settings
from app.utils.logger import get_logger

# Configure root logger once — all app.* loggers inherit this level
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

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
    get_connection()
    logger.info("DB seeded and ready.")
    logger.info("Model: %s @ %s", settings.OLLAMA_MODEL, settings.OLLAMA_BASE_URL)
    logger.info(
        "Ollama retry config: max_retries=%d, retry_delay=%.1fs",
        settings.OLLAMA_MAX_RETRIES,
        settings.OLLAMA_RETRY_DELAY,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)