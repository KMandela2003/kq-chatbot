# KQ Chatbot — System Design Notes

## Architectural Transition: Flask to FastAPI

### Rationale
- **Asynchronous Execution (`async`/`await`):** The prototype built on Flask operated synchronously, meaning external API calls to AviationStack blocked thread execution. FastAPI operates natively on an ASGI event loop via `uvicorn` and `httpx`, preventing server thread starvation during high concurrency.
- **Automated Validation via Pydantic:** Request validation for incoming user messages and staff ID credentials is handled declaratively through Pydantic models rather than manual regex checks scattered in endpoint handlers.
- **API Documentation:** FastAPI generates OpenAPI specification schema automatically, accessible at `/docs`.

---

## Security & Environment Strategy
- API tokens and environment-specific settings are loaded strictly via `python-dotenv` from local `.env` files.
- `.env`, `*.db`, and cache directories are explicitly excluded in `.gitignore` to avoid pushing secrets to version control.

---

## Multi-Role Architecture
- **Passenger Mode:** Open access for checking baggage rules, flight statuses, and standard FAQs.
- **Staff Mode:** Gated behind authorization verification requiring a valid employee staff ID (`KQxxxxx` / `PFxxxxx` / 5-6 digit payroll format).