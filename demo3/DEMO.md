# Demo 3 — Follow-Up / Recovery Agent

**Status: VERIFIED RUNNING** (2026-09-23)

## What it is
A real lead follow-up/recovery service: ingests a leads CSV, flags stale leads with
real date arithmetic, and generates personalized follow-up messages (WhatsApp + email
variants) via a Jinja2 template engine. SQLite storage, minimal dashboard UI.

## What was verified
- `POST /api/upload` with `sample_leads.csv` → 12 leads ingested, 0 errors
- `GET /api/stale?days=14` → 5 stale flagged with correct `days_since_contact`
  (Neha Kapoor 18d, Amit Verma 49d, Sunita Rao 46d, Arjun Nair 65d, Meena Iyer 34d);
  recent leads (2–10 days) and `cold`-stage leads correctly excluded
- `POST /api/generate` → 5 personalized messages; name/business/days/value
  interpolated; stage-specific angles (quote_sent vs negotiating differ)
- `GET /docs` → 200, `GET /` → dashboard UI

## Run it

```bash
# one-time setup
python3 -m venv ~/.venvs-demo3
~/.venvs-demo3/bin/pip install --no-cache-dir -r requirements.txt

# boot
cd ~/workspace/playbook-phase1/demo3
~/.venvs-demo3/bin/uvicorn app:app --host 127.0.0.1 --port 18022
```

## Try it

```bash
# upload leads (columns: name,business,phone_or_email,channel,last_contact_date,stage,quoted_value,notes)
curl -X POST http://127.0.0.1:18022/api/upload -F "file=@sample_leads.csv"

# list all leads with computed days-since-contact
curl http://127.0.0.1:18022/api/leads

# flag stale leads (last contact older than N days, stages new/quote_sent/negotiating)
curl "http://127.0.0.1:18022/api/stale?days=14"

# generate personalized follow-ups for stale leads
curl -X POST "http://127.0.0.1:18022/api/generate?stale_only=true"
```

## Use with a real lead list
1. Export your leads to CSV with the exact column headers above (`stage` must be one
   of: new, quote_sent, negotiating, cold; `channel`: whatsapp or email;
   `last_contact_date`: YYYY-MM-DD).
2. Upload via the dashboard at `http://127.0.0.1:18022/` or the API.
3. Copy the generated messages — review before sending (nothing here sends anything).

## Optional LLM upgrade
Set `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) in the environment and use
`POST /api/generate-llm` to have an LLM rewrite the template drafts. Without a key,
the service runs fully on the local template engine.
