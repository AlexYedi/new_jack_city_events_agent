# new_jack_city_events_agent

# NYC AI Events Digest

A weekly **Sunday-morning** email digest that helps you discover and register for the **best in-person AI / Agentic / ML / Venture Funding events** across **NYC (all 5 boroughs; Hoboken/Jersey City allowed but de-prioritized)** — **≥ 2 weeks out**, with an emphasis on looking **4+ weeks ahead** to improve RSVP success.

This repo is designed to ship fast, stay cheap, and avoid regressions.

---

## Product Goals

### Outcome
- Spend less time searching.
- Find higher-quality events earlier (so you can actually get in).
- Keep the system maintainable and low-cost.

### Weekly Digest Requirements
- **Cadence:** Weekly, **Sunday morning (America/New_York)**
- **Scope:** In-person events; NYC prioritized; Hoboken/Jersey City allowed but not prioritized
- **Topic filter:** Artificial Intelligence, Machine Learning, Agentic AI, Agentic Systems, Venture Funding
- **Format:**
  - Bullets arranged by **date**
  - **Max 20 events** per email
  - Include a “countdown” view working backwards:
    - **~4 weeks out**, **3 weeks**, **2 weeks**, **next week**
  - Include links to each event
  - Include a section summarizing **events you’re attending next week**:
    - topic, presenting company, speakers, and key topics

---

## Quality Rubric (Ranking)

Events are scored across these dimensions:

1. **Content format (highest weight)**
   - Hands-on building / workshops (best)
   - Live demonstrations (second)
   - Expert panels (third)

2. **Expertise / value**
   - Speaker caliber (accomplishments, body of work)
   - Company caliber (where they work / what they’ve built)

3. **Price**
   - Free preferred
   - Paid allowed if quality is high, especially for **conference/expo-style events**
   - Goal: improve conference/expo mix (“Yes, at conferences”)

---

## Sources (Initial Priority)

Must-track:
- Gary’s Guide
- Luma
- Grey Journal

Other starters:
- AI Tinkerers events
- Supermomos
- Meetup (via ICS/export where possible)
- Eventbrite (likely via tracked org/venue lists)

> Note: We explicitly **exclude job boards** unless we later add a feature to pull **relevant roles at companies hosting/sponsoring/speaking at events**.

---

## Architecture (MVP)

```mermaid
flowchart LR
  S[Sources\nGarysGuide, GreyJournal,\nAI Tinkerers, Supermomos,\nMeetup(ICS), Luma(calendars)] --> I[Ingest\nScheduled Runner]
  I --> N[Normalize\nLLM extraction -> schema]
  N --> D[Dedup + Enrich\nfingerprints + tie-break]
  D --> F[Filter\nin-person + NYC + topics]
  F --> R[Rank/Score\nrubric + speaker/company]
  R --> C[Compose Weekly Digest\n<=20 events]
  C --> E[Send Email\nGmail]
  D --> DB[(Store)\nSupabase or Google Sheets]
  A[GCal\nAttending events] --> C
