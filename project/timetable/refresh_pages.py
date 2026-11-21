"""Download a complete TIU timetable and publish its database for the Pages build."""
import gzip
import json
import os
import shutil
import subprocess
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from .importer import load_snapshot
from .source import CACHE, download

REPOSITORY = "https://github.com/KhafizovTimur/prepodnavigator-mockups.git"
DATA_FILE = Path("project/data/schedule.sqlite3.gz")


def git(*args, cwd):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, timeout=240,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))


def refresh():
    CACHE.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="daily-", dir=CACHE) as directory:
        work = Path(directory)
        repo = work / "release"
        git("clone", "--quiet", "--depth=1", "--branch", "main", REPOSITORY, str(repo), cwd=work)
        snapshot = download(cache=work)
        database = work / "schedule.sqlite3"
        report = load_snapshot(snapshot, database)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        # Import locally with the same transaction and stale-snapshot guard as a manual update.
        load_snapshot(snapshot)
        with database.open("rb") as data, gzip.open(repo / DATA_FILE, "wb") as bundle:
            shutil.copyfileobj(data, bundle)
        git("add", "--", DATA_FILE.as_posix(), cwd=repo)
        git("-c", "user.name=Kafedra Online", "-c", "user.email=kafedra-online@users.noreply.github.com",
            "commit", "-m", "Обновить расписание ТИУ " + report["downloaded_at"][:10], cwd=repo)
        git("push", "origin", "HEAD:main", cwd=repo)
        print("Снимок отправлен для публикации на GitHub Pages.", flush=True)


def main():
    CACHE.mkdir(exist_ok=True)
    with (CACHE / "daily-update.log").open("a", encoding="utf-8", buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            print(datetime.now().astimezone().isoformat(timespec="seconds"))
            try:
                refresh()
            except Exception:
                traceback.print_exc()
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

