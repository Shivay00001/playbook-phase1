# Playbook Phase 1 (Days 1–14) — BUILD Report
**Date:** 2026-09-23 · **Everything below was actually run locally. No mocks, no fake data.**

## What runs (verified)

### Demo 1 — Lead Response Agent ✅
Re-verified the existing `whatsapp-ai-agent` (FastAPI + LiteLLM + Next.js). Boots, `/docs` 200,
settings endpoints 200, Meta webhook parses messages → 200. Live AI/Twilio/Meta paths need real keys (by design).
- Run: see [demo1/DEMO.md](demo1/DEMO.md)

### Demo 2 — Support Resolution Agent ✅ (built new)
FastAPI + TF-IDF cosine-similarity FAQ matcher over editable `kb.json` (18 Q&As for a mock
e-commerce store). **5/5 test questions answered correctly** (conf 0.41–0.80); nonsense input
escalates to human instead of hallucinating. Chat UI included. Optional LiteLLM path via env key.
- Boot: `cd demo2 && ~/.venvs-demo2/demo2/bin/uvicorn app:app --port 18021` (~30s for sklearn import)
- Test: `curl -X POST localhost:18021/api/ask -H 'Content-Type: application/json' -d '{"question":"how long does shipping take"}'`
- Docs: [demo2/DEMO.md](demo2/DEMO.md) · [demo2/TEST_LOG.md](demo2/TEST_LOG.md)

### Demo 3 — Follow-Up / Recovery Agent ✅ (built new)
FastAPI + SQLite: uploads a leads CSV, flags stale leads with **real date arithmetic**,
generates personalized WhatsApp + email follow-ups via Jinja2 templates. Verified on 12 sample
leads: 12 ingested, 5 correctly flagged stale (18/49/46/65/34 days), recent + cold correctly
excluded, messages interpolate name/business/days/value with stage-specific angles.
- Boot: `cd demo3 && ~/.venvs-demo3/bin/uvicorn app:app --port 18022`
- Test: `curl -X POST localhost:18022/api/upload -F "file=@sample_leads.csv"` then `curl "localhost:18022/api/stale?days=14"`
- Docs: [demo3/DEMO.md](demo3/DEMO.md) · [demo3/TEST_LOG.md](demo3/TEST_LOG.md)

### Offer site ✅
Single self-contained page: [offer-site/index.html](offer-site/index.html) — "VisionQuantech Revenue
Agents": 3 demos with measured outcomes, pricing tables (India INR + international local-currency
figures from the official pricing file), 14-day install steps, outcome guarantee, "Book a free audit"
CTA. Mobile-friendly, no phone numbers, no lorem ipsum. Validated HTML.

### Pipeline tracker ✅
[tracker/pipeline-tracker.html](tracker/pipeline-tracker.html) — 65 real prospects (50 Jev-scored leads
+ 14 follow-ups + 1 emailed), columns Prospect | Stage | Est. value | Next action | Date, with search
+ stage filter. Stages reflect verified sends only. No invented data.

### Message templates ✅
[templates/outreach-templates.md](templates/outreach-templates.md) — LinkedIn, cold email, community
post, pilot close script (with real pricing), 4-step follow-up sequence. Adapted from playbook
appendix 21.1–21.2. Placeholders marked: `[LOOM LINK]`, `[OFFER SITE LINK]`, `[CALENDLY LINK]`.

## Exact run commands (all three demos)

```bash
# Demo 1 (Lead Response)
mkdir -p /tmp/demo1-run && cd /tmp/demo1-run
DATABASE_URL="sqlite+aiosqlite:///./whatsapp.db" \
PYTHONPATH=~/workspace/gh-cleanup/all-repos/ai-multi-agent-system/whatsapp-ai-agent/backend \
~/.wa-venv/bin/uvicorn server:app --port 8123

# Demo 2 (Support) — venv already at ~/.venvs-demo2/demo2
cd ~/workspace/playbook-phase1/demo2 && ~/.venvs-demo2/demo2/bin/uvicorn app:app --port 18021

# Demo 3 (Follow-Up) — venv already at ~/.venvs-demo3
cd ~/workspace/playbook-phase1/demo3 && ~/.venvs-demo3/bin/uvicorn app:app --port 18022
```

## What is left for Shivay himself
1. **Payments:** sign up for Stripe + Wise + Payoneer (takes minutes; needed before any deposit).
2. **Booking link:** create a Calendly "Free audit" event and replace `calendly.com/YOUR-LINK` in
   `offer-site/index.html`; replace `hello@visionquantech.com` with the real inbox.
3. **Loom recordings:** record one 60–90s Loom per demo (scripts: show the ROI — sub-60s reply,
   ticket auto-resolved, stale quote revived) and replace `[LOOM LINK]` in templates.
4. **(Optional) Publish:** the offer site is a single HTML file — upload to Cloudflare Pages /
   any static host as-is. The demos deploy as: frontends → Cloudflare Pages, APIs → Render,
   DB → Supabase (SQLite→Postgres swap documented in each DEMO.md).
5. **Real keys (only when selling):** LLM key for live AI replies, Twilio/Meta credentials for
   Demo 1's live WhatsApp paths. Nothing here needs them to demo.

## Notes
- Two child agents died mid-build in a daemon restart; Demo 3's code survived and was verified
  as-is, Demo 2 was completed directly. One real bug was found and fixed during Demo 2 testing
  (keyword-boost in the matcher — documented in its TEST_LOG.md).
- Nothing was committed or pushed to any git repo; all venvs live in `~/.venvs-*`, outside the workspace.
