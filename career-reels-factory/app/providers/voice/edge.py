"""edge-tts：把腳本逐字稿合成台灣中文 mp3，並取出逐字時間軸（WordBoundary）。

關鍵：因為我們手上就有「正確的繁體腳本」，字幕直接用這裡產出的時間軸去組，
不必再丟給 whisper 重聽（whisper 會吐簡體＋聽錯字）。
"""
import edge_tts

# 台灣中文聲線
MALE = "zh-TW-YunJheNeural"      # 雲哲，男聲（學長）
FEMALE = "zh-TW-HsiaoChenNeural"  # 曉臻，女聲（學姐）

# WordBoundary 的 offset/duration 單位是 100 奈秒（tick）；除以 1e7 = 秒
_TICKS_PER_SEC = 1e7


def synthesize(text: str, out_mp3, voice: str = MALE, rate: str = "+0%", pitch: str = "+0Hz"):
    """合成 mp3 並回傳 [(start_sec, end_sec, segment_text), ...]。同步版（給背景 thread 用）。

    台灣中文聲線回傳的是 SentenceBoundary（整句一段）；其他情況可能是 WordBoundary。
    兩種都收，交給字幕產生器再依字數切行。
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    boundaries = []
    with open(out_mp3, "wb") as f:
        for chunk in communicate.stream_sync():
            ctype = chunk.get("type")
            if ctype == "audio":
                f.write(chunk["data"])
            elif ctype in ("WordBoundary", "SentenceBoundary"):
                start = chunk["offset"] / _TICKS_PER_SEC
                end = (chunk["offset"] + chunk["duration"]) / _TICKS_PER_SEC
                boundaries.append((start, end, chunk.get("text", "")))
    return str(out_mp3), boundaries
