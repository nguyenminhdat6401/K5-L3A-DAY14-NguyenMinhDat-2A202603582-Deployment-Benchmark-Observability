"""Production agent: auth, Redis limits, JSON logs and Uvicorn lifecycle."""
import json
import logging
import math
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for name in ("path", "method", "status", "ms", "cost_usd"):
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger("day14.agent")
START_TIME = time.monotonic()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    # Uvicorn handles SIGTERM and drains requests before lifespan cleanup.
    yield
    r.close()
    logger.info("shutdown_complete")

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value

@app.middleware("http")
async def log_request(request: Request, call_next):
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        logger.info("request", extra={
            "method": request.method, "path": request.url.path,
            "status": status, "ms": round((time.monotonic() - started) * 1000, 2),
        })

@app.exception_handler(redis.RedisError)
async def redis_error(request: Request, exc: redis.RedisError):
    logger.warning("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "State service unavailable"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failed", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": round(time.monotonic() - START_TIME, 1),
            "environment": settings.environment}

@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}

@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    check_budget()
    answer = llm_ask(body.question)
    # A reproducible approximation, not actual provider token accounting.
    input_tokens = max(1, math.ceil(len(body.question.encode("utf-8")) / 4))
    output_tokens = max(1, math.ceil(len(answer.encode("utf-8")) / 4))
    cost = record_cost(input_tokens, output_tokens)
    logger.info("llm_complete", extra={"cost_usd": cost})
    return {"question": body.question, "answer": answer,
            "usage": {"input_tokens_estimated": input_tokens,
                      "output_tokens_estimated": output_tokens, "cost_usd": cost}}
