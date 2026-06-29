"""流程編排 + job 狀態機。

狀態：created → script_ready → processing → done / failed

腳本階段除了產腳本，還會順手：
  1) 用 edge-tts 把口播逐字稿合成 mp3（拿去餵 OmniHuman 等 avatar 工具）
  2) 由語音時間軸產「正確繁體」字幕 SRT（不經 whisper）
  3) 產一段「邊走邊講」的 avatar 場景 prompt
媒體階段優先用這份預產 SRT；若沒有（例如 avatar 用了別的 TTS）才用 whisper 後備。
"""
import json
import random
from pathlib import Path

from app import jobs
from app.providers.script import generate_script
from app.providers import prompts, voice
from app.media import captions, compose

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def _make_voiceover(job: dict, cfg: dict) -> None:
    """口播語音 + 繁體字幕。容錯：失敗不影響腳本就緒（媒體階段還有 whisper 後備）。"""
    text = (job.get("script") or {}).get("heygen_script") or ""
    if not text.strip():
        return
    d = jobs.INCOMING / job["id"]
    d.mkdir(parents=True, exist_ok=True)
    mp3 = d / "voiceover.mp3"
    _, boundaries = voice.synthesize(text, mp3, voice=cfg.get("voice", "學長"))
    max_chars = (cfg.get("caption") or {}).get("max_chars", 15)
    captions.build_srt_from_boundaries(boundaries, d / "captions.srt", max_chars=max_chars)
    job["voiceover"] = f"/api/jobs/{job['id']}/voiceover"


def run_script_stage(job: dict) -> dict:
    cfg = load_config()
    try:
        # 內容線留空 / 隨機 → 隨機挑一條
        pillar = job.get("pillar", "")
        if not pillar or pillar == "隨機":
            pillar = random.choice(cfg.get("pillars") or ["求職硬技能"])
            job["pillar"] = pillar
        data = generate_script(
            job.get("topic", ""), job.get("notes", ""), pillar, cfg.get("persona", {})
        )
        if not job.get("topic"):
            job["topic"] = data.get("title") or "（AI 自動主題）"
        data["scene_prompt"] = prompts.build_scene_prompt(cfg.get("persona", {}), data)
        job["script"] = data
        job["status"] = "script_ready"
        job["error"] = None
        # 口播語音 + 字幕（容錯）
        job["voice_error"] = None
        try:
            _make_voiceover(job, cfg)
        except Exception as e:  # noqa: BLE001
            job["voice_error"] = f"口播語音生成失敗（可改用 avatar 工具內建 TTS，或稍後重試）：{e}"
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
        d = jobs.INCOMING / job["id"]
        d.mkdir(parents=True, exist_ok=True)
        srt = d / "captions.srt"
        script_text = (job.get("script") or {}).get("heygen_script") or ""
        # 預產字幕在時間上要和上傳影片對得起來；對不上（avatar 用了別的 TTS）就用 whisper 後備
        use_prebuilt = srt.exists() and _srt_matches(srt, uploaded_path)
        if not use_prebuilt:
            captions.srt_from_script_via_whisper(
                uploaded_path, script_text, srt,
                model_size=cfg.get("whisper_model", "small"),
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


def _srt_matches(srt_path: Path, video_path: str, tol: float = 2.0) -> bool:
    """預產 SRT 的長度與上傳影片時長差距在容許範圍內，才採用。"""
    try:
        vid = compose.probe_duration(video_path)
        cues = captions.parse_srt(srt_path)
        if not cues or not vid:
            return False
        srt_end = cues[-1][1]
        return abs(srt_end - vid) <= tol
    except Exception:  # noqa: BLE001
        return False
