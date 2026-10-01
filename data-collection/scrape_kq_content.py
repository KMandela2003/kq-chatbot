"""
Kenya Airways public content scraper — for building intents.json training data
--------------------------------------------------------------------------------
The KQ site renders its FAQ/policy text with JavaScript, so plain requests +
BeautifulSoup returns an empty shell. This uses Playwright (a real headless
browser) instead, and also tries to click open any FAQ-style accordions
before extracting text, since those sections often start collapsed.

This only visits public, non-authenticated pages and adds a short delay
between requests to be polite. robots.txt for kenya-airways.com currently
allows crawling (Allow: /, disallowing only /episerver/ and /util/) — always
re-check https://www.kenya-airways.com/robots.txt yourself before running
this, since that can change.

Setup:
    pip install playwright
    playwright install chromium

Run:
    python scrape_kq_content.py

Output:
    scraped/<intent_id>.txt   — raw extracted text per page
    scraped_content.json      — all pages combined, structured

This gives you RAW page text, not ready-made training phrases. Read each
.txt file, pull out the specific facts/sentences relevant to that intent,
and hand-write 5-10 short question variations + a response into your
intents.json — see README.md for the recommended workflow.
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "scraped"
OUTPUT_DIR.mkdir(exist_ok=True)

# Map each passenger-facing intent to a public page that documents it.
# Staff-facing intents (shift schedule, HR policy, payroll, etc.) aren't on
# the public site at all — those still need mock/synthetic data per your
# proposal's stated limitation.
PAGES = [
    {
        "intent_id": "baggage_allowance",
        "url": "https://www.kenya-airways.com/en/plan/baggage-information/baggage-allowance/",
    },
    {
        "intent_id": "hand_baggage",
        "url": "https://www.kenya-airways.com/en/plan/baggage-information/hand-baggage/",
    },
    {
        "intent_id": "lost_baggage",
        "url": "https://www.kenya-airways.com/en/plan/baggage-information/delayed-baggage/",
    },
    {
        "intent_id": "checkin_process",
        "url": "https://www.kenya-airways.com/en/book-manage/post-booking/check-in/",
    },
    {
        "intent_id": "booking_change",
        "url": "https://www.kenya-airways.com/en/book-manage/manage-booking/change-booking/",
    },
    {
        "intent_id": "refund_policy",
        "url": "https://www.kenya-airways.com/en/book-manage/manage-booking/refunds/",
    },
    {
        "intent_id": "flight_delay_compensation",
        "url": "https://www.kenya-airways.com/en/book-manage/self-rebooking-service/",
    },
    {
        "intent_id": "seat_selection",
        "url": "https://www.kenya-airways.com/en/experience/seat-selection/seat-faqs/",
    },
    {
        "intent_id": "travel_documents",
        "url": "https://www.kenya-airways.com/en/plan/travel-information/travel-requirements/",
    },
    {
        "intent_id": "loyalty_program",
        "url": "https://asante.kenya-airways.com/faq",
    },
    {
        "intent_id": "general_faqs",
        "url": "https://www.kenya-airways.com/en/help/faqs/",
    },
]

# Common patterns used for collapsed FAQ/accordion sections across sites.
# We try each selector and click whatever matches, ignoring ones that don't
# exist on a given page.
ACCORDION_SELECTORS = [
    '[aria-expanded="false"]',
    ".accordion-header",
    ".accordion-toggle",
    ".faq-question",
    "button.accordion",
    "[data-toggle='collapse']",
]

REQUEST_DELAY_SECONDS = 2.0
MAX_ACCORDION_CLICKS_PER_PAGE = 40


def expand_accordions(page):
    """Best-effort: click anything that looks like a collapsed FAQ toggle."""
    clicked = 0
    for selector in ACCORDION_SELECTORS:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue
        for el in elements:
            if clicked >= MAX_ACCORDION_CLICKS_PER_PAGE:
                return clicked
            try:
                if el.is_visible():
                    el.click(timeout=1500)
                    clicked += 1
                    page.wait_for_timeout(150)
            except Exception:
                # Element not clickable / detached / covered — skip it.
                continue
    return clicked


def scrape_page(page, url: str) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # Some pages keep background requests alive indefinitely; proceed anyway.

    expand_accordions(page)
    page.wait_for_timeout(500)

    # Prefer <main> if the page has one; otherwise fall back to <body>.
    try:
        text = page.inner_text("main")
    except Exception:
        text = page.inner_text("body")

    # Collapse excess blank lines for readability.
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (compatible; KQChatbotResearchBot/1.0; "
            "academic capstone project data collection)"
        ))

        for entry in PAGES:
            intent_id, url = entry["intent_id"], entry["url"]
            print(f"Scraping [{intent_id}] {url} ...")
            try:
                text = scrape_page(page, url)
            except Exception as exc:
                print(f"  failed: {exc}")
                text = ""

            out_path = OUTPUT_DIR / f"{intent_id}.txt"
            out_path.write_text(text, encoding="utf-8")
            results.append({"intent_id": intent_id, "url": url, "char_count": len(text)})
            print(f"  saved {len(text)} chars -> {out_path}")

            time.sleep(REQUEST_DELAY_SECONDS)

        browser.close()

    with open(Path(__file__).parent / "scraped_content.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nDone. Raw text is in ./scraped/*.txt")
    print("Next: read each file, pull the relevant facts, and hand-write")
    print("question phrasings + a response into intents.json.")


if __name__ == "__main__":
    main()
