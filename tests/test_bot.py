import os
import sys
import tempfile

os.environ["ROOMS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import booking, bot  # noqa: E402

booking.init()


def chat(sid, *msgs):
    return [bot.reply(sid, m) for m in msgs]


def test_full_booking_flow():
    r = chat("a", "book a room", "tomorrow", "2pm", "2", "5", "Asha", "yes")
    assert "Bhaskara" in r[5] and "Booked" in r[6]


def test_conflict_hides_booked_room():
    chat("b", "book a room for 5 people tomorrow at 10am for 2 hours", "Ravi", "yes")
    r = chat("c", "check availability for 8 people tomorrow at 11am for 1 hour")
    assert "Bhaskara" not in r[0] and "Charaka" in r[0]


def test_validation_opening_hours():
    assert "08:00" in chat("d", "book a room tomorrow at 6am for 1 hour")[0]


def test_list_and_cancel():
    chat("e", "book a room for 2 people tomorrow at 3pm for 1 hour", "Meena", "yes")
    chat("e", "show my bookings")
    assert "Eka" in bot.reply("e", "Meena")
    bid = booking.upcoming("Meena")[0]["id"]
    assert "cancelled" in bot.reply("e", f"cancel booking {bid}")
