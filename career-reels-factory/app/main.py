"""FastAPI：入口 UI + REST API + 成果靜態服務。"""
import json
import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app import jobs, pipeline  # noqa: E402  (需在 load_dotenv 之後)

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="職場短影音內容工廠")


@app.get("/api/config")
async def get_config():
    cfg = pipeline.load_config()
    return {
        "pillars": cfg.get("pillars", []),
        "topics": cfg.get("topics", []),
        "persona": cfg.get("persona", {}),
    }


@app.post("/api/jobs")
async def create_job(
    background: BackgroundTasks,
    topic: str = Form(""),
    notes: str = Form(""),
    pillar: str = Form(""),
):
    # 主題、內容線皆可留空 → 由 AI 自動決定（見 pipeline.run_script_stage）
    job = jobs.create(topic.strip(), notes.strip(), pillar.strip())
    background.add_task(pipeline.run_script_stage, job)
    return job


@app.get("/api/jobs")
async def list_jobs():
    return jobs.list_all()


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "找不到 job")
    return job


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    if not jobs.delete(job_id):
        raise HTTPException(404, "找不到 job")
    return {"ok": True}


@app.get("/api/jobs/{job_id}/voiceover")
async def get_voiceover(job_id: str):
    mp3 = jobs.INCOMING / job_id / "voiceover.mp3"
    if not mp3.exists():
        raise HTTPException(404, "這個任務還沒有口播語音")
    return FileResponse(str(mp3), media_type="audio/mpeg", filename=f"voiceover_{job_id}.mp3")


@app.post("/api/jobs/{job_id}/retry-script")
async def retry_script(job_id: str, background: BackgroundTasks):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "找不到 job")
    job["status"] = "created"
    jobs.save(job)
    background.add_task(pipeline.run_script_stage, job)
    return job


@app.post("/api/jobs/{job_id}/video")
async def upload_video(
    job_id: str, background: BackgroundTasks, file: UploadFile = File(...)
):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "找不到 job")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".mp4", ".mov", ".m4v"):
        raise HTTPException(400, "請上傳 mp4 / mov 影片")
    dest_dir = jobs.INCOMING / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"source{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    job["status"] = "processing"
    jobs.save(job)
    background.add_task(pipeline.run_media_stage, job, str(dest))
    return job


# 成品與前端靜態檔（API 路由先註冊，靜態掛載放最後避免遮蔽）
app.mount("/data/output", StaticFiles(directory=str(jobs.OUTPUT)), name="output")
app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
