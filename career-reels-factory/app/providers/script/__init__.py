"""腳本 provider 選擇器：可抽換。

預設 auto：有 ANTHROPIC_API_KEY 用 Claude，否則用 Groq（免費）。
之後要換 LLM 只要新增一個 provider 模組 + 在這裡接上即可。
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from app.providers import prompts
from . import groq as groq_provider
from . import claude as claude_provider

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _pick() -> str | None:
    load_dotenv(_ENV_PATH, override=True)
    pref = os.environ.get("SCRIPT_PROVIDER", "auto").lower()
    if pref == "claude":
        return "claude"
    if pref == "groq":
        return "groq"
    # auto
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    return None


def generate_script(topic: str, notes: str, pillar: str, persona: dict) -> dict:
    provider = _pick()
    if provider is None:
        raise RuntimeError(
            "沒有可用的腳本 provider：請在 .env 填入 GROQ_API_KEY（免費）或 ANTHROPIC_API_KEY。"
        )
    system, user = prompts.build_prompt(topic, notes, pillar, persona)
    data = (claude_provider if provider == "claude" else groq_provider).generate(system, user)

    data["_provider"] = provider
    # 組出「貼到 HeyGen 的逐字稿」：開場 + 口播 + 收尾
    lines = [data.get("hook", "")] + list(data.get("voiceover_lines", []) or []) + [data.get("outro", "")]
    data["heygen_script"] = "\n".join(l.strip() for l in lines if l and l.strip())
    return data
