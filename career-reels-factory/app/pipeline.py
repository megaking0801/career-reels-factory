"""流程編排 + job 狀態機。

狀態：created → script_ready → processing → done / failed
"""
import json
import random
from pathlib import Path

from app import jobs
from app.providers.script import generate_script
from app.media import captions, compose

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def run_script_stage(job: dict) -> dict:
    cfg = load_config()
    try:
        # 內容線留空 / 隨機 → 隨機挑一條，存回 job 讓卡片有具體標籤
        pillar = job.get("pillar", "")
        if not pillar or pillar == "隨機":
            pillar = random.choice(cfg.get("pillars") or ["求職硬技能"])
            job["pillar"] = pillar
        # 主題留空 → 讓 AI 自己出題（見 prompts.build_prompt）
        data = generate_script(
            job.get("topic", ""), job.get("notes", ""), pillar, cfg.get("persona", {})
        )
        # 自動出題時，把 AI 想的標題回填成 job 主題，卡片才有意義的名稱
        if not job.get("topic"):
            job["topic"] = data.get("title") or "（AI 自動主題）"
        job["script"] = data
        job["status"] = "script_ready"
        job["error"] = None
    except Exception as e:  # noqa: BLE001 - 回報給前端
        job["status"] = "failed"
        job["error"] = f"腳本生成失敗：{e}"
    return jobs.save(job)


def run_media_stage(job: dict, uploaded_path: str) -> dict:
    cfg = load_config()
    job["status"] = "processing"
    job["error"] = None
    jobs.save(job)
    try:
        srt = jobs.INCOMING / job["id"] / "captions.srt"
        srt.parent.mkdir(parents=True, exist_ok=True)
        captions.transcribe_to_srt(
            uploaded_path, srt, model_size=cfg.get("whisper_model", "small")
        )
        out = jobs.OUTPUT / f"{job['id']}.mp4"
        question = (job.get("script") or {}).get("question_text", "")
        compose.compose(
            uploaded_path, srt, out,
            question_text=question,
            resolution=cfg.get("output_resolution", "1080x1920"),
            caption=cfg.get("caption"),
        )
        job["output"] = f"/data/output/{job['id']}.mp4"
        job["status"] = "done"
        job["error"] = None
    except Exception as e:  # noqa: BLE001 - 回報給前端
        job["status"] = "failed"
        job["error"] = f"影片合成失敗：{e}"
    return jobs.save(job)
