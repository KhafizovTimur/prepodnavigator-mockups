import gzip
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from tempfile import mkdtemp
from time import sleep
from urllib.request import ProxyHandler, Request, build_opener, getproxies_environment

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://timetable.tyuiu.ru/"
CACHE = ROOT / ".cache"


class InertiaPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reading = False
        self.payload = None

    def handle_starttag(self, tag, attrs):
        self.reading = tag == "script" and dict(attrs).get("type") == "application/json"

    def handle_endtag(self, tag):
        self.reading = False

    def handle_data(self, data):
        if self.reading:
            page = json.loads(data)
            if isinstance(page, dict) and "component" in page:
                self.payload = page


def read_page(url, component):
    opener = build_opener(ProxyHandler(getproxies_environment()))
    request = Request(url, headers={"Accept-Encoding": "gzip", "User-Agent": "Kafedra-Online/1.0"})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=20) as response:
                data = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    data = gzip.decompress(data)
            break
        except (OSError, HTTPException, EOFError) as error:
            if attempt == 2:
                raise RuntimeError(f"Не удалось загрузить {url}: {error}") from error
            sleep(2 ** (attempt + 1))
    parser = InertiaPage()
    parser.feed(data.decode("utf-8"))
    if parser.payload and parser.payload["component"] == component:
        return parser.payload["props"]
    raise ValueError(f"Формат страницы ТИУ изменился: {url}")


def write_json(path, data):
    staged = path.with_suffix(".tmp")
    staged.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    staged.replace(path)


def download_teacher(snapshot, teacher):
    teacher_id = teacher["id"]
    props = read_page(teacher["url"], "Schedule")
    if props["entityType"] != "teacher" or str(props["entity"]["id"]) != str(teacher_id):
        raise ValueError("Страница вернула расписание другого преподавателя")
    write_json(snapshot / f"{teacher_id}.json", props)
    sleep(0.2)


def download(snapshot=None, *, cache=CACHE):
    if snapshot is None:
        catalog = read_page(SOURCE, "Welcome")["teachers"]
        ids = {row["id"] for row in catalog}
        if not catalog or len(ids) != len(catalog):
            raise ValueError("Пустой каталог преподавателей или повторяющиеся ID")
        for row in catalog:
            expected = rf"{re.escape(SOURCE)}schedule/teacher/{re.escape(str(row['id']))}"
            if not str(row["id"]).isdigit() or not re.fullmatch(expected, row["url"]):
                raise ValueError(f"Неизвестный адрес расписания: {row['url']}")
        cache.mkdir(exist_ok=True)
        snapshot = Path(mkdtemp(prefix="tiu-", dir=cache))
        write_json(snapshot / "catalog.json", catalog)
    else:
        catalog = json.loads((snapshot / "catalog.json").read_text(encoding="utf-8"))

    waiting = [row for row in catalog if not (snapshot / f"{row['id']}.json").exists()]
    print(f"Снимок: {snapshot}\nВ каталоге: {len(catalog)}, осталось скачать: {len(waiting)}", flush=True)
    failed = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(download_teacher, snapshot, row): row["id"] for row in waiting}
        for index, job in enumerate(as_completed(jobs), 1):
            try:
                job.result()
            except Exception as error:
                failed[jobs[job]] = str(error)
            if index % 100 == 0 or index == len(jobs):
                print(f"Обработано {index}/{len(jobs)}, ошибок: {len(failed)}", flush=True)

    if failed:
        write_json(snapshot / "errors.json", failed)
        raise RuntimeError(f"Не скачано страниц: {len(failed)}. См. {snapshot / 'errors.json'}")

    if not (snapshot / "complete.json").exists():
        write_json(snapshot / "complete.json", {"downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    (snapshot / "errors.json").unlink(missing_ok=True)
    return snapshot


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Скачать открытые страницы расписания ТИУ")
    parser.add_argument("--resume", type=Path, help="Продолжить скачивание в указанную папку снимка")
    args = parser.parse_args()
    download(args.resume)
