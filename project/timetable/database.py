import sqlite3
from pathlib import Path

from .source import ROOT

DATABASE = ROOT / "data" / "schedule.sqlite3"
PAGE_SIZE = 15

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    department TEXT NOT NULL,
    institute TEXT NOT NULL,
    sources TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    period TEXT NOT NULL,
    day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 7),
    date TEXT NOT NULL,
    starts TEXT NOT NULL,
    ends TEXT NOT NULL,
    subject TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    building TEXT NOT NULL,
    room TEXT NOT NULL,
    address TEXT NOT NULL,
    place_key TEXT NOT NULL,
    kind_key TEXT NOT NULL,
    groups TEXT NOT NULL,
    PRIMARY KEY (teacher_id, period, day, starts, ends, subject_key, kind_key, place_key)
) WITHOUT ROWID;
"""


def connect(path: Path = DATABASE, *, readonly=True):
    db = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) if readonly else sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def search_key(value):
    return " ".join(value.casefold().replace("ё", "е").split())


def search(db, query, mode, page):
    words = search_key(query).split()
    if mode in ("subject", "all") and words:
        predicate = " AND ".join(["instr(l.subject_key, ?) > 0"] * len(words))
        match = f"WHERE EXISTS (SELECT 1 FROM lessons l WHERE l.teacher_id = t.id AND {predicate})"
        if mode == "all":
            match += " OR (" + " AND ".join(["instr(t.name_key, ?) > 0"] * len(words)) + ")"
            words = words * 2
    else:
        predicate = " AND ".join(["instr(t.name_key, ?) > 0"] * len(words))
        match = f"WHERE {predicate}" if predicate else ""
    total = db.execute(f"SELECT COUNT(*) FROM teachers t {match}", words).fetchone()[0]
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    teachers = db.execute(
        f"SELECT t.* FROM teachers t {match} ORDER BY t.name_key, t.id LIMIT ? OFFSET ?",
        (*words, PAGE_SIZE, (page - 1) * PAGE_SIZE),
    ).fetchall()
    return teachers, total, page, pages


def subjects_for(db, teachers, query):
    if not teachers:
        return {}
    ids = [teacher["id"] for teacher in teachers]
    words = search_key(query).split()
    placeholders = ",".join(["?"] * len(ids))
    rows = db.execute(
        f"""SELECT teacher_id, MIN(subject) AS subject, subject_key
            FROM lessons WHERE teacher_id IN ({placeholders})
            GROUP BY teacher_id, subject_key ORDER BY subject_key""",
        ids,
    )
    subjects = {teacher_id: [] for teacher_id in ids}
    for row in rows:
        if all(word in row["subject_key"] for word in words):
            subjects[row["teacher_id"]].append(row["subject"])
    return subjects
