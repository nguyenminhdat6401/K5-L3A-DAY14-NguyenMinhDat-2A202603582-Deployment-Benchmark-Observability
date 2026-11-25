# Deployment Information

## Public URL

https://lab14-agent.onrender.com

## Platform and resources

- Platform: Render, workspace My Workspace, region Oregon.
- Agent: lab14-agent, Docker web service, Free compute ($0/month).
- Redis-compatible datastore: lab14-redis, Render Key Value (Valkey 8.1.10), Free compute ($0/month, 25 MB RAM, 50 connections).
- Source: main branch, commit 21d557eb5d45559ef8a1c84ba035f89f70e756d1.
- Root directory: 06-lab-complete; Docker build context: .; Dockerfile: ./Dockerfile.
- Health check: /health; Uvicorn binds the PORT supplied by Render (10000 in observed logs).
- Deployment observed: Deploy succeeded | Live, 25/11/2026 at approximately 16:15 GMT+7; dashboard duration 40.9 seconds.

## Dashboard links

- Agent: https://dashboard.render.com/web/srv-dc3adqifngtc73deom8g
- Deployment: https://dashboard.render.com/web/srv-dc3adqifngtc73deom8g/deploys/dep-dc3adqqfngtc73deomr0
- Key Value: https://dashboard.render.com/r/red-dc3acqvlot8c739ji57g

Dashboard links require the owner's login; the public API URL above is accessible without dashboard access.

## Environment variables

- ENVIRONMENT=production
- AGENT_API_KEY: generated random secret, stored only in Render service environment.
- REDIS_URL: private connection URL of lab14-redis in the same region; no public datastore access enabled.
- RATE_LIMIT_PER_MINUTE=10
- DAILY_BUDGET_USD=1.0
- PORT: supplied by Render.

The API key is intentionally omitted. The owner can retrieve it from lab14-agent → Environment in Render. No provider LLM key is needed: this app uses the supplied mock LLM.

## Reproduce the four CP6 checks

Run in Bash. Enter the existing Render API key at the hidden prompt, not directly in a command saved to shell history.

```bash
BASE='https://lab14-agent.onrender.com'
read -s -p 'API key: ' AGENT_API_KEY
printf '\n'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
unset AGENT_API_KEY
```

## Actual verification — 25/11/2026

These requests were executed against the public HTTPS endpoint after Render reported Live:

| Request | Observed HTTP | Body |
|---|---:|---|
| GET /health | 200 | {"status":"ok","uptime_seconds":31.6,"environment":"production"} |
| GET /ready | 200 | {"ready":true} |
| POST /ask, no key | 401 | {"detail":"Missing or invalid API key"} |
| POST /ask, correct key | 200 | Response below |

```json
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"input_tokens_estimated":2,"output_tokens_estimated":23,"cost_usd":1.4099999999999997e-05}}
```

## Free-tier limits

The free web service can sleep during inactivity, so the first request may take longer. Free Key Value has no disk persistence and can lose data on a datastore restart; Redis state survives app restarts while the datastore itself remains online. This is the lab deployment, not a guarantee of durable production storage. Budget figures are mock estimates, not charges from an LLM provider.

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Public health endpoint](screenshots/running.png)
- [Four HTTP checks, API key hidden](screenshots/test.png)

All three files are present; test.png was visually checked and shows 200,200,401,200 without the API key.
