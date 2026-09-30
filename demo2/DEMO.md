# Demo 2 — Support Resolution Agent

**Status: VERIFIED RUNNING** (2026-09-23)

## What it is
A real FAQ/support triage service for a mock e-commerce store ("DemoKart"):
FastAPI + TF-IDF cosine-similarity matching over an editable local knowledge base
(`kb.json`, 18 Q&A pairs). No API key needed. Low-confidence queries escalate to a
human honestly instead of hallucinating. Minimal chat UI included.

## What was verified
- `GET /docs` → 200; `GET /api/kb` → 18 entries; `POST /api/kb/reload` works
- 5/5 real test questions answered correctly (confidences 0.41–0.80)
- Nonsense input → escalated, not answered
- Matching = 0.75 × TF-IDF cosine + 0.25 × keyword hit — deterministic, explainable

## Run it

```bash
# one-time setup
python3 -m venv ~/.venvs-demo2
~/.venvs-demo2/bin/pip install --no-cache-dir -r requirements.txt

# boot (takes ~30s — scikit-learn import is slow)
cd ~/workspace/playbook-phase1/demo2
~/.venvs-demo2/bin/uvicorn app:app --host 127.0.0.1 --port 18021
```

## Try it

```bash
curl -X POST http://127.0.0.1:18021/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"how long does shipping take"}'
# → {"answer":"Standard shipping takes 3-5 business days…","matched_q":"How long does shipping take?","confidence":0.803,"escalated":false}

# chat UI:
open http://127.0.0.1:18021/
```

## Customize for a real client
1. Edit `kb.json` — replace the DemoKart Q&As with the client's real FAQs
   (fields: id, question, answer, keywords, category).
2. `curl -X POST http://127.0.0.1:18021/api/kb/reload` — no restart needed.
3. Tune `ESCALATE_THRESHOLD` in `app.py` (default 0.25) if the client wants
   more/fewer escalations.

## Optional LLM upgrade
Set `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) + `pip install litellm`: low-confidence
queries are then answered by the LLM grounded on the KB instead of escalating.
Without a key the service runs fully offline.
