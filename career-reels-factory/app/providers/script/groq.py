"""腳本 provider：Groq（免費額度）。"""
import os
import json
from groq import Groq


def generate(system: str, user: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.8,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
