import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "kq_chatbot.db"
INTENTS_PATH = BASE_DIR / "intents.json"

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "459c83af34f9ea01033e145d6cfb230f")
CONFIDENCE_THRESHOLD = 0.25

app = FastAPI(
    title="Kenya Airways AI Assistant",
    description="Production FastAPI service for KQ Chatbot.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Pydantic Schemas ---
class ChatPayload(BaseModel):
    message: str = Field(..., min_length=1)
    role: str = Field("passenger", pattern="^(passenger|staff)$")
    session_token: Optional[str] = None
    staff_id: Optional[str] = None

    @field_validator("staff_id")
    @classmethod
    def validate_staff_id(cls, v, info):
        if info.data.get("role") == "staff" and v:
            pattern = r"^(KQ[-]?\d{4,6}|\d{5,6}|PF[-]?\d{4,5})$"
            if not re.match(pattern, v.strip(), re.IGNORECASE):
                raise ValueError("Invalid Staff ID format.")
        return v

class FeedbackPayload(BaseModel):
    log_id: str
    usability_score: int
    comments: Optional[str] = ""

# --- Helper Functions ---
def extract_flight_code(text: str) -> Optional[str]:
    match = re.search(r"\b(kq\s?\d{3,4})\b", text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "").upper()
    return None

async def fetch_live_flight_status(flight_code: str) -> str:
    url = "http://api.aviationstack.com/v1/flights"
    params = {"access_key": AVIATIONSTACK_API_KEY, "flight_iata": flight_code}
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params=params)
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
                    f"✈️ Live Flight Details for {flight_code}:\n"
                    f"• Status: {status}\n"
                    f"• Origin: {dep_airport}\n"
                    f"• Destination: {arr_airport}\n"
                    f"• Scheduled Departure: {sched_dep}\n"
                    f"• Scheduled Arrival: {sched_arr}\n"
                    f"• Gate: {gate}"
                )
            return f"I identified flight code {flight_code}, but could not find an active schedule today."
    except Exception as e:
        return f"Unable to fetch live flight details right now. Internal Error: {str(e)}"

# --- NLP Model Setup ---
with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    INTENTS = json.load(f)["intents"]

INTENT_BY_ID = {i["id"]: i for i in INTENTS}
STAFF_ONLY_INTENTS = {i["id"] for i in INTENTS if i["category"] == "staff"}

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def train_model():
    X, y = [], []
    for intent in INTENTS:
        for phrase in intent["phrases"]:
            X.append(normalize(phrase))
            y.append(intent["id"])
    
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=2000, C=15)),
    ])
    pipeline.fit(X, y)
    return pipeline

MODEL = train_model()

def classify(message: str):
    cleaned = normalize(message)
    if not cleaned:
        return None, 0.0
    probs = MODEL.predict_proba([cleaned])[0]
    classes = MODEL.classes_
    best_idx = probs.argmax()
    return classes[best_idx], float(probs[best_idx])

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
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
    """)
    conn.commit()
    conn.close()

init_db()

# --- Endpoints ---
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.post("/api/chat")
async def api_chat(payload: ChatPayload):
    start = time.perf_counter()
    session_token = payload.session_token or str(uuid.uuid4())
    flight_code = extract_flight_code(payload.message)

    if flight_code:
        response_text = await fetch_live_flight_status(flight_code)
        latency = time.perf_counter() - start
        log_id = str(uuid.uuid4())
        
        with get_db() as conn:
            conn.execute(
                """INSERT INTO interaction_logs
                   (log_id, session_token, role, raw_input_text, classified_intent_id,
                    confidence_score, response_latency_seconds, escalated, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (log_id, session_token, payload.role, payload.message, "flight_status", 1.0, latency, 0),
            )
            conn.commit()

        return {
            "log_id": log_id,
            "session_token": session_token,
            "intent_id": "flight_status",
            "intent_label": "Flight Status (Live API)",
            "confidence": 1.0,
            "escalated": False,
            "latency_ms": round(latency * 1000, 1),
            "response": response_text,
        }

    intent_id, confidence = classify(payload.message)
    latency = time.perf_counter() - start
    escalated = False

    if intent_id is None or confidence < CONFIDENCE_THRESHOLD:
        response_text = "I'm sorry, I couldn't fully understand your request. Please rephrase or provide a flight code (e.g., KQ101)."
        intent_label = "unrecognized_intent"
    else:
        intent_label = INTENT_BY_ID[intent_id]["label"]
        if payload.role == "passenger" and intent_id in STAFF_ONLY_INTENTS:
            response_text = "That looks like an internal staff question — please switch roles above if you are an employee."
            escalated = True
        else:
            response_text = INTENT_BY_ID[intent_id]["response"]

    log_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """INSERT INTO interaction_logs
               (log_id, session_token, role, raw_input_text, classified_intent_id,
                confidence_score, response_latency_seconds, escalated, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (log_id, session_token, payload.role, payload.message, intent_id, confidence, latency, int(escalated)),
        )
        conn.commit()

    return {
        "log_id": log_id,
        "session_token": session_token,
        "intent_id": intent_id,
        "intent_label": intent_label,
        "confidence": round(confidence, 3),
        "escalated": escalated,
        "latency_ms": round(latency * 1000, 1),
        "response": response_text,
    }

@app.post("/api/feedback")
async def api_feedback(payload: FeedbackPayload):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback_metrics (feedback_id, log_id, usability_score, comments) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), payload.log_id, payload.usability_score, payload.comments),
        )
        conn.commit()
    return {"status": "recorded"}

@app.get("/api/logs")
async def api_logs():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM interaction_logs ORDER BY timestamp DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]