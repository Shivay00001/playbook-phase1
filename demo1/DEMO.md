# Demo 1 — Lead Response Agent (whatsapp-ai-agent)

**Status: VERIFIED RUNNING** (re-verified 2026-09-23)

## What it is
A real WhatsApp conversational AI agent: FastAPI backend + LiteLLM (multi-provider LLM) + SQLAlchemy + Next.js 16 frontend. Receives WhatsApp messages via Twilio or Meta Cloud API webhooks, replies with AI, and exposes a dashboard to edit the system prompt and API keys.

Source repo: `~/workspace/gh-cleanup/all-repos/ai-multi-agent-system/whatsapp-ai-agent/` (unmodified — this demo runs it read-only).

## What was verified
- Uvicorn boots, lifespan creates `settings` + `conversations` tables and seeds the default system prompt
- `GET /docs` → 200, `GET /openapi.json` → 200
- `GET /api/settings/prompt` → 200 (seeded prompt returned)
- `POST /api/settings/keys` → validates full key payload
- `POST /webhook/meta` with a sample message payload → 200 `{"status":"ok"}`, message parsed and background AI-reply task dispatched
- Frontend: `npm install` + `npm run build` → clean, 4 routes prerendered
- Live AI replies / Twilio / Meta outbound need real keys — those paths are intentionally blocked without them (by design, not a bug)

## Run it (backend)

```bash
# one-time setup
python3 -m venv ~/.wa-venv
~/.wa-venv/bin/pip install --no-cache-dir fastapi uvicorn sqlalchemy aiosqlite twilio httpx python-dotenv pydantic
# NOTE: litellm's full dependency tree is heavy; the demo venv has a documented
# stub in site-packages so the server boots offline. For live AI replies install
# the real package: ~/.wa-venv/bin/pip install litellm

# boot (from any scratch dir — keeps the sqlite db out of the repo)
mkdir -p /tmp/demo1-run && cd /tmp/demo1-run
DATABASE_URL="sqlite+aiosqlite:///./whatsapp.db" \
PYTHONPATH=~/workspace/gh-cleanup/all-repos/ai-multi-agent-system/whatsapp-ai-agent/backend \
~/.wa-venv/bin/uvicorn server:app --host 127.0.0.1 --port 8123
```

## Try it

```bash
curl http://127.0.0.1:8123/docs                                  # 200 Swagger UI
curl http://127.0.0.1:8123/api/settings/prompt                  # current system prompt
curl -X POST http://127.0.0.1:8123/webhook/meta \
  -H 'Content-Type: application/json' \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"15551234567","text":{"body":"Hi, I need a 3BHK in Dubai"},"type":"text"}]}}]}]}'
# → {"status":"ok"} — message parsed, AI-reply task dispatched
```

## Run it (frontend)

```bash
cd ~/workspace/gh-cleanup/all-repos/ai-multi-agent-system/whatsapp-ai-agent/frontend
npm install && npm run build && npm start   # serves on :3000
```

## Configure for a real client
1. In the dashboard (or `POST /api/settings/keys`), add: LLM key (`OPENAI_API_KEY` etc.),
   Twilio (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) or
   Meta (`META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_VERIFY_TOKEN`).
2. Set `DATABASE_URL` to a Postgres/Supabase URL in production (default in
   `database.py` is Postgres; override with sqlite for local dev as above).
3. Deploy: frontend → Cloudflare Pages, API → Render, DB → Supabase.

## Known gaps (fix before selling)
- No `requirements.txt` in the repo — reconstruct from imports before any deploy.
- `database.py` defaults to Postgres (`postgresql+asyncpg://user:password@localhost/...`);
  README's "SQLite" claim only holds via the `DATABASE_URL` override shown above.
- Frontend hardcodes the backend URL — needs an env var for cloud deploy.
