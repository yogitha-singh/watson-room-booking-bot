"""Dialog manager: slot filling, validation, confirmation and booking actions."""
import re
import datetime as dt
import booking
import nlu

SESS = {}
ORDER = ["date", "time", "hours", "people", "name"]
PROMPTS = {
    "date": "Which date do you need the room? (e.g. tomorrow or 2026-11-20)",
    "time": "What time should it start? (e.g. 2pm or 14:00)",
    "hours": "For how many hours?",
    "people": "How many people will attend?",
    "name": "What name should I book it under?",
}
YES = re.compile(r"\b(yes|yeah|yep|confirm|ok|okay|sure|y)\b")
NO = re.compile(r"\b(no|nope|n|stop|never ?mind)\b")
OPEN, CLOSE = 8 * 60, 20 * 60


def new():
    return {"slots": {}, "await": None, "offer": None, "mode": "book"}


def validate(slots):
    """Return an error message and drop the offending slot, or None if all is fine."""
    s = slots
    if "date" in s:
        try:
            d = dt.date.fromisoformat(s["date"])
        except ValueError:
            s.pop("date")
            return "I couldn't read that date."
        if d < dt.date.today():
            s.pop("date")
            return "That date is in the past."
    if "hours" in s and not 0.5 <= s["hours"] <= 8:
        s.pop("hours")
        return "Bookings can be between 0.5 and 8 hours."
    if "people" in s and not 1 <= s["people"] <= 30:
        s.pop("people")
        return "Our biggest room seats 30 people, so please give a number from 1 to 30."
    if "time" in s and "hours" in s:
        start = booking.to_min(s["time"])
        if start < OPEN or start + int(s["hours"] * 60) > CLOSE:
            s.pop("time")
            return "Rooms are available from 08:00 to 20:00 and the booking must end by 20:00."
    return None


def reply(sid, text):
    s = SESS.setdefault(sid, new())
    low = text.lower().strip()

    if s["offer"]:
        if YES.search(low):
            return confirm(sid, s)
        if NO.search(low):
            SESS[sid] = new()
            return "No problem, I've dropped that request. Anything else?"

    if s["await"] == "lookup_name":
        s["await"] = None
        return list_for(text.strip())

    intent, ent = nlu.analyse(text, s["await"])

    if intent == "goodbye":
        SESS[sid] = new()
        return "You're welcome! Message me any time you need a room."
    if intent == "cancel_booking":
        m = re.search(r"(\d+)", text)
        if not m:
            return "Which booking should I cancel? Send me the booking number, e.g. 'cancel 12'."
        ok = booking.cancel(int(m.group(1)))
        return f"Booking #{m.group(1)} is cancelled." if ok else f"I can't find booking #{m.group(1)}."
    if intent == "list_bookings":
        s["await"] = "lookup_name"
        return "Sure. What name are your bookings under?"
    if intent in ("book_room", "check_availability") or s["await"]:
        if intent in ("book_room", "check_availability"):
            s["mode"] = "check" if intent == "check_availability" else "book"
        return fill_slots(sid, s, text, ent)
    if intent == "greeting":
        return "Hello! I can book a room, check availability, or cancel a booking. What would you like?"
    return "I can help you book a room, check availability, list or cancel bookings. Try 'Book a room for 5 people tomorrow at 2pm'."


def fill_slots(sid, s, text, ent):
    for k, v in ent.items():
        if k in ORDER:
            s["slots"][k] = v
    if s["await"] == "name" and "name" not in ent:
        s["slots"]["name"] = re.sub(r"(?i)^(it'?s|my name is|under|name:?)\s+", "", text.strip()).title()
    err = validate(s["slots"])
    if err:
        s["await"] = [k for k in ORDER if k not in s["slots"]][0]
        return f"{err} {PROMPTS[s['await']]}"

    needed = [k for k in ORDER if not (k == "name" and s["mode"] == "check")]
    missing = [k for k in needed if k not in s["slots"]]
    if missing:
        s["await"] = missing[0]
        return PROMPTS[missing[0]]

    sl = s["slots"]
    start = booking.to_min(sl["time"])
    end = start + int(sl["hours"] * 60)
    rooms = booking.free_rooms(sl["date"], start, end, sl["people"])
    window = f"{sl['date']} {booking.fmt(start)}-{booking.fmt(end)}"
    if not rooms:
        SESS[sid] = new()
        return f"Sorry, no room for {sl['people']} people is free on {window}. Want to try another time?"
    if s["mode"] == "check":
        SESS[sid] = new()
        names = ", ".join(f"{r['name']} (seats {r['capacity']})" for r in rooms)
        return f"Free on {window}: {names}."
    room = rooms[0]
    s["offer"], s["await"] = room, None
    return (f"{room['name']} ({room['kind']}, seats {room['capacity']}) is free on {window} "
            f"for {sl['people']} people. Shall I confirm the booking for {sl['name']}? (yes/no)")


def confirm(sid, s):
    sl, room = s["slots"], s["offer"]
    start = booking.to_min(sl["time"])
    end = start + int(sl["hours"] * 60)
    bid = booking.book(room["name"], sl["date"], start, end, sl["name"], sl["people"])
    SESS[sid] = new()
    if bid is None:
        return "Sorry, that room was just taken. Please start again with a different time."
    return (f"Booked! Booking #{bid}: {room['name']} on {sl['date']}, "
            f"{booking.fmt(start)}-{booking.fmt(end)} for {sl['name']}. Say 'cancel {bid}' to cancel.")


def list_for(name):
    rows = booking.upcoming(name)
    if not rows:
        return f"I found no upcoming bookings for {name}."
    lines = [f"#{r['id']} {r['room']} {r['date']} {booking.fmt(r['start'])}-{booking.fmt(r['end'])}" for r in rows]
    return "Your upcoming bookings: " + "; ".join(lines) + "."
