"""字幕產生。

主路徑：用 edge-tts 的時間軸 + 我們手上的「正確繁體腳本」直接產 SRT
（不經 whisper，避免簡體與聽錯字）。
後備：拿回的 avatar 若用平台自家 TTS（時間軸不同），用 whisper 取「語音時間範圍」，
但字幕文字一律用已知腳本，不用 whisper 聽出來的字。
"""
import re
from pathlib import Path

# 斷句標點（句尾強停 vs 弱停）
_STRONG = "。！？!?"
_WEAK = "，、；：,;:"
_ALL_PUNCT = _STRONG + _WEAK


def _fmt_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_caption_lines(text: str, max_chars: int = 16) -> list[str]:
    """把一段文字切成 reel 友善的短行：先用標點切小句，再打包到 max_chars。"""
    text = re.sub(r"\s+", "", text.strip())
    if not text:
        return []
    clauses = re.findall(rf"[^{_ALL_PUNCT}]+[{_ALL_PUNCT}]?", text)
    lines: list[str] = []
    cur = ""
    for c in clauses:
        if not cur:
            cur = c
        elif len(cur) + len(c) <= max_chars:
            cur += c
        else:
            lines.append(cur)
            cur = c
        while len(cur) > max_chars:  # 單句仍超長 → 硬切
            lines.append(cur[:max_chars])
            cur = cur[max_chars:]
    if cur:
        lines.append(cur)
    # 去掉行尾的弱標點，字幕較乾淨
    return [l.rstrip(_WEAK) for l in lines if l.strip()]


def _distribute(lines: list[str], t0: float, t1: float) -> list[tuple]:
    """把 [t0,t1] 依各行字數比例分配給每一行。"""
    total = sum(len(l) for l in lines) or 1
    cues = []
    t = t0
    for l in lines:
        dur = (t1 - t0) * len(l) / total
        cues.append((t, t + dur, l))
        t += dur
    return cues


def _write_srt(cues: list[tuple], srt_path) -> str:
    out = []
    for i, (start, end, text) in enumerate(cues, 1):
        if end <= start:
            end = start + 0.4
        out.append(str(i))
        out.append(f"{_fmt_ts(start)} --> {_fmt_ts(end)}")
        out.append(text)
        out.append("")
    Path(srt_path).write_text("\n".join(out), encoding="utf-8")
    return str(srt_path)


# ---- SRT → ASS（寫死 PlayRes，字級/邊距用真實像素，避免 libass 預設 384x288 放大 bug） ----
def _ass_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def parse_srt(srt_path) -> list[tuple]:
    text = Path(srt_path).read_text(encoding="utf-8")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        m = next((_SRT_TIME.search(l) for l in lines if _SRT_TIME.search(l)), None)
        if not m:
            continue
        g = list(map(int, m.groups()))
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = [l for l in lines if not _SRT_TIME.search(l) and not l.strip().isdigit()]
        if body:
            cues.append((start, end, "\\N".join(body)))
    return cues


def write_ass(cues: list[tuple], ass_path, resolution: tuple, style: dict | None = None) -> str:
    w, h = resolution
    style = style or {}
    fn = style.get("font_name") or "Sans"
    fs = style.get("font_size", 58)
    pc = style.get("primary_color", "&H00FFFFFF")
    oc = style.get("outline_color", "&H00000000")
    outline = style.get("outline", 4)
    mv = style.get("margin_v", 210)
    mh = style.get("margin_h", 70)
    align = style.get("alignment", 2)
    bold = 1 if style.get("bold", True) else 0
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{fn},{fs},{pc},&H000000FF,{oc},&H64000000,{bold},0,0,0,"
        f"100,100,0,0,1,{outline},0,{align},{mh},{mh},{mv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    body = [
        f"Dialogue: 0,{_ass_ts(s)},{_ass_ts(e if e > s else s + 0.4)},Default,,0,0,0,,{t}"
        for s, e, t in cues
    ]
    Path(ass_path).write_text(header + "\n".join(body) + "\n", encoding="utf-8")
    return str(ass_path)


def build_srt_from_boundaries(boundaries: list[tuple], srt_path, max_chars: int = 16) -> str:
    """主路徑：用 edge-tts 的 (start, end, text) 時間軸產繁體 SRT。"""
    cues = []
    for start, end, text in boundaries:
        lines = _split_caption_lines(text, max_chars)
        if not lines:
            continue
        cues.extend(_distribute(lines, start, end))
    return _write_srt(cues, srt_path)


def build_srt_from_text(text: str, t0: float, t1: float, srt_path, max_chars: int = 16) -> str:
    """把整段文字平均分配到 [t0,t1]（後備用：只有語音時間範圍時）。"""
    lines = _split_caption_lines(text, max_chars)
    return _write_srt(_distribute(lines, t0, t1), srt_path)


# ---- whisper 後備（只取語音時間範圍，文字仍用已知腳本） ----
_model = None
_model_size = None


def _get_model(size: str = "small"):
    global _model, _model_size
    if _model is None or _model_size != size:
        from faster_whisper import WhisperModel
        _model = WhisperModel(size, device="cpu", compute_type="int8")
        _model_size = size
    return _model


def speech_span(media_path, model_size: str = "small", language: str = "zh") -> tuple:
    """用 whisper 量出語音的起訖時間（秒）。文字丟棄，只要時間範圍。"""
    model = _get_model(model_size)
    segments, _info = model.transcribe(str(media_path), language=language, beam_size=5)
    starts, ends = [], []
    for seg in segments:
        starts.append(seg.start)
        ends.append(seg.end)
    if not starts:
        return 0.0, 0.0
    return min(starts), max(ends)


def srt_from_script_via_whisper(media_path, script_text: str, srt_path,
                                model_size: str = "small", max_chars: int = 16) -> str:
    """後備：whisper 量語音範圍 → 把已知繁體腳本平均分配進去。"""
    t0, t1 = speech_span(media_path, model_size=model_size)
    if t1 <= t0:
        t1 = t0 + 1.0
    return build_srt_from_text(script_text, t0, t1, srt_path, max_chars=max_chars)
