"""Job 持久化：每個 job 一個 JSON 檔。"""
import json
import shutil
import time
import uuid
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
JOBS = DATA / "jobs"
INCOMING = DATA / "incoming"
OUTPUT = DATA / "output"

for _d in (JOBS, INCOMING, OUTPUT):
    _d.mkdir(parents=True, exist_ok=True)


def _path(job_id: str) -> Path:
    return JOBS / f"{job_id}.json"


def create(topic: str, notes: str, pillar: str) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "topic": topic,
        "notes": notes,
        "pillar": pillar,
        "status": "created",
        "created_at": time.time(),
        "script": None,
        "error": None,
        "output": None,
    }
    return save(job)


def save(job: dict) -> dict:
    job["updated_at"] = time.time()
    _path(job["id"]).write_text(
        json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return job


def get(job_id: str):
    p = _path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_all() -> list:
    items = []
    for p in sorted(JOBS.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        items.append(json.loads(p.read_text(encoding="utf-8")))
    return items


def delete(job_id: str) -> bool:
    """刪掉 job 的 JSON、上傳素材與成品。回傳是否真的有刪到。"""
    p = _path(job_id)
    existed = p.exists()
    if existed:
        p.unlink()
    shutil.rmtree(INCOMING / job_id, ignore_errors=True)
    out = OUTPUT / f"{job_id}.mp4"
    if out.exists():
        out.unlink()
    return existed
