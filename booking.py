"""Room inventory and booking storage (SQLite). Times are stored as minutes after midnight."""
import os
import sqlite3
import datetime as dt

DB = os.getenv("ROOMS_DB", "rooms.db")
ROOMS = [("Eka", 2, "huddle"), ("Aryabhata", 4, "meeting"), ("Bhaskara", 8, "meeting"),
         ("Charaka", 12, "conference"), ("Dhruva", 30, "seminar")]


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS rooms(name TEXT PRIMARY KEY, capacity INT, kind TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, date TEXT, start INT, end INT,
            name TEXT, people INT, created TEXT)""")
        c.executemany("INSERT OR IGNORE INTO rooms VALUES(?,?,?)", ROOMS)


def to_min(hhmm):
    h, m = hhmm.split(":")[:2]
    return int(h) * 60 + int(m)


def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def free_rooms(date, start, end, people):
    """Rooms that fit `people` and have no overlapping booking, smallest first."""
    with conn() as c:
        rows = c.execute("""SELECT * FROM rooms r WHERE capacity >= ? AND NOT EXISTS (
            SELECT 1 FROM bookings b WHERE b.room = r.name AND b.date = ?
            AND b.start < ? AND b.end > ?) ORDER BY capacity""", (people, date, end, start)).fetchall()
    return [dict(r) for r in rows]


def book(room, date, start, end, name, people):
    """Insert a booking; returns id, or None if the slot was taken meanwhile."""
    with conn() as c:
        clash = c.execute("SELECT 1 FROM bookings WHERE room=? AND date=? AND start<? AND end>?",
                          (room, date, end, start)).fetchone()
        if clash:
            return None
        cur = c.execute("INSERT INTO bookings(room,date,start,end,name,people,created) VALUES(?,?,?,?,?,?,?)",
                        (room, date, start, end, name, people, dt.datetime.now().isoformat()))
        return cur.lastrowid


def cancel(booking_id):
    with conn() as c:
        return c.execute("DELETE FROM bookings WHERE id=?", (booking_id,)).rowcount > 0


def upcoming(name):
    today = dt.date.today().isoformat()
    with conn() as c:
        rows = c.execute("SELECT * FROM bookings WHERE lower(name)=lower(?) AND date>=? ORDER BY date,start",
                         (name, today)).fetchall()
    return [dict(r) for r in rows]
