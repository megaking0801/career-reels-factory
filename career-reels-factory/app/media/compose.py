"""用 FFmpeg 把上傳的 avatar 影片：轉 9:16、燒字幕、疊開場問題字卡。"""
import os
import subprocess
from pathlib import Path

# 候選中文字型 (檔案路徑, libass 家族名)。會挑第一個存在的。
# 不同 macOS 版本內建字型不一，所以自動偵測而非寫死。
_FONT_CANDIDATES = [
    (os.environ.get("CJK_FONT"), os.environ.get("CJK_FONT_NAME", "PingFang TC")),
    ("/System/Library/Fonts/PingFang.ttc", "PingFang TC"),
    ("/System/Library/Fonts/STHeiti Medium.ttc", "Heiti TC"),
    ("/System/Library/Fonts/STHeiti Light.ttc", "Heiti TC"),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", "Hiragino Sans GB"),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti TC"),
]


def _resolve_font():
    for path, name in _FONT_CANDIDATES:
        if path and os.path.exists(path):
            return path, name, str(Path(path).parent)
    return None, None, None


def _escape_subs_path(path: str) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "’")
        .replace("%", "\\%")
    )


def compose(input_video, srt_path, output_path, question_text: str = "",
            resolution: str = "1080x1920", caption: dict | None = None) -> str:
    w, h = resolution.split("x")
    caption = caption or {}
    font_file, font_name, fonts_dir = _resolve_font()

    style_parts = [
        f"FontSize={caption.get('font_size', 18)}",
        f"PrimaryColour={caption.get('primary_color', '&H00FFFFFF')}",
        f"OutlineColour={caption.get('outline_color', '&H00000000')}",
        "BorderStyle=1", "Outline=2", "Shadow=0",
        f"MarginV={caption.get('margin_v', 150)}", "Alignment=2",
    ]
    if font_name:
        style_parts.insert(0, f"FontName={font_name}")
    style = ",".join(style_parts)

    subs = f"subtitles='{_escape_subs_path(srt_path)}'"
    if fonts_dir:
        subs += f":fontsdir='{_escape_subs_path(fonts_dir)}'"
    subs += f":force_style='{style}'"

    filters = [
        f"scale={w}:{h}:force_original_aspect_ratio=decrease",
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
        "setsar=1",
        subs,
    ]

    # 開場問題字卡：需要實體字型檔，找不到就略過(字幕仍正常)
    if question_text and font_file:
        qt = _escape_drawtext(question_text)
        filters.append(
            f"drawtext=fontfile='{font_file}':text='{qt}':fontcolor=white:fontsize=52:"
            "box=1:boxcolor=black@0.6:boxborderw=24:x=(w-text_w)/2:y=h*0.16:"
            "line_spacing=14:enable='lt(t,3)'"
        )

    vf = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", str(input_video),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 失敗：\n{proc.stderr[-1500:]}")
    return str(output_path)
