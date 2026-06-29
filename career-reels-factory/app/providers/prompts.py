"""腳本生成的 prompt 模板（人設 + 藏鏡人街訪格式）。"""


def build_prompt(topic: str, notes: str, pillar: str, persona: dict):
    persona_desc = persona.get("style", "一位中肯的職場前輩")
    system = (
        f"你是台灣職場短影音帳號的腳本編劇。帳號人設：{persona_desc}\n"
        "格式是「藏鏡人街訪」：鏡頭後一個看不見的提問者丟出痛點問題（會做成開場字卡），"
        "鏡頭前的前輩用口播回答。平台是 IG Reels，直式，總長 15–40 秒。"
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
        '  "voiceover_lines": ["導師口播逐字稿，2-4 句，最多講 3 個重點，口語、講人話"],\n'
        '  "outro": "收尾金句 + 一句追蹤 CTA",\n'
        '  "scene_notes": "畫面/運鏡建議，例如走在哪、字幕重點字"\n'
        "}\n\n"
        "要求：用台灣用語、口語；內容要正確、站得住腳；不要說教腔；Hook 要有記憶點。"
    )
    return system, user
