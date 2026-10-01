# KQ Public Content Scraper

Pulls text from Kenya Airways' public policy/FAQ pages so you can turn it
into real training phrases for `intents.json` in the chatbot prototype.

Tested against a local mock accordion page to confirm the click-to-expand
and text-extraction logic works — the actual `kenya-airways.com` pages
weren't reachable from the environment this was built in, so **run it
yourself and check the output** before trusting it fully. Sites change
their markup over time, so if a particular page comes back empty or looks
wrong, that page's structure has likely changed and the accordion selectors
may need adjusting (see "If a page comes back empty" below).

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
python scrape_kq_content.py
```

This visits each URL in the `PAGES` list inside the script, tries to expand
any collapsed FAQ sections, and saves:
- `scraped/<intent_id>.txt` — one raw text dump per page
- `scraped_content.json` — a summary (url + character count) for all pages

## What to do with the output

The script gives you **raw page text**, not ready-made training data. For
each `scraped/<intent_id>.txt`:

1. Open it and find the actual policy fact (e.g. the baggage weight limit).
2. Write 5–10 short, differently-phrased questions a real user might ask
   about it — this is what goes in `intents.json`'s `"phrases"` list.
3. Turn the policy fact into a clear one- or two-sentence `"response"`.
4. Paste both into the matching intent block in the chatbot's
   `intents.json`, then retrain by restarting `app.py`.

This matches your proposal's own Data Acquisition step — real public
content in, hand-curated intents out.

## If a page comes back with little or no text

- Check the `.txt` file — you might just be getting a cookie-consent banner
  or the page's outer navigation instead of the FAQ content.
- Some pages may lazy-load content only after scrolling — try adding
  `page.mouse.wheel(0, 2000)` before extraction if that happens.
- If a specific FAQ section still won't expand, open the page in your
  browser's DevTools, inspect the button element for that question, and
  add its class name to `ACCORDION_SELECTORS` in the script.

## Being a considerate visitor

- `robots.txt` for kenya-airways.com currently allows crawling public pages
  (only `/episerver/` and `/util/` are disallowed) — re-check it yourself
  before running this, since it can change.
- The script waits 2 seconds between pages by default
  (`REQUEST_DELAY_SECONDS`) — don't lower this for a one-off data pull.
- This is for personal/academic use in your capstone proposal — cite the
  site as your source, and don't republish the scraped text wholesale.
