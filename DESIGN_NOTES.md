# Design plan — "Departure Board" aesthetic

Subject: an airline operations chatbot. Audience: passengers and internal
staff, viewed by an academic panel as a demo. Job: show the NLP pipeline is
real and inspectable, not just a pretty chat window.

## Color
- `--bg`: #10161D (charcoal-navy, not pure black)
- `--panel`: #182029 (message panel / input bar)
- `--panel-raised`: #1E2833 (incoming message bubble)
- `--amber`: #F2A93B (primary accent — split-flap departure board amber)
- `--teal`: #3FA9A0 (secondary accent — runway/taxiway light)
- `--text`: #EDEFF2
- `--text-muted`: #8996A3
- `--danger`: #D9695F (escalation state)

## Type
- Display / UI chrome: "Space Grotesk" — geometric, signage-like, carries
  the "airport board" personality in headers and the role switch.
- Body / message text: "Inter" — quiet, legible, doesn't compete with the
  display face. No third typeface; the small intent/confidence readout
  uses Space Grotesk at a smaller size and letter-spacing, not a monospace
  face, so it doesn't read as generic "data label" chrome.

## Layout
Single centered column, split-flap board framing the whole chat:

```
+--------------------------------------------------+
| KQ CONNECT                    [Passenger|Staff]  |  <- board header
+--------------------------------------------------+
| history of messages, alternating L/R              |
| each bot reply has a thin readout strip underneath:|
|   intent: baggage_allowance   conf: 0.71  212ms    |
+--------------------------------------------------+
| [ type a message........................] [Send] |
+--------------------------------------------------+
```//
Left-aligned bot messages, right-aligned user messages — but bubbles use a
single clipped corner (like a torn ticket stub) instead of full rounding,
alternating which corner is clipped by side. No drop shadows; a 1px hairline
border in a slightly lighter tone does the separation work instead.

## Principles
- The intent/confidence/latency readout under each bot reply is structural
  information, not decoration — it's the panel's window into the NLP core
  actually working, which is the whole point of the demo.
- One motion moment: the readout strip fades in a beat after the message
  text, like a flap display settling — not per-hover animation everywhere.
- Restraint: no gradients, no card-shadow kit, no ALL-CAPS labels except the
  literal departure-board style header (which is load-bearing to the
  metaphor, not a generic eyebrow tag).
