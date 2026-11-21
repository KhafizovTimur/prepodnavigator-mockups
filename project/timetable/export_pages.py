import argparse
import json
import shutil
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from .database import PAGE_SIZE, connect
from .source import ROOT
from .views import affiliation, default_period, search_view, teacher_view


def export(destination):
    with closing(connect()) as db, db:
        db.execute("BEGIN")
        teachers = db.execute("SELECT * FROM teachers ORDER BY name_key, id").fetchall()
        updated = db.execute("SELECT value FROM metadata WHERE key = 'downloaded_at'").fetchone()[0]
        rows = db.execute("SELECT * FROM lessons ORDER BY teacher_id, period, day, starts, ends, subject_key, kind_key, place_key")
        schedules = defaultdict(lambda: defaultdict(list))
        weeks = set()
        for row in rows:
            schedules[row["teacher_id"]][row["period"]].append(row)
            if row["date"]:
                weeks.add(row["period"])

        subjects = defaultdict(list)
        for row in db.execute("SELECT teacher_id, MIN(subject) FROM lessons GROUP BY teacher_id, subject_key ORDER BY subject_key"):
            subjects[row[0]].append(row[1])

    if not teachers or not schedules:
        raise ValueError("Сначала загрузите расписание в базу")

    destination.mkdir(parents=True)
    web = ROOT / "web"
    shutil.copytree(web / "assets", destination / "assets")
    shutil.copyfile(web / "pages.js", destination / "pages.js")
    (destination / "index.html").write_text(search_view("", "name", [], {}, 0, 1, 1, static=True), encoding="utf-8")
    catalog = {
        "pageSize": PAGE_SIZE,
        "teachers": [
            {"id": row["id"], "name": row["name"], "affiliation": affiliation(row), "subjects": subjects[row["id"]]}
            for row in teachers
        ],
    }
    (destination / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    weeks = sorted(weeks)
    for teacher in teachers:
        periods = schedules[teacher["id"]]
        initial = default_period(set(periods) or set(weeks))
        path = destination / "teacher" / str(teacher["id"]) / "index.html"
        path.parent.mkdir(parents=True)
        html = teacher_view(teacher, periods.get(initial, []), weeks, initial, "", "name", 1, updated, static_schedules=periods)
        path.write_text(html, encoding="utf-8")
    print(f"GitHub Pages: {len(teachers)} teacher cards exported to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Экспорт расписания для GitHub Pages")
    parser.add_argument("destination", type=Path, help="Путь к новой папке для статических файлов")
    export(parser.parse_args().destination)
