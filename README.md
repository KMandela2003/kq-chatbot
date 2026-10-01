# KQ Connect — Kenya Airways Chatbot Prototype

A working demo of the system described in the proposal: a centralized,
web-based AI chatbot that classifies passenger and staff inquiries and
routes them to an automated response or a human agent.

This is a **scaled-down proof of concept** for the proposal defense — it
demonstrates the pipeline end to end, not the production system.

## Architecture mapping (prototype → proposal)

| Proposal component | This prototype |
|---|---|
| Python NLP core | `app.py` — TF-IDF + Logistic Regression intent classifier |
| PostgreSQL | SQLite (`kq_chatbot.db`) — same table shape, swap the connection in `app.py` for production |
| JavaScript frontend | `static/js/chat.js` + `static/js/admin.js`, vanilla fetch/async |
| Admin dashboard | `/admin` — live interaction logs, intent distribution, evaluation metrics |
| 20 predefined intents | `intents.json` — 10 passenger-facing, 10 staff-facing |
| Access clearance (Public/Internal) | Passenger role is blocked from staff-only intents in `app.py` |

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** for the chat, and
**http://127.0.0.1:5000/admin** for the ops dashboard.

## What to demo in your defense

1. Ask a passenger question ("how many bags can I check in") — shows
   correct intent classification, confidence, and latency under the reply.
2. Switch to Staff and ask an internal question ("when is my next shift").
3. Ask a staff question while still set to Passenger — shows the
   access-control boundary from the proposal's Public/Internal design.
4. Type something unrelated ("asdkjaslkdj") — shows the confidence
   threshold escalating to a human instead of guessing.
5. Open `/admin` — shows the offline F1-score from the train/test split,
   live interaction volume, latency, and intent distribution, mirroring
   your proposed Evaluation Strategy slide.

## Tuning notes (for Q&A)

- **Dataset size**: this demo uses ~10 training phrases per intent (200
  total). The proposal specifies at least 25 phrases per intent from real
  historical + synthetic data — a larger, cleaner dataset is expected to
  push holdout F1 well above this prototype's current score, which you can
  see live on the `/admin` page.
- **Confidence threshold** (`CONFIDENCE_THRESHOLD` in `app.py`, currently
  0.25): tuned by hand against the validation set so that gibberish input
  reliably escalates while real questions still resolve automatically.
  In production this would be tuned against a much larger validation set,
  and per-intent thresholds might replace a single global cutoff.
- **Why Logistic Regression over an SVM or deep model**: fast to train,
  interpretable probabilities for the confidence/escalation logic, and
  appropriate for a small-intent-count classification problem — matches
  the model options listed in the proposal's methodology chapter.
- **Why SQLite instead of PostgreSQL here**: zero setup for a local demo.
  The table schema (`interaction_logs`, `feedback_metrics`) mirrors the
  proposal's PostgreSQL design directly, so swapping the connection layer
  in `app.py` (e.g. to `psycopg2`) is a drop-in change, not a redesign.

## Known limitations (be upfront about these if asked)

- No live GDS/ERP integration — responses are canned text per intent, not
  pulled from a real booking or HR system (matches the proposal's stated
  limitation).
- No authentication — role is selected via a UI toggle for demo purposes,
  not verified staff login.
- English only, text only — no voice or multi-language support (matches
  the proposal's delimitations).
- Small training set — see "Tuning notes" above.

## Project structure

```
app.py                  Flask backend + NLP training/inference
intents.json            20 intents with training phrases + responses
requirements.txt
templates/
  index.html            Chat UI
  admin.html            Admin dashboard
static/
  css/style.css         Chat UI styling
  css/admin.css         Dashboard styling
  js/chat.js            Chat frontend logic
  js/admin.js           Dashboard frontend logic
data-collection/
  scrape_kq_content.py  Pulls real FAQ/policy text from kenya-airways.com
  README.md             How to run it and turn output into intents.json
DESIGN_NOTES.md          Visual design rationale
```

## Expanding the training data

`intents.json` currently ships with ~10 hand-written phrases per intent.
`data-collection/scrape_kq_content.py` pulls real policy text from the
public Kenya Airways site for your 10 passenger-facing intents, which you
can use to write more (and more realistic) training phrases — see
`data-collection/README.md` for the full workflow. The 10 staff-facing
intents still need mock/synthetic phrasing, since that content isn't
public (matches the proposal's stated data limitation).

