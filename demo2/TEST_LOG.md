# Demo 2 — TEST LOG (2026-09-23, run for real)

## Boot
- `uvicorn app:app --host 127.0.0.1 --port 18021` → up (~30s for sklearn import)
- `curl /docs` → **200**; `GET /api/kb` → 18 entries

## Matching tests (`POST /api/ask`)
| # | Question | Matched | Confidence | Escalated |
|---|---|---|---|---|
| 1 | how long does shipping take | How long does shipping take? | 0.803 | no ✓ |
| 2 | i want to return my phone | What is your return policy? | 0.408 | no ✓ |
| 3 | do you accept cash on delivery | Is Cash on Delivery available? | 0.646 | no ✓ |
| 4 | my order arrived broken what do i do | My order arrived damaged. What should I do? | 0.583 | no ✓ |
| 5 | what payment methods do you take | What payment methods do you accept? | 0.602 | no ✓ |
| 6 | asdfgh qwerty zzz | — | 0.000 | **yes** ✓ |

## Bug found & fixed during testing
- Q2 initially scored 0.21 (< 0.25 threshold) and escalated — correct ranking,
  wrong outcome. Fixed by blending cosine with a keyword-hit bonus
  (0.75 × cosine + 0.25 × keyword) in `match()`. Re-tested: 5/5 correct,
  nonsense still escalates at 0.0.
