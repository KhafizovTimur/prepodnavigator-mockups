import argparse
import json
import mimetypes
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .database import connect, search, subjects_for
from .export_pages import catalog_data
from .source import ROOT
from .views import PARITIES, TYUMEN, default_period, message_view, search_view, teacher_view

ASSETS = ROOT / "web" / "assets"
TEACHER_PATH = re.compile(r"/teacher/([0-9]{1,12})/?")
ASSET_PATH = re.compile(r"/assets/([a-z0-9-]+\.(?:css|js|svg|woff2))")


def positive_page(value):
    return max(1, int(value)) if re.fullmatch(r"[0-9]{1,6}", value) else 1


def teacher_page(db, teacher_id, period, query, mode, page):
    teacher = db.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if teacher is None:
        return HTTPStatus.NOT_FOUND, message_view("Преподаватель не найден", "Вернитесь в каталог и попробуйте поиск по фамилии.")
    weeks = [row[0] for row in db.execute("SELECT DISTINCT period FROM lessons WHERE date <> '' ORDER BY period")]
    today = datetime.now(TYUMEN).date()
    weeks = sorted(set(weeks) | {(today - timedelta(days=today.weekday())).isoformat()})
    available = {row[0] for row in db.execute("SELECT DISTINCT period FROM lessons WHERE teacher_id = ?", (teacher_id,))}
    if period not in PARITIES and period not in weeks:
        period = default_period(available or set(weeks))
    lessons = db.execute(
        """SELECT * FROM lessons WHERE teacher_id = ? AND period = ?
           ORDER BY day, starts, ends, subject_key, kind_key, place_key""",
        (teacher_id, period),
    ).fetchall()
    updated = db.execute("SELECT value FROM metadata WHERE key = 'downloaded_at'").fetchone()[0]
    return HTTPStatus.OK, teacher_view(teacher, lessons, weeks, period, query, mode, page, updated, available=available)


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def do_GET(self):
        try:
            request = urlsplit(self.path)
            params = parse_qs(request.query, max_num_fields=20)
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        if match := ASSET_PATH.fullmatch(request.path):
            path = ASSETS / match[1]
            if path.is_file():
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self.respond(HTTPStatus.OK, path.read_bytes(), content_type)
                return

        if request.path == "/pages.js":
            self.respond(HTTPStatus.OK, (ROOT / "web/pages.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        teacher = TEACHER_PATH.fullmatch(request.path)
        if request.path in ("/", "/catalog.json") or teacher:
            query = params.get("q", [""])[0][:120].strip()
            mode = "all"
            page = positive_page(params.get("page", [""])[0])
            try:
                with closing(connect()) as db, db:
                    db.execute("BEGIN")
                    if request.path == "/catalog.json":
                        teachers = db.execute("SELECT * FROM teachers ORDER BY name_key, id").fetchall()
                        payload = json.dumps(catalog_data(db, teachers), ensure_ascii=False).encode("utf-8")
                        self.respond(HTTPStatus.OK, payload, "application/json; charset=utf-8")
                        return
                    if teacher:
                        status, html = teacher_page(db, int(teacher[1]), params.get("period", [""])[0], query, mode, page)
                    elif params.get("view") == ["retakes"]:
                        status, html = HTTPStatus.OK, search_view("", mode, [], {}, 0, 1, 1, retake_index=True)
                    else:
                        teachers, total, page, pages = search(db, query, mode, page)
                        subjects = subjects_for(db, teachers, query if mode == "subject" else "")
                        status = HTTPStatus.OK
                        html = search_view(query, mode, teachers, subjects, total, page, pages)
            except sqlite3.Error as error:
                self.log_error("Ошибка чтения базы расписания: %s", error)
                status = HTTPStatus.SERVICE_UNAVAILABLE
                html = message_view("Расписание пока недоступно", "Попробуйте открыть страницу ещё раз чуть позже.")
        else:
            status = HTTPStatus.NOT_FOUND
            html = message_view("Страница не найдена", "Проверьте адрес или вернитесь к поиску преподавателя.")
        self.respond(status, html.encode("utf-8"), "text/html; charset=utf-8")

    do_HEAD = do_GET


def main():
    parser = argparse.ArgumentParser(description="Запустить сайт «Кафедра Онлайн»")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"Кафедра Онлайн: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
