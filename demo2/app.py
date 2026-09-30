"""
Demo 2 — Support Resolution Agent (VisionQuantech Playbook Phase 1).

Real, working software: TF-IDF cosine-similarity matching over a local,
editable knowledge base. No API key required. Optional LiteLLM upgrade
path for low-confidence queries when an LLM key is present in the env.

Run:
    uvicorn app:app --port 18021
"""

import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "kb.json")
ESCALATE_THRESHOLD = 0.25  # below this cosine score we escalate to a human

app = FastAPI(title="Demo 2 — Support Resolution Agent")

kb = []
vectorizer = None
tfidf_matrix = None


def load_kb():
    """(Re)load kb.json and rebuild the TF-IDF index."""
    global kb, vectorizer, tfidf_matrix
    with open(KB_PATH, encoding="utf-8") as f:
        kb = json.load(f)
    docs = [
        " ".join([e["question"]] + e.get("keywords", []) + [e.get("category", "")])
        for e in kb
    ]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    tfidf_matrix = vectorizer.fit_transform(docs)
    return len(kb)


load_kb()


class AskRequest(BaseModel):
    question: str


def keyword_hit(entry: dict, question: str) -> float:
    """1.0 if any of the entry's keywords appear in the question, else 0.0."""
    q = question.lower()
    q_tokens = set(q.split())
    for kw in entry.get("keywords", []):
        kw = kw.lower()
        if kw in q or any(tok in q_tokens for tok in kw.split()):
            return 1.0
    return 0.0


def match(question: str):
    """Return (best_entry, confidence).
    Blended score: 0.75 * TF-IDF cosine similarity + 0.25 * keyword hit.
    Genuine, deterministic, explainable — no fakes."""
    q_vec = vectorizer.transform([question])
    sims = cosine_similarity(q_vec, tfidf_matrix)[0]
    blended = [
        0.75 * float(s) + 0.25 * keyword_hit(entry, question)
        for entry, s in zip(kb, sims)
    ]
    best_idx = int(max(range(len(blended)), key=lambda i: blended[i]))
    return kb[best_idx], blended[best_idx]


def try_llm_fallback(question: str):
    """Optional upgrade path: only used when an LLM key exists in env."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import litellm

        context = "\n".join(f"Q: {e['question']}\nA: {e['answer']}" for e in kb)
        resp = litellm.completion(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are DemoKart support. Answer ONLY from the FAQ below. "
                    "If the FAQ doesn't cover it, say you'll escalate to a human.\n\n" + context,
                },
                {"role": "user", "content": question},
            ],
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


@app.get("/", response_class=HTMLResponse)
def ui():
    return CHAT_HTML


@app.get("/api/kb")
def get_kb():
    return {"count": len(kb), "entries": kb}


@app.post("/api/kb/reload")
def reload_kb():
    return {"ok": True, "count": load_kb()}


@app.post("/api/ask")
def ask(req: AskRequest):
    q = req.question.strip()
    if not q:
        return {"error": "empty question"}
    entry, conf = match(q)
    if conf >= ESCALATE_THRESHOLD:
        return {
            "answer": entry["answer"],
            "matched_q": entry["question"],
            "confidence": round(conf, 3),
            "category": entry["category"],
            "escalated": False,
        }
    # Low confidence: try the optional LLM path, else escalate honestly.
    llm_answer = try_llm_fallback(q)
    if llm_answer:
        return {
            "answer": llm_answer,
            "matched_q": None,
            "confidence": round(conf, 3),
            "category": entry["category"],
            "escalated": False,
            "via": "llm",
        }
    return {
        "answer": (
            "I'm not confident I have the right answer for that, so I'm escalating "
            "this to our human support team (support@demokart.example, Mon–Sat 9am–9pm IST). "
            f"This looks related to '{entry['category']}' — they'll pick it up with full context."
        ),
        "matched_q": None,
        "confidence": round(conf, 3),
        "category": entry["category"],
        "escalated": True,
    }


CHAT_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DemoKart Support — AI Agent</title>
<style>
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#0f172a;color:#e2e8f0;display:flex;flex-direction:column;height:100vh}
header{background:#1e293b;padding:14px 18px;border-bottom:1px solid #334155}
header b{font-size:1.05rem}header small{color:#94a3b8;display:block;font-size:.78rem}
#chat{flex:1;overflow-y:auto;padding:18px;max-width:640px;width:100%;margin:0 auto}
.msg{max-width:85%;padding:10px 14px;border-radius:14px;margin:8px 0;font-size:.93rem;line-height:1.5}
.user{background:#0ea5e9;color:#fff;margin-left:auto;border-bottom-right-radius:4px}
.bot{background:#1e293b;border:1px solid #334155;border-bottom-left-radius:4px}
.meta{font-size:.72rem;color:#64748b;margin-top:6px}
.esc{border-color:#b45309}.typing{color:#94a3b8;font-style:italic}
#bar{display:flex;gap:8px;padding:12px;max-width:640px;width:100%;margin:0 auto}
#q{flex:1;background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:12px;border-radius:10px;font-size:.95rem}
button{background:#0ea5e9;color:#fff;border:0;padding:12px 20px;border-radius:10px;font-weight:700;cursor:pointer}
</style></head><body>
<header><b>🤖 DemoKart Support Agent</b><small>Demo 2 — VisionQuantech · answers from the store FAQ, escalates when unsure</small></header>
<div id="chat"></div>
<div id="bar"><input id="q" placeholder="Ask about shipping, returns, refunds…" autocomplete="off"><button onclick="send()">Ask</button></div>
<script>
const chat=document.getElementById('chat'),q=document.getElementById('q');
function add(html,cls){const d=document.createElement('div');d.className='msg '+cls;d.innerHTML=html;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
add("Hi! I'm the DemoKart support agent. Ask me about shipping, returns, refunds, payments, warranty…","bot");
async function send(){const t=q.value.trim();if(!t)return;q.value='';
add(t.replace(/</g,'&lt;'),'user');
const ty=add("typing…","bot typing");
try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:t})});
const d=await r.json();ty.remove();
let m=d.answer.replace(/</g,'&lt;').replace(/\\n/g,'<br>');
m+=`<div class="meta">${d.escalated?'⚠️ escalated to human':'✓ answered'} · confidence ${d.confidence}${d.via?' · via '+d.via:''}${d.matched_q?' · matched: “'+d.matched_q.replace(/</g,'&lt;')+'”':''}</div>`;
add(m,'bot'+(d.escalated?' esc':''));}
catch(e){ty.remove();add("Something went wrong reaching the agent. Please try again.","bot")}}
q.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
</script></body></html>"""
