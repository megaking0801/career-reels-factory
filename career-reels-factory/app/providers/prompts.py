"""腳本生成的 prompt 模板（人設 + 藏鏡人街訪格式）。"""


def build_prompt(topic: str, notes: str, pillar: str, persona: dict):
    persona_desc = persona.get("style", "一位中肯的職場前輩")
    system = (
        f"你是台灣職場短影音帳號的腳本編劇。帳號人設：{persona_desc}\n"
        "格式是「藏鏡人街訪」：鏡頭後一個看不見的提問者丟出痛點問題（會做成開場字卡），"
        "鏡頭前的前輩邊走邊用口播回答。平台是 IG Reels，直式，總長約 45–60 秒。"
    )
    topic_line = (
        f"主題：{topic}\n"
        if topic
        else "主題：（請你自己決定一個此內容線底下、最近會紅、台灣上班族有共鳴的具體主題，不要太空泛）\n"
    )
    user = (
        "請為以下需求產出 1 支腳本。\n"
        f"{topic_line}"
        f"內容線：{pillar}\n"
        f"額外調整方向：{notes or '（無）'}\n\n"
        "只輸出 JSON（不要 markdown 圍欄、不要多餘文字），格式如下：\n"
        "{\n"
        '  "title": "短標題",\n'
        f'  "pillar": "{pillar}",\n'
        '  "question_text": "藏鏡人的開場問題，一句，戳痛點，會放成開場字卡",\n'
        '  "hook": "導師開場第一句，要嗆或反差，能讓人停下來",\n'
        '  "voiceover_lines": ["導師口播逐字稿，4-7 句、合計約 45–60 秒（中文約 200–280 字），講 3 個重點，口語、講人話、句子之間能自然銜接"],\n'
        '  "outro": "收尾金句 + 一句追蹤 CTA",\n'
        '  "scene_notes": "畫面/運鏡建議，例如走在哪、字幕重點字"\n'
        "}\n\n"
        "要求：用台灣用語、口語；內容要正確、站得住腳；不要說教腔；Hook 要有記憶點。"
    )
    return system, user


def build_scene_prompt(persona: dict, script: dict) -> str:
    """產一段給 avatar 影片生成工具（OmniHuman 等）的「邊走邊講」場景 prompt。

    丟「固定角色圖 + 口播語音 mp3 + 這段 prompt」即可生成走動 avatar。
    """
    name = persona.get("name", "職涯前輩")
    scene = (script or {}).get("scene_notes", "")
    base = (
        f"A consistent virtual Taiwanese career mentor ({name}), walking and talking to camera "
        "on a busy modern office/city street, natural hand gestures, confident friendly expression, "
        "lips synced to the provided audio, vertical 9:16 framing, cinematic shallow depth of field, "
        "smooth handheld walking shot, daytime."
    )
    if scene:
        base += f" 參考畫面方向：{scene}"
    return base
