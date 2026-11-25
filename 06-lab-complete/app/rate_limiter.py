"""Atomic sliding window shared by workers and preserved across app restarts."""
import uuid
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r, credential_id

# Redis server time avoids clock differences between application instances.
WINDOW_SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local window = 60000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], window)
return 0
"""

def check_rate_limit(key: str) -> None:
    retry_after = int(r.eval(
        WINDOW_SCRIPT, 1, "day14:rate:" + credential_id(key),
        settings.rate_limit_per_minute, uuid.uuid4().hex,
    ))
    if retry_after:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
