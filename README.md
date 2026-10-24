# Kenya Airways (KQ) AI Chatbot & Flight Tracker

An intelligent, multi-role web assistant built to handle passenger inquiries, validate staff credentials, and retrieve real-time flight status updates using the AviationStack API.

---

## Architecture & Tech Stack

- **Backend:** FastAPI (ASGI Python 3.10+) for non-blocking asynchronous requests
- **Data Validation:** Pydantic v2 schemas for request models and staff ID validation
- **Frontend:** Responsive HTML5 / CSS3 / JavaScript dashboard
- **API Integration:** Async HTTP client (`httpx`) connecting to AviationStack API
- **NLP / ML:** TF-IDF Vectorization with Logistic Regression for intent parsing

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Environment Setup

```bash
# Clone the repository
git clone [https://github.com/KMandela2003/kq-chatbot.git](https://github.com/KMandela2003/kq-chatbot.git)
cd kq-chatbot

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate  # Windows

# Install dependencies
pip install -r requirements.txt