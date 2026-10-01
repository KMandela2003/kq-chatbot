"""
Kenya Airways Centralized Chatbot — Prototype
------------------------------------------------
Demo implementation of the proposed architecture:
  Python (NLP core) + JavaScript (frontend) + relational DB (SQLite stands
  in for PostgreSQL in this local prototype — same schema shape, swappable
  connection string in production).

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path

import requests
from flask import Flask, g, jsonify, render_template, request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kq_chatbot.db"
INTENTS_PATH = BASE_DIR / "intents.json"

# Below this confidence, provide a direct helpful response without human handoff
CONFIDENCE_THRESHOLD = 0.25

app = Flask(__name__)

# ---------------------------------------------------------------------
# Live Flight Integration Helper
# ---------------------------------------------------------------------
def extract_flight_code(text: str) -> str | None:
    """Extracts KQ flight codes (e.g., KQ101, KQ 102, kq305) from user input."""
    pattern = r"\b(kq\s?\d{3,4})\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "").upper()
    return None


def get_live_flight_status(flight_code: str) -> str:
    """Queries live aviation API for real-time KQ flight status."""
    api_key = os.getenv("AVIATIONSTACK_API_KEY", "459c83af34f9ea01033e145d6cfb230f")
    url = "http://api.aviationstack.com/v1/flights"
    params = {"access_key": api_key, "flight_iata": flight_code.upper()}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            flight = data["data"][0]
            status = flight.get("flight_status", "Scheduled").capitalize()
            dep_airport = flight.get("departure", {}).get("airport", "Nairobi Jomo Kenyatta")
            arr_airport = flight.get("arrival", {}).get("airport", "Destination")
            sched_dep = flight.get("departure", {}).get("scheduled", "N/A")
            sched_arr = flight.get("arrival", {}).get("scheduled", "N/A")
            gate = flight.get("departure", {}).get("gate", "TBD")

            return (
                f"✈️ Live Flight Details for {flight_code.upper()}:\n"
                f"• Status: {status}\n"
                f"• Origin: {dep_airport}\n"
                f"• Destination: {arr_airport}\n"
                f"• Scheduled Departure: {sched_dep}\n"
                f"• Scheduled Arrival: {sched_arr}\n"
                f"• Gate: {gate}"
            )
        else:
            return (
                f"I identified flight code {flight_code.upper()}, but could not find "
                "an active schedule for today. Please verify the flight number."
            )
    except Exception as e:
        return f"Unable to fetch live flight details right now. Internal Error: {str(e)}"


# ---------------------------------------------------------------------
# 1. Load intents & train the NLP intent-classification core
# ---------------------------------------------------------------------
with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    INTENTS = json.load(f)["intents"]

INTENT_BY_ID = {i["id"]: i for i in INTENTS}


def normalize(text: str) -> str:
    """Lightweight preprocessing: lowercase, strip punctuation/noise."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_training_set():
    X, y = [], []
    for intent in INTENTS:
        for phrase in intent["phrases"]:
            X.append(normalize(phrase))
            y.append(intent["id"])
    return X, y


def train_model():
    X, y = build_training_set()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=2000, C=15)),
        ]
    )
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    metrics = {
        "precision": round(precision_score(y_test, y_pred, average="macro", zero_division=0), 3),
        "recall": round(recall_score(y_test, y_pred, average="macro", zero_division=0), 3),
        "f1_score": round(f1_score(y_test, y_pred, average="macro", zero_division=0), 3),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "num_intents": len(INTENT_BY_ID),
    }

    # Refit on the full dataset so the deployed model uses all available phrases.
    pipeline.fit(X, y)
    return pipeline, metrics


MODEL, EVAL_METRICS = train_model()
print(f"[startup] intent classifier trained — holdout F1: {EVAL_METRICS['f1_score']}")


def classify(message: str):
    cleaned = normalize(message)
    if not cleaned:
        return None, 0.0
    probs = MODEL.predict_proba([cleaned])[0]
    classes = MODEL.classes_
    best_idx = probs.argmax()
    return classes[best_idx], float(probs[best_idx])


# ---------------------------------------------------------------------
# 2. Relational schema (mirrors the proposal's PostgreSQL design)
#    Users / Intent_Configurations / Interaction_Logs / Feedback_Metrics
# ---------------------------------------------------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interaction_logs (
            log_id TEXT PRIMARY KEY,
            session_token TEXT NOT NULL,
            role TEXT NOT NULL,
            raw_input_text TEXT NOT NULL,
            classified_intent_id TEXT,
            confidence_score REAL,
            response_latency_seconds REAL,
            escalated INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback_metrics (
            feedback_id TEXT PRIMARY KEY,
            log_id TEXT NOT NULL,
            usability_score INTEGER,
            comments TEXT,
            FOREIGN KEY (log_id) REFERENCES interaction_logs(log_id)
        );
        """
    )
    conn.commit()
    conn.close()


init_db()

# Access clearance per role, matching the proposal's Public/Internal split.
STAFF_ONLY_INTENTS = {i["id"] for i in INTENTS if i["category"] == "staff"}
PASSENGER_ONLY_INTENTS = {i["id"] for i in INTENTS if i["category"] == "passenger"}


# ---------------------------------------------------------------------
# 3. Routes — chat UI, admin dashboard, and the API used by chat.js
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(force=True) or {}
    message = (payload.get("message") or "").strip()
    role = payload.get("role", "passenger")
    session_token = payload.get("session_token") or str(uuid.uuid4())

    if not message:
        return jsonify({"error": "message is required"}), 400

    start = time.perf_counter()

    # 1. Check for explicit flight code entity
    flight_code = extract_flight_code(message)
    if flight_code:
        latency = time.perf_counter() - start
        response_text = get_live_flight_status(flight_code)
        log_id = str(uuid.uuid4())
        
        db = get_db()
        db.execute(
            """INSERT INTO interaction_logs
               (log_id, session_token, role, raw_input_text, classified_intent_id,
                confidence_score, response_latency_seconds, escalated, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (log_id, session_token, role, message, "flight_status", 1.0, latency, 0),
        )
        db.commit()

        return jsonify(
            {
                "log_id": log_id,
                "session_token": session_token,
                "intent_id": "flight_status",
                "intent_label": "Flight Status (Live API)",
                "confidence": 1.0,
                "escalated": False,
                "latency_ms": round(latency * 1000, 1),
                "response": response_text,
            }
        )

    # 2. Run standard intent classifier
    intent_id, confidence = classify(message)
    latency = time.perf_counter() - start

    escalated = False
    if intent_id is None or confidence < CONFIDENCE_THRESHOLD:
        response_text = (
            "I'm sorry, I couldn't fully understand your request. "
            "Please rephrase your query or specify a valid flight code (e.g., KQ101)."
        )
        intent_label = "unrecognized_intent"
    else:
        intent_label = INTENT_BY_ID[intent_id]["label"]
        if role == "passenger" and intent_id in STAFF_ONLY_INTENTS:
            response_text = (
                "That looks like an internal staff question — please use the employee "
                "portal, or switch roles above if you're signed in as staff."
            )
            escalated = True
        else:
            response_text = INTENT_BY_ID[intent_id]["response"]

    log_id = str(uuid.uuid4())
    db = get_db()
    db.execute(
        """INSERT INTO interaction_logs
           (log_id, session_token, role, raw_input_text, classified_intent_id,
            confidence_score, response_latency_seconds, escalated, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (log_id, session_token, role, message, intent_id, confidence, latency, int(escalated)),
    )
    db.commit()

    return jsonify(
        {
            "log_id": log_id,
            "session_token": session_token,
            "intent_id": intent_id,
            "intent_label": intent_label,
            "confidence": round(confidence, 3),
            "escalated": escalated,
            "latency_ms": round(latency * 1000, 1),
            "response": response_text,
        }
    )


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    payload = request.get_json(force=True) or {}
    log_id = payload.get("log_id")
    score = payload.get("usability_score")
    comments = payload.get("comments", "")
    if not log_id or score is None:
        return jsonify({"error": "log_id and usability_score are required"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO feedback_metrics (feedback_id, log_id, usability_score, comments) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), log_id, int(score), comments),
    )
    db.commit()
    return jsonify({"status": "recorded"})


@app.route("/api/logs")
def api_logs():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM interaction_logs ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/metrics")
def api_metrics():
    db = get_db()
    total = db.execute("SELECT COUNT(*) c FROM interaction_logs").fetchone()["c"]
    escalated = db.execute(
        "SELECT COUNT(*) c FROM interaction_logs WHERE escalated = 1"
    ).fetchone()["c"]
    avg_latency = db.execute(
        "SELECT AVG(response_latency_seconds) a FROM interaction_logs"
    ).fetchone()["a"] or 0
    avg_conf = db.execute(
        "SELECT AVG(confidence_score) a FROM interaction_logs WHERE confidence_score IS NOT NULL"
    ).fetchone()["a"] or 0
    by_intent = db.execute(
        """SELECT classified_intent_id, COUNT(*) c FROM interaction_logs
           WHERE classified_intent_id IS NOT NULL
           GROUP BY classified_intent_id ORDER BY c DESC"""
    ).fetchall()

    return jsonify(
        {
            "offline_eval": EVAL_METRICS,
            "live": {
                "total_interactions": total,
                "escalated_count": escalated,
                "escalation_rate": round(escalated / total, 3) if total else 0,
                "avg_latency_ms": round(avg_latency * 1000, 1),
                "avg_confidence": round(avg_conf, 3),
            },
            "intent_distribution": [
                {
                    "intent_id": r["classified_intent_id"],
                    "label": INTENT_BY_ID.get(r["classified_intent_id"], {}).get(
                        "label", r["classified_intent_id"]
                    ),
                    "count": r["c"],
                }
                for r in by_intent
            ],
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)