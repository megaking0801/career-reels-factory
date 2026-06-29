"""用 faster-whisper 把影片/音訊轉成 SRT 字幕（本機、免費）。"""
from pathlib import Path

_model = None
_model_size = None


def _get_model(size: str = "small"):
    global _model, _model_size
    if _model is None or _model_size != size:
        from faster_whisper import WhisperModel
        # CPU + int8：Mac 無 GPU 也能跑
        _model = WhisperModel(size, device="cpu", compute_type="int8")
        _model_size = size
    return _model


def _fmt_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_to_srt(media_path, srt_path, model_size: str = "small", language: str = "zh") -> str:
    model = _get_model(model_size)
    segments, _info = model.transcribe(str(media_path), language=language, beam_size=5)
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    Path(srt_path).write_text("\n".join(lines), encoding="utf-8")
    return str(srt_path)
