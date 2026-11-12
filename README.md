# AI Room Booking Chatbot (IBM Watson Assistant)

A conversational assistant that books meeting rooms, checks availability, lists and cancels bookings.
**IBM Watson Assistant** performs natural-language understanding (intents and entities); a **Flask** backend
handles the dialog, validation and a **SQLite** booking database; a lightweight web page is the chat front end.

---

## 1. Problem statement and objectives

Booking a room through forms or email is slow and error-prone (double bookings, unclear availability).
This project provides a chat interface that lets a user book a room in natural language, such as
*"Book a room for 5 people tomorrow at 2pm for 2 hours"*.

Objectives
1. Understand booking requests in free text using IBM Watson Assistant.
2. Collect missing details through guided questions (slot filling).
3. Prevent double bookings and enforce business rules (opening hours, capacity, valid dates).
4. Let users confirm, list and cancel bookings.
5. Keep working in offline demo mode when Watson credentials are not available.

## 2. System architecture

```
 User (browser)
      │  POST /chat {session_id, message}
      ▼
 Flask app (app.py) ──► bot.py  Dialog manager: slot filling, validation, confirmation
                          │  ├─► nlu.py  ──► IBM Watson Assistant (intents + entities)
                          │  │               └─ regex/keyword fallback if Watson is unavailable
                          │  └─► booking.py ──► SQLite (rooms, bookings)
      ▲                   │
      └───── reply ◄──────┘
```

Design decision: Watson handles **what the user means**; the application code handles **what to do**.
This keeps business rules (conflict checks, hours) testable and independent of the cloud service.

| Component | File | Responsibility |
|---|---|---|
| Web UI | `static/index.html` | Chat window, quick-reply chips, session id |
| API | `app.py` | `/chat`, `/health`, serves UI |
| Dialog manager | `bot.py` | Per-session state, slot filling, validation, confirmation |
| NLU layer | `nlu.py` | Calls Watson (v2 stateless API), merges entities, fallback parser |
| Data layer | `booking.py` | Rooms table, overlap-safe booking, cancel, list |
| Watson skill | `watson/skill-dialog.json` | Importable intents and entities |
| Tests | `tests/test_bot.py` | End-to-end conversation tests |

## 3. Technology stack

Python 3.10+, Flask, IBM Watson Assistant (`ibm-watson` SDK, API v2), SQLite, HTML/CSS/JavaScript.

## 4. Watson Assistant design

### Intents
| Intent | Purpose | Example utterance |
|---|---|---|
| `book_room` | Start a booking | "reserve a conference room" |
| `check_availability` | Query free rooms | "which rooms are free at 11am" |
| `cancel_booking` | Cancel by number | "cancel booking 12" |
| `list_bookings` | Show a user's bookings | "show my bookings" |
| `greeting` / `goodbye` | Small talk | "hello" / "thank you" |

Each intent has 6 to 8 training examples in `watson/skill-dialog.json`. Add more for better accuracy.

### Entities
| Entity | Type | Used for |
|---|---|---|
| `@sys-date` | System | Booking date (resolves "tomorrow", "next Friday") |
| `@sys-time` | System | Start time |
| `@sys-number` | System | Number of attendees |
| `@room_type` | Custom | meeting, conference, seminar, huddle (with synonyms) |

### Setup steps
1. Create an **IBM Cloud** account and a **Watson Assistant** service instance (Lite plan is free).
2. Open the instance, create an assistant, then **Add a dialog skill > Upload skill** and select `watson/skill-dialog.json`.
3. Enable the system entities `@sys-date`, `@sys-time`, `@sys-number` in the skill's *Entities > System entities* tab.
4. Open *Assistant settings* and copy the **Assistant ID**. From the service credentials copy the **API key** and **URL**.
5. Copy `.env.example` to `.env` and fill in the three values.

## 5. Dialog flow

```
greeting ─► book_room ─► ask date ─► ask time ─► ask hours ─► ask people ─► ask name
                                                                              │
              no free room ◄── check conflicts / capacity ◄───────────────────┘
                   │                         │
            suggest another time      offer smallest suitable room
                                             │
                                  user confirms (yes/no) ─► booking id returned
```

Business rules: bookings between 08:00 and 20:00, 0.5 to 8 hours, 1 to 30 attendees, no past dates,
overlapping bookings in the same room rejected (checked again at write time).

Rooms: Eka (2), Aryabhata (4), Bhaskara (8), Charaka (12), Dhruva (30). Edit `ROOMS` in `booking.py`.

## 6. Installation and running

```bash
git clone <your-repo> && cd room-booking-bot
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # add Watson credentials (optional)
python app.py
```

Open http://localhost:5000. Check `http://localhost:5000/health`: it reports `"nlu": "watson"` or `"fallback"`.

### API
`POST /chat` with `{"session_id": "abc", "message": "book a room"}` returns `{"session_id": "abc", "reply": "..."}`.

## 7. Sample conversation

```
User: Book a room for 5 people tomorrow at 2pm
Bot : For how many hours?
User: 2
Bot : What name should I book it under?
User: Asha
Bot : Bhaskara (meeting, seats 8) is free on 2026-11-13 14:00-16:00 for 5 people.
      Shall I confirm the booking for Asha? (yes/no)
User: yes
Bot : Booked! Booking #1: Bhaskara on 2026-11-13, 14:00-16:00 for Asha. Say 'cancel 1' to cancel.
```

## 8. Testing

Four conversation tests cover the full booking flow, conflict handling, opening-hours validation, and
list/cancel. Run `pytest -q tests`. All four passed during development using the offline fallback NLU.

| Test | What it proves |
|---|---|
| `test_full_booking_flow` | Slot filling and confirmation produce a booking |
| `test_conflict_hides_booked_room` | A booked room is not offered for overlapping time |
| `test_validation_opening_hours` | 06:00 start is rejected |
| `test_list_and_cancel` | A booking can be listed by name and cancelled |

Suggested additions for the report: measure Watson intent accuracy using the Watson *Improve* tab or a
held-out set of 30+ utterances and report a confusion matrix.

## 9. Limitations

- Dialog state is kept in memory, so it resets on restart and does not scale across multiple servers.
- No user authentication; bookings are matched by name only.
- Times are interpreted in the server's local time zone; single-language (English).
- Small training set; accuracy will improve with more utterances.

## 10. Future work

Authentication (SSO), Google/Outlook calendar sync, email confirmations, Redis session store,
room-type preference (`@room_type` is trained but not yet used in search), multilingual support,
deployment to IBM Cloud Code Engine, and voice input with Watson Speech to Text.

## 11. Project structure

```
room-booking-bot/
├── app.py            ├── bot.py           ├── nlu.py          ├── booking.py
├── static/index.html ├── watson/skill-dialog.json
├── tests/test_bot.py ├── requirements.txt └── .env.example
```

## 12. References

IBM Watson Assistant documentation (cloud.ibm.com/docs/assistant), IBM Watson Python SDK (`ibm-watson`), Flask documentation.
