"""腳本 provider：Claude（Anthropic API，繁中品質最佳）。"""
import os
import json
from anthropic import Anthropic


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # 去掉 ```json ... ``` 圍欄
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def generate(system: str, user: str) -> dict:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    msg = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system,
        messages=[{
            "role": "user",
            "content": user + "\n\n直接輸出 JSON 物件，不要任何其他文字。",
        }],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    return json.loads(_strip_fences(text))
