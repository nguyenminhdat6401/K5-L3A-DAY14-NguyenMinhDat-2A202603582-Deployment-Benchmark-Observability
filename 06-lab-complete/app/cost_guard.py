"""Daily UTC budget per configured API credential, persisted in Redis.

The mock exposes no token usage, so main.py supplies a documented estimate.
Checking prior spend and recording actual usage permits in-flight overshoot;
strict production budgets require preauthorization/reservation before the LLM call.
"""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r, credential_id

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

def budget_key() -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"day14:cost:{credential_id(settings.agent_api_key)}:{day}"

def check_budget() -> None:
    spent = float(r.get(budget_key()) or 0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")

def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    # Atomic increment prevents concurrent workers from losing recorded costs.
    key = budget_key()
    with r.pipeline(transaction=True) as pipe:
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, 172800)
        pipe.execute()
    return cost
