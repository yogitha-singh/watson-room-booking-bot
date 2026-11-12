"""Language understanding. Uses IBM Watson Assistant when credentials exist,
otherwise a keyword/regex fallback so the bot still runs offline (demo mode)."""
import os
import re
import datetime as dt

API_KEY = os.getenv("WATSON_API_KEY")
URL = os.getenv("WATSON_URL")
ASSISTANT_ID = os.getenv("WATSON_ASSISTANT_ID")
_watson = None

if API_KEY and URL and ASSISTANT_ID:
    from ibm_watson import AssistantV2
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    _watson = AssistantV2(version="2023-06-15", authenticator=IAMAuthenticator(API_KEY))
    _watson.set_service_url(URL)

KEYWORDS = [
    ("cancel_booking", r"\bcancel|delete booking|remove booking"),
    ("list_bookings", r"my bookings|my reservations|show bookings|list bookings"),
    ("check_availability", r"availab|free rooms?|is there a room|any room"),
    ("book_room", r"\bbook|reserve|need a room|want a room|schedule"),
    ("goodbye", r"\b(bye|goodbye|see you|thanks|thank you)\b"),
    ("greeting", r"\b(hi|hello|hey|good (morning|afternoon|evening))\b"),
]


def _today():
    return dt.date.today()


def regex_entities(text, awaiting=None):
    t = text.lower()
    ent = {}
    if "tomorrow" in t:
        ent["date"] = (_today() + dt.timedelta(days=1)).isoformat()
    elif "today" in t:
        ent["date"] = _today().isoformat()
    elif m := re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t):
        ent["date"] = m.group(1)
    if m := re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t):
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
        ent["time"] = f"{h:02d}:{m.group(2) or '00'}"
    elif m := re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", t):
        ent["time"] = f"{int(m.group(1)):02d}:{m.group(2)}"
    if m := re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", t):
        ent["hours"] = float(m.group(1))
    if m := re.search(r"(\d+)\s*(?:people|persons?|attendees|members|pax|guests)", t):
        ent["people"] = int(m.group(1))
    if awaiting in ("hours", "people", "time") and awaiting not in ent:
        if m := re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", t):
            v = float(m.group(1))
            ent[awaiting] = f"{int(v):02d}:00" if awaiting == "time" else (int(v) if awaiting == "people" else v)
    return ent


def watson_analyse(text):
    res = _watson.message_stateless(assistant_id=ASSISTANT_ID,
                                    input={"message_type": "text", "text": text}).get_result()
    out = res["output"]
    intent = out["intents"][0]["intent"] if out.get("intents") else None
    ent = {}
    for e in out.get("entities", []):
        name, val = e["entity"], e["value"]
        if name == "sys-date":
            ent["date"] = val
        elif name == "sys-time":
            ent["time"] = val[:5]
        elif name == "sys-number" and re.search(r"(people|persons|attendees)", text.lower()):
            ent["people"] = int(float(val))
    return intent, ent


def analyse(text, awaiting=None):
    """Return (intent, entities). Watson wins when available; regex fills any gaps."""
    ent = regex_entities(text, awaiting)
    intent = None
    if _watson:
        try:
            intent, w_ent = watson_analyse(text)
            ent.update(w_ent)
        except Exception as exc:  # network/quota errors: degrade gracefully
            print("Watson error, using fallback:", exc)
    if not intent:
        low = text.lower()
        intent = next((i for i, p in KEYWORDS if re.search(p, low)), None)
    return intent, ent
