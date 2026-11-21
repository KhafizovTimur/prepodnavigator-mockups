import json
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from timetable.database import connect, search
from timetable.importer import load_snapshot
from timetable.views import teacher_row


class ScheduleTest(unittest.TestCase):
    def test_catalog_shows_institute_to_distinguish_matching_names_and_departments(self):
        row = {"id": 1, "name": "Иванова Анна Петровна", "department": "Центр проектного обучения", "institute": "ВИШ"}
        self.assertIn("Центр проектного обучения · ВИШ", teacher_row(row, [], "Иванова", "name", 1))

    def test_import_merges_groups_and_replaces_snapshot_without_duplicates(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory)
            database = snapshot / "schedule.sqlite3"
            teacher = {"id": 1, "name": "Семёнова Анна", "department": "Кафедра", "institute": "Институт",
                       "studyForm": "full_time", "url": "https://timetable.tyuiu.ru/schedule/teacher/1"}
            lesson = {"id": 10, "dayNumber": 2, "slotId": 12, "date": "2026-11-10", "weekStart": "2026-11-09",
                      "isEven": False, "subject": "Математика", "lessonType": "лекция", "group": "А-1",
                      "subgroup": 0, "room": "208 / Корпус 2", "roomAddress": "Мельникайте, 72"}
            schedule = {"entityType": "teacher", "entity": teacher,
                        "slots": [{"id": 12, "start": "19:00", "end": "20:25"}], "buildings": [],
                        "lessons": [lesson, {**lesson, "id": 11, "group": "А-2", "subgroup": 1},
                                    {**lesson, "id": 12, "date": None, "weekStart": None, "isEven": True}]}
            (snapshot / "catalog.json").write_text(json.dumps([teacher]), encoding="utf-8")
            (snapshot / "complete.json").write_text('{"downloaded_at": "2026-11-07T10:00:00+00:00"}', encoding="utf-8")
            source_page = snapshot / "1.json"
            source_page.write_text(json.dumps(schedule), encoding="utf-8")

            first = load_snapshot(snapshot, database)
            self.assertEqual(first, load_snapshot(snapshot, database))
            self.assertEqual((first["source_lessons"], first["lessons"], first["merged_lessons"]), (3, 2, 1))
            schedule["lessons"][0]["date"] = "2026-11-11"
            source_page.write_text(json.dumps(schedule), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_snapshot(snapshot, database)

            with closing(connect(database)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0], 2)
                dated = db.execute("SELECT * FROM lessons WHERE date = '2026-11-10'").fetchone()
                self.assertEqual((dated["starts"], dated["ends"], dated["building"], dated["room"]),
                                 ("19:00", "20:25", "Корпус 2", "208"))
                self.assertEqual(json.loads(dated["groups"]), [["А-1", 0], ["А-2", 1]])
                recurring = db.execute("SELECT date FROM lessons WHERE period = 'even'").fetchone()
                self.assertEqual(recurring["date"], "")
                for query, mode in [("семенова", "name"), ("математика", "subject"),
                                    ("семенова", "all"), ("математика", "all")]:
                    with self.subTest(query=query, mode=mode):
                        self.assertEqual(search(db, query, mode, 1)[1], 1)
