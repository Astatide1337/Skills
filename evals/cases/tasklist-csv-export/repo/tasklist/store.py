import json
import os
from datetime import datetime, timezone
from pathlib import Path


def path() -> Path:
    return Path(os.environ.get("TASKLIST_FILE", "tasks.json"))


def load() -> list[dict]:
    p = path()
    return json.loads(p.read_text()) if p.exists() else []


def save(tasks: list[dict]) -> None:
    path().write_text(json.dumps(tasks, indent=2))


def add(title: str) -> dict:
    tasks = load()
    task = {"id": len(tasks) + 1, "title": title, "done": False,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    tasks.append(task)
    save(tasks)
    return task


def mark_done(task_id: int) -> None:
    tasks = load()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            save(tasks)
            return
    raise KeyError(task_id)
