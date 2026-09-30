"""
Demo 3 — Follow-Up/Recovery Agent (VisionQuantech Playbook Phase 1).

Real, working software: no mocks, no simulated data. Date arithmetic is done
with datetime.date against the machine's actual current date.

Run:
    uvicorn app:app --port 18022
"""

import csv
import io
import os
import sqlite3
import threading
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import HTMLResponse
from jinja2 import Template

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.db")

REQUIRED_COLUMNS = [
    "name", "business", "phone_or_email", "channel",
    "last_contact_date", "stage", "quoted_value", "notes",
]

VALID_CHANNELS = {"whatsapp", "email"}
VALID_STAGES = {"new", "quote_sent", "negotiating", "cold"}
STALE_ELIGIBLE_STAGES = ("quote_sent", "negotiating", "new")  # cold excluded


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            business TEXT NOT NULL,
            phone_or_email TEXT,
            channel TEXT NOT NULL,
            last_contact_date TEXT NOT NULL,
            stage TEXT NOT NULL,
            quoted_value REAL NOT NULL DEFAULT 0,
            notes TEXT
        )"""
    )
    return conn


db_lock = threading.Lock()
get_db().close()

app = FastAPI(
    title="Demo 3 — Follow-Up/Recovery Agent",
    description=(
        "Lead follow-up/recovery from CSV. Flags stale leads with real date "
        "arithmetic and generates personalized per-channel follow-up messages."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Date logic (real, no fakes)
# ---------------------------------------------------------------------------

def days_since(last_contact: str) -> int:
    """Whole days between a lead's last_contact_date and the real today."""
    contacted = date.fromisoformat(last_contact)  # YYYY-MM-DD
    return (date.today() - contacted).days


def is_stale(lead: dict, days: int) -> bool:
    """Stale = older than N days AND stage is quote_sent/negotiating/new."""
    return lead["stage"] in STALE_ELIGIBLE_STAGES and days_since(lead["last_contact_date"]) > days


def enrich(lead_row) -> dict:
    lead = dict(lead_row)
    lead["days_since_contact"] = days_since(lead["last_contact_date"])
    lead["is_stale_default"] = is_stale(lead, 14)
    return lead


# ---------------------------------------------------------------------------
# Message generation — real Jinja2 templates, stage-specific angles
# ---------------------------------------------------------------------------

ANGLE_BY_STAGE = {
    "new": "reconnecting — you reached out a while back and I wanted to pick up the thread",
    "quote_sent": "checking on the quote we shared",
    "negotiating": "getting this over the line — happy to revisit terms so we can close it out",
    "cold": "re-engaging — a lot has improved since we last spoke",
}

WHATsapp_TMPL = Template(
    """Hi {{ name }}! This is from VisionQuantech. It's been {{ days }} days since we last connected about {{ business }}.
{% if stage == "quote_sent" -%}
Just checking on the quote we shared (₹{{ value }}). Still on your mind? Happy to walk you through it again.
{%- elif stage == "negotiating" -%}
Wanted to pick back up where we left off — happy to revisit terms so we can get this over the line. ₹{{ value }} is still locked in for this week.
{%- elif stage == "cold" -%}
Long time no talk! A lot has improved on our side since — quick 10-min call to see if it fits now? We've got a limited launch offer running this month.
{%- else -%}
You reached out a while back and I wanted to reconnect. Are you still exploring options for {{ business }}?
{%- endif %}
Let me know a good time to talk 👍"""
)

EMAIL_TMPL = Template(
    """Subject: Following up — {{ business }}{% if value %} · ₹{{ value }} quote{% endif %}

Hi {{ name }},

I hope you're doing well. It's been {{ days }} days since we last spoke about {{ business }}, and I'm reaching out about: {{ angle }}.

{% if stage == "quote_sent" -%}
To recap, the quote we shared was **₹{{ value }}** — it covers a fully managed AI setup with no hidden costs. Happy to walk you through any part of it again, or adjust the scope if your needs have shifted.
{%- elif stage == "negotiating" -%}
We were in the middle of working out the terms (₹{{ value }}), and I'd love to get this over the line. I'm happy to revisit the numbers this week — the quote stays locked in, no surprises later.
{%- elif stage == "cold" -%}
A lot has improved on our side since we last spoke, and we're running a limited launch offer this month. Would a quick 10-minute call make sense to see if the timing is better now?
{%- else -%}
You reached out a while back, and I wanted to pick up the thread. Are you still exploring options for {{ business }}? Happy to share a short demo tailored to what you do.
{%- endif %}

Just reply to this email and we'll take it from there.

Best,
VisionQuantech — AI agents & automation
"""
)


def generate_message(lead: dict) -> dict:
    days = lead["days_since_contact"]
    value = int(lead["quoted_value"]) if float(lead["quoted_value"]).is_integer() else lead["quoted_value"]
    ctx = {
        "name": lead["name"],
        "business": lead["business"],
        "days": days,
        "stage": lead["stage"],
        "value": f"{value:,}" if value else "",
        "angle": ANGLE_BY_STAGE[lead["stage"]],
    }
    return {
        "name": lead["name"],
        "business": lead["business"],
        "stage": lead["stage"],
        "days_since_contact": days,
        "quoted_value": lead["quoted_value"],
        "channel": lead["channel"],
        "whatsapp": WHATsapp_TMPL.render(**ctx),
        "email": EMAIL_TMPL.render(**ctx),
    }


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Accept a CSV upload, validate columns, store leads, return count + per-row errors."""
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    errors: List[str] = []
    rows: List[dict] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        return {"ok": False, "count": 0, "errors": [f"Missing columns: {', '.join(missing)}"]}

    for i, r in enumerate(reader, start=2):  # line 2 = first data row
        row = {k: (r.get(k) or "").strip() for k in REQUIRED_COLUMNS}
        row_errors = []
        if not row["name"]:
            row_errors.append("name is empty")
        if not row["business"]:
            row_errors.append("business is empty")
        if row["channel"].lower() not in VALID_CHANNELS:
            row_errors.append(f"channel must be one of {sorted(VALID_CHANNELS)}")
        try:
            date.fromisoformat(row["last_contact_date"])
        except ValueError:
            row_errors.append("last_contact_date must be YYYY-MM-DD")
        if row["stage"].lower() not in VALID_STAGES:
            row_errors.append(f"stage must be one of {sorted(VALID_STAGES)}")
        try:
            row["quoted_value"] = float(row["quoted_value"] or 0)
        except ValueError:
            row_errors.append("quoted_value must be a number")
        if row_errors:
            errors.append(f"line {i}: {'; '.join(row_errors)}")
            continue
        rows.append(row)

    with db_lock:
        conn = get_db()
        conn.execute("DELETE FROM leads")
        for row in rows:
            conn.execute(
                "INSERT INTO leads (name, business, phone_or_email, channel, last_contact_date, stage, quoted_value, notes)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (row["name"], row["business"], row["phone_or_email"], row["channel"].lower(),
                 row["last_contact_date"], row["stage"].lower(), row["quoted_value"], row["notes"]),
            )
        conn.commit()
        conn.close()

    return {"ok": True, "count": len(rows), "errors": errors}


def _all_leads() -> List[dict]:
    with db_lock:
        conn = get_db()
        rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
        conn.close()
    return [enrich(r) for r in rows]


@app.get("/api/leads")
def list_leads():
    """List all ingested leads with computed days_since_contact / stale fields."""
    return {"count": len(_all_leads()), "leads": _all_leads()}


@app.get("/api/stale")
def stale_leads(days: int = Query(14, ge=0, description="Stale threshold in days")):
    """Leads whose last_contact_date is older than N days AND stage is quote_sent/negotiating/new."""
    leads = _all_leads()
    stale = [l for l in leads if is_stale(l, days)]
    return {
        "threshold_days": days,
        "today": date.today().isoformat(),
        "count": len(stale),
        "leads": stale,
    }


@app.post("/api/generate")
def generate_all(stale_only: bool = Query(True, description="Generate only for stale leads")):
    """Generate personalized per-channel follow-up messages (real Jinja2 templates)."""
    leads = _all_leads()
    if stale_only:
        leads = [l for l in leads if is_stale(l, 14)]
    messages = [generate_message(l) for l in leads]
    return {"count": len(messages), "messages": messages}


@app.post("/api/generate-llm")
def generate_llm():
    """
    Optional LLM upgrade: rewrites generated messages via LiteLLM.
    Requires OPENAI_API_KEY env var. Not required — /api/generate works without it.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return {
            "ok": False,
            "error": "LLM upgrade not configured. Set OPENAI_API_KEY to enable.",
        }
    try:
        import litellm  # noqa
    except ImportError:
        return {"ok": False, "error": "litellm is not installed. pip install litellm."}
    return {
        "ok": False,
        "error": "LLM rewriting is a placeholder hook — wire litellm.completion here with your key.",
    }


# ---------------------------------------------------------------------------
# Minimal dashboard UI
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Follow-Up / Recovery Agent — Demo 3</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.6rem; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { border: 1px solid #ddd; padding: .45rem .6rem; text-align: left; }
th { background: #f5f5f5; }
tr.stale { background: #fff3cd; }
.badge { display:inline-block; padding: .1rem .5rem; border-radius: 999px; font-size: .75rem; }
.badge.stale { background:#ffc107; color:#333; }
.badge.ok { background:#d4edda; color:#155724; }
pre.msg { white-space: pre-wrap; background: #f8f9fa; padding: .7rem; border-radius: 6px; font-size: .85rem; }
button { cursor: pointer; }
.row { display:flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
</style>
</head>
<body>
<h1>📞 Follow-Up / Recovery Agent <small style="font-weight:normal;color:#666">Demo 3 — Playbook Phase 1</small></h1>

<div class="card">
  <h3>1. Upload leads CSV</h3>
  <form id="upform" enctype="multipart/form-data">
    <input type="file" name="file" accept=".csv" required>
    <button type="submit">Upload</button>
  </form>
  <p id="upstatus"></p>
</div>

<div class="card">
  <h3>2. Stale threshold</h3>
  <div class="row">
    <label>Stale after <input id="days" type="number" value="14" min="0" style="width:4rem"> days</label>
    <button onclick="loadAll()">Refresh</button>
  </div>
</div>

<div class="card">
  <h3>3. Leads</h3>
  <table id="leadtbl"><thead><tr>
    <th>Name</th><th>Business</th><th>Channel</th><th>Stage</th>
    <th>Last contact</th><th>Days ago</th><th>Quoted ₹</th><th>Status</th>
  </tr></thead><tbody></tbody></table>
</div>

<div class="card">
  <h3>4. Generated follow-up messages (stale leads)</h3>
  <button onclick="generateMsgs()">Generate messages</button>
  <div id="msgs"></div>
</div>

<script>
async function loadAll(){
  const days = document.getElementById('days').value || 14;
  const [allRes, staleRes] = await Promise.all([
    fetch('/api/leads').then(r=>r.json()),
    fetch('/api/stale?days='+days).then(r=>r.json())
  ]);
  const staleIds = new Set(staleRes.leads.map(l=>l.id));
  const tb = document.querySelector('#leadtbl tbody');
  tb.innerHTML = '';
  for (const l of allRes.leads){
    const isStale = staleIds.has(l.id);
    const tr = document.createElement('tr');
    if (isStale) tr.className = 'stale';
    tr.innerHTML = `<td>${l.name}</td><td>${l.business}</td><td>${l.channel}</td>
      <td>${l.stage}</td><td>${l.last_contact_date}</td><td>${l.days_since_contact}</td>
      <td>${Number(l.quoted_value).toLocaleString('en-IN')}</td>
      <td><span class="badge ${isStale?'stale':'ok'}">${isStale?'NEEDS FOLLOW-UP':'fresh'}</span></td>`;
    tb.appendChild(tr);
  }
}
document.getElementById('upform').addEventListener('submit', async e=>{
  e.preventDefault();
  const fd = new FormData(e.target);
  const res = await fetch('/api/upload', {method:'POST', body:fd}).then(r=>r.json());
  document.getElementById('upstatus').textContent =
    `Uploaded: ${res.count} leads. ${res.errors && res.errors.length ? 'Errors: '+res.errors.join(' | ') : ''}`;
  loadAll();
});
async function generateMsgs(){
  const res = await fetch('/api/generate?stale_only=true', {method:'POST'}).then(r=>r.json());
  const box = document.getElementById('msgs');
  box.innerHTML = '';
  for (const m of res.messages){
    const d = document.createElement('div');
    d.className = 'card';
    d.innerHTML = `<h4>${m.name} — ${m.business} <small>(${m.stage}, ${m.days_since_contact} days)</small></h4>
      <h5>WhatsApp</h5><pre class="msg" id="wa-${m.name.replace(/\\s/g,'')}">${m.whatsapp}</pre>
      <button onclick="copyMsg('wa-${m.name.replace(/\\s/g,'')}')">Copy WhatsApp</button>
      <h5>Email</h5><pre class="msg" id="em-${m.name.replace(/\\s/g,'')}">${m.email}</pre>
      <button onclick="copyMsg('em-${m.name.replace(/\\s/g,'')}')">Copy email</button>`;
    box.appendChild(d);
  }
}
function copyMsg(id){
  const txt = document.getElementById(id).innerText;
  navigator.clipboard.writeText(txt).then(()=>alert('Copied to clipboard'));
}
loadAll();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=18022)
