"""口播語音 provider（可抽換）。

預設用 edge-tts（免費、台灣中文）。日後要換 ElevenLabs 只要新增一個模組、
在這裡接上即可。對外提供 synthesize()，回傳 mp3 路徑與逐字時間軸。
"""
from . import edge as _edge

# 聲線別名：學長 = 男聲、學姐 = 女聲
VOICES = {
    "學長": _edge.MALE,
    "學姐": _edge.FEMALE,
    "male": _edge.MALE,
    "female": _edge.FEMALE,
}


def synthesize(text: str, out_mp3, voice: str = "學長", rate: str = "+0%", pitch: str = "+0Hz"):
    """把逐字稿合成 mp3，回傳 (mp3_path, boundaries)。

    boundaries = [(start_sec, end_sec, word_text), ...]，供後續產字幕用。
    voice 可給別名（學長/學姐）或完整 edge-tts 聲線名。
    """
    real_voice = VOICES.get(voice, voice or _edge.MALE)
    return _edge.synthesize(text, out_mp3, voice=real_voice, rate=rate, pitch=pitch)
