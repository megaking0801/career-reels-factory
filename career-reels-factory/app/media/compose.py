"""用 FFmpeg 把 avatar 影片合成成「藏鏡人街訪」直式 reel。

版面（1080x1920，三區，吃掉死邊）：
  上方帶  ── 藏鏡人提問字卡（路人提問，整片持續顯示）
  中段    ── avatar（等比縮放置中），背景用 avatar 模糊放大鋪滿（無黑/白死邊）
  下三分之一 ── 回答字幕（繁體，安全區、不蓋臉）
"""
import os
import subprocess
import textwrap
from pathlib import Path

from app.media import captions

# 候選中文字型 (檔案路徑, libass 家族名)。會挑第一個存在的。
# macOS / Windows 內建字型路徑不同，所以自動偵測而非寫死。
_FONT_CANDIDATES = [
    (os.environ.get("CJK_FONT"), os.environ.get("CJK_FONT_NAME", "PingFang TC")),
    # Windows
    ("C:/Windows/Fonts/msjhbd.ttc", "Microsoft JhengHei"),
    ("C:/Windows/Fonts/msjh.ttc", "Microsoft JhengHei"),
    ("C:/Windows/Fonts/mingliu.ttc", "MingLiU"),
    ("C:/Windows/Fonts/NotoSansCJK-Regular.ttc", "Noto Sans CJK TC"),
    # macOS
    ("/System/Library/Fonts/PingFang.ttc", "PingFang TC"),
    ("/System/Library/Fonts/STHeiti Medium.ttc", "Heiti TC"),
    ("/System/Library/Fonts/STHeiti Light.ttc", "Heiti TC"),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", "Hiragino Sans GB"),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti TC"),
]


def probe_duration(path) -> float:
    """用 ffprobe 取影片秒數；失敗回 0。"""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True,
        )
        return float(proc.stdout.strip())
    except Exception:  # noqa: BLE001
        return 0.0


def _resolve_font():
    for path, name in _FONT_CANDIDATES:
        if path and os.path.exists(path):
            return path, name, str(Path(path).parent)
    return None, None, None


def _escape_path(path: str) -> str:
    """供 filter 內單引號字串使用：反斜線→正斜線、跳脫冒號（Windows subtitles/drawtext 友善）。"""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _wrap_question(text: str, width: int = 16, max_lines: int = 3) -> str:
    """把藏鏡人提問依寬度折行（中文逐字折），最多 max_lines 行。"""
    text = (text or "").strip()
    if not text:
        return ""
    lines = textwrap.wrap(text, width=width) or [text]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，、。！？") + "…"
    return "\n".join(lines)


def compose(input_video, srt_path, output_path, question_text: str = "",
            resolution: str = "1080x1920", caption: dict | None = None) -> str:
    w, h = (int(x) for x in resolution.split("x"))
    caption = caption or {}
    font_file, font_name, fonts_dir = _resolve_font()

    # ── 版面分區（依輸出高度比例）──
    band_top_h = int(h * 0.15)          # 上方提問帶高度
    avatar_top = int(h * 0.175)         # avatar 區起點
    avatar_band_h = int(h * 0.55)       # avatar 區高度（中段）

    # ── filter graph ──
    # 背景：放大裁切鋪滿 + 模糊 + 壓暗 scrim；前景：等比縮放塞進中段
    parts = [
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},boxblur=26:2,eq=saturation=0.85,"
        f"drawbox=x=0:y=0:w={w}:h={h}:color=black@0.30:t=fill[bg]",
        f"[0:v]scale={w}:{avatar_band_h}:force_original_aspect_ratio=decrease[fg]",
        f"[bg][fg]overlay=x=(W-w)/2:y={avatar_top}+({avatar_band_h}-h)/2[base]",
    ]
    last = "base"

    # 回答字幕（下三分之一）：SRT → ASS（寫死 PlayRes，字級/邊距用真實像素）
    ass_path = None
    if srt_path and Path(srt_path).exists():
        ass_path = Path(output_path).with_suffix(".ass")
        captions.write_ass(
            captions.parse_srt(srt_path), ass_path, (w, h),
            style={
                "font_name": font_name,
                "font_size": caption.get("font_size", 60),
                "primary_color": caption.get("primary_color", "&H00FFFFFF"),
                "outline_color": caption.get("outline_color", "&H00000000"),
                "outline": caption.get("outline", 4),
                "margin_v": caption.get("margin_v", int(h * 0.11)),
                "margin_h": caption.get("margin_h", 70),
            },
        )
        subs = f"subtitles='{_escape_path(ass_path)}'"
        if fonts_dir:
            subs += f":fontsdir='{_escape_path(fonts_dir)}'"
        parts.append(f"[{last}]{subs}[subbed]")
        last = "subbed"

    # 上方藏鏡人提問字卡（需要實體字型檔；找不到就略過）
    qfile = None
    if question_text and font_file:
        wrapped = _wrap_question(question_text, width=caption.get("q_wrap", 16))
        qfile = Path(output_path).with_suffix(".q.txt")
        qfile.write_text(wrapped, encoding="utf-8")
        q_fontsize = caption.get("q_font_size", 46)
        draw = (
            f"drawtext=fontfile='{_escape_path(font_file)}':"
            f"textfile='{_escape_path(qfile)}':"
            f"fontcolor=white:fontsize={q_fontsize}:line_spacing=12:"
            "box=1:boxcolor=black@0.55:boxborderw=28:"
            f"x=(w-text_w)/2:y=({band_top_h}-text_h)/2+{int(h * 0.02)}"
        )
        parts.append(f"[{last}]{draw}[out]")
        last = "out"

    filter_complex = ";".join(parts)
    cmd = [
        "ffmpeg", "-y", "-i", str(input_video),
        "-filter_complex", filter_complex,
        "-map", f"[{last}]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for tmp in (qfile, ass_path):
        if tmp and Path(tmp).exists():
            Path(tmp).unlink()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 失敗：\n{proc.stderr[-1800:]}")
    return str(output_path)
