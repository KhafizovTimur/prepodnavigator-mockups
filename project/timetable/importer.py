import argparse
import json
from collections import defaultdict
from contextlib import closing
from datetime import date, time, timedelta
from pathlib import Path

from .database import DATABASE, SCHEMA, connect, search_key
from .source import SOURCE, download


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value):
    return " ".join((value or "").split())


def group_teachers(catalog):
    matches = defaultdict(list)
    for row in catalog:
        identity = tuple(search_key(clean(row[field])) for field in ("name", "department", "institute"))
        matches[identity].append(row)
    for identity, rows in matches.items():
        forms = {row["studyForm"] for row in rows}
        if all(identity) and len(rows) == 2 and forms == {"full_time", "part_time"}:
            yield sorted(rows, key=lambda row: row["studyForm"])
        else:
            for row in rows:
                yield [row]


def lesson_timing(lesson, slots):
    day = lesson["dayNumber"]
    slot = slots[lesson["slotId"]]
    starts = time.fromisoformat(slot["start"]).isoformat(timespec="minutes")
    ends = time.fromisoformat(slot["end"]).isoformat(timespec="minutes")
    if day not in range(1, 8) or starts >= ends:
        raise ValueError("Недопустимый день недели или время пары")
    if lesson["date"] is None:
        if not isinstance(lesson["isEven"], bool):
            raise ValueError("Для повторяющегося занятия не указана чётность недели")
        return "even" if lesson["isEven"] else "odd", day, "", starts, ends
    lesson_date = date.fromisoformat(lesson["date"])
    monday = (lesson_date - timedelta(days=lesson_date.weekday())).isoformat()
    if lesson_date.isoweekday() != day or lesson["weekStart"] != monday:
        raise ValueError("Дата занятия не совпадает с днём недели или началом недели в ТИУ")
    return monday, day, lesson_date.isoformat(), starts, ends


def lesson_place(lesson, buildings):
    room, separator, building = clean(lesson["room"]).rpartition(" / ")
    if not separator:
        room, building = building, ""
    address = clean(lesson["roomAddress"]) or buildings.get(building, "")
    if search_key(room) in {"online", "онлайн"}:
        return "", "Онлайн", ""
    if search_key(building) == "корпус 0":
        building = ""
    return building, room, address


def add_schedule(lessons, teacher_id, schedule):
    slots = {slot["id"]: slot for slot in schedule["slots"]}
    buildings = {clean(row["name"]): clean(row["address"]) for row in schedule["buildings"]}
    for lesson in schedule["lessons"]:
        try:
            period, day, lesson_date, starts, ends = lesson_timing(lesson, slots)
            subject = clean(lesson["subject"])
            kind = clean(lesson["lessonType"])
            building, room, address = lesson_place(lesson, buildings)
            if not subject:
                raise ValueError("Пустое название дисциплины")
        except (KeyError, ValueError) as error:
            raise ValueError(f"Занятие {lesson.get('id')}: {error}") from error
        subject_key, kind_key = search_key(subject), search_key(kind)
        place_key = json.dumps([search_key(value) for value in (building, room, address)], ensure_ascii=False)
        key = (teacher_id, period, day, starts, ends, subject_key, kind_key, place_key)
        if key not in lessons:
            row = (teacher_id, period, day, lesson_date, starts, ends, subject, subject_key, kind, building, room,
                   address, place_key, kind_key)
            lessons[key] = (row, set())
        if group := clean(lesson["group"]):
            lessons[key][1].add((group, lesson["subgroup"] or 0))


def load_snapshot(snapshot, database=DATABASE):
    catalog = read_json(snapshot / "catalog.json")
    finished = read_json(snapshot / "complete.json")
    teachers, lessons = [], {}
    raw_count = 0
    for sources in group_teachers(catalog):
        primary = sources[0]
        teacher_id = primary["id"]
        links = [{"url": row["url"], "form": row["studyForm"]} for row in sources]
        teachers.append((teacher_id, clean(primary["name"]), search_key(clean(primary["name"])),
                         clean(primary["department"]), clean(primary["institute"]), json.dumps(links)))
        for row in sources:
            schedule = read_json(snapshot / f"{row['id']}.json")
            if schedule["entityType"] != "teacher" or schedule["entity"]["id"] != row["id"]:
                raise ValueError(f"Несовпадение ID преподавателя: {row['id']}")
            try:
                add_schedule(lessons, teacher_id, schedule)
            except ValueError as error:
                raise ValueError(f"Страница {row['url']}: {error}") from error
            raw_count += len(schedule["lessons"])
    if not teachers or not lessons:
        raise ValueError("Пустой снимок расписания")

    dated = [row[3] for row, _ in lessons.values() if row[3]]
    report = {
        "source": SOURCE,
        "downloaded_at": finished["downloaded_at"],
        "source_pages": len(catalog),
        "teachers": len(teachers),
        "source_lessons": raw_count,
        "lessons": len(lessons),
        "merged_lessons": raw_count - len(lessons),
        "dated_lessons": len(dated),
        "recurring_lessons": len(lessons) - len(dated),
        "first_date": min(dated, default=""),
        "last_date": max(dated, default=""),
    }
    database.parent.mkdir(exist_ok=True)
    with closing(connect(database, readonly=False)) as db:
        db.executescript(SCHEMA)
        with db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT value FROM metadata WHERE key = 'downloaded_at'").fetchone()
            if previous and previous[0] > report["downloaded_at"]:
                raise ValueError("Этот снимок старее данных в базе")
            for table in ("lessons", "teachers", "metadata"):
                db.execute(f"DELETE FROM {table}")
            db.executemany("INSERT INTO teachers VALUES (?, ?, ?, ?, ?, ?)", teachers)
            db.executemany("INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           ((*row, json.dumps(sorted(groups), ensure_ascii=False)) for row, groups in lessons.values()))
            db.executemany("INSERT INTO metadata VALUES (?, ?)", report.items())
    return report


def main():
    parser = argparse.ArgumentParser(description="Загрузить расписание ТИУ в базу проекта")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--snapshot", type=Path, help="Использовать уже скачанный полный снимок")
    choice.add_argument("--resume", type=Path, help="Докачать страницы в существующий снимок")
    args = parser.parse_args()
    snapshot = args.snapshot or download(args.resume)
    print(json.dumps(load_snapshot(snapshot), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
