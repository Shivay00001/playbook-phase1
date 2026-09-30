# Demo 3 — TEST LOG (2026-09-23, run for real)

## Boot
- `uvicorn app:app --host 127.0.0.1 --port 18022` → up
- `curl /docs` → **200**

## Upload
- `curl -X POST /api/upload -F "file=@sample_leads.csv"`
- → `{"ok":true,"count":12,"errors":[]}`

## Stale detection (`GET /api/stale?days=14`, today = 2026-09-23)
Flagged 5/12 — all correct:
| Lead | last_contact | days_since | stage | verdict |
|---|---|---|---|---|
| Neha Kapoor | 2026-09-05 | 18 | quote_sent | stale ✓ |
| Amit Verma | 2026-08-05 | 49 | quote_sent | stale ✓ |
| Sunita Rao | 2026-08-08 | 46 | negotiating | stale ✓ |
| Arjun Nair | 2026-07-20 | 65 | new | stale ✓ |
| Meena Iyer | 2026-08-20 | 34 | quote_sent | stale ✓ |

Correctly NOT flagged: Rajesh Gupta (2d), Anil Mehta (3d), Deepak Yadav (1d),
Priya Sharma (10d < 14), Vikram Singh (13d < 14), Kavita Desai (5d),
Rohit Malhotra (70d but stage=cold → excluded by design).

## Message generation (`POST /api/generate?stale_only=true`)
- → 5 messages generated.
- Neha Kapoor (WhatsApp): "Hi Neha Kapoor! This is from VisionQuantech. It's been
  18 days since we last connected about Kapoor Dental Care. Just checking on the
  quote we shared (₹60,000). Still on your mind? Happy to walk you through it again."
- Sunita Rao (negotiating angle): "...happy to revisit terms so we can get this
  over the line. ₹150,000 is still locked in for this week."
- Personalization verified: name, business, computed days, quoted value, and
  stage-specific wording all interpolated — no lorem ipsum, no placeholders.
