from __future__ import annotations

import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import ipaddress
import socket
import mimetypes
import random
import zipfile
import html as html_lib
from urllib.parse import urlparse, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError
from functools import lru_cache
import webbrowser
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional
from html.parser import HTMLParser

# All app data stays beside the application (portable folder layout).
APP_DIR = Path(__file__).resolve().parent
MODELS_DIR = APP_DIR / "models"
WHISPER_DIR = MODELS_DIR / "whisper"
HF_CACHE_DIR = MODELS_DIR / "huggingface_cache"
ASSETS_DIR = APP_DIR / "assets"
OUTPUT_DIR = APP_DIR / "output"
DATA_DIR = APP_DIR / "data"
FONTS_DIR = APP_DIR / "fonts"
for folder in (MODELS_DIR, WHISPER_DIR, HF_CACHE_DIR, ASSETS_DIR, OUTPUT_DIR, DATA_DIR, FONTS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(HF_CACHE_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(HF_CACHE_DIR / "hub")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageTk
import imageio_ffmpeg
from jsonschema import Draft202012Validator, FormatChecker

APP_TITLE = "Educational Audio Video Studio 1.19 – Batch Video + Audio Mux"
SCHEMA_PATH = APP_DIR / "storyboard.schema.json"
PROMPT_PATH = APP_DIR / "PROMPT_TEMPLATE_VI.md"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpeg", ".mpg"}
IMAGE_MIME_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/bmp": ".bmp"}
VIDEO_MIME_EXT = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov", "video/x-matroska": ".mkv", "video/x-msvideo": ".avi", "video/mpeg": ".mpeg"}
MAX_ASSET_BYTES = 500 * 1024 * 1024

# Curated composition systems. These are layout grammars, not random coordinate generators.
VISUAL_COMPOSITION_PRESETS = {
    "Auto theo nội dung": {
        "description": "AI tự chọn bố cục phù hợp nhất với ý nghĩa từng scene và thay đổi có chủ đích.",
        "guide": "Chọn bố cục theo chức năng sư phạm của từng cảnh; không lặp cùng một bố cục liên tiếp. Ưu tiên đọc hiểu nhanh, hình ảnh đúng nghĩa và vùng trống rõ ràng."
    },
    "Comic panels – truyện tranh": {
        "description": "Chia cảnh thành 2–4 panel như truyện tranh, mỗi panel có một hành động hoặc ví dụ.",
        "guide": "Dùng bố cục COMIC PANELS: chia phần visual thành 2–4 panel có khoảng cách rõ; mỗi panel chỉ có một nhân vật/hành động hoặc một ví dụ. Dùng person + speech_bubble + vật thể phù hợp khi cần hội thoại. Đánh số/trình tự bằng vị trí panel, không nhồi nhiều câu vào một panel."
    },
    "Character scene – nhân vật tương tác": {
        "description": "Một nhân vật chính tương tác với đồ vật/đối tượng đang được giải thích.",
        "guide": "Dùng bố cục CHARACTER SCENE: một person làm nhân vật chính, tương tác trực tiếp với 1–3 vật thể có ý nghĩa (monitor, phone, book, cup, bird, clock...). Hướng nhìn/hướng connector phải thể hiện quan hệ. Không đặt chữ lên người hoặc vật thể; lời thoại nằm trong speech_bubble riêng."
    },
    "Grammar board – bảng công thức": {
        "description": "Công thức lớn ở trung tâm, các thành phần và ví dụ nằm trong thẻ độc lập.",
        "guide": "Dùng bố cục GRAMMAR BOARD: một formula card nổi bật ở phần trên/giữa; các thành phần tách thành chip/card nhỏ; ví dụ đặt trong 1–2 thẻ ở lane phía dưới. Connector chỉ nối các thành phần thực sự liên quan. Mỗi card có lề trong rộng, không để chữ chạm viền."
    },
    "Before / After – so sánh": {
        "description": "Hai vùng song song để so sánh câu cơ bản/nâng cấp, đúng/sai hoặc trước/sau.",
        "guide": "Dùng bố cục BEFORE / AFTER: hai panel song song có tiêu đề ngắn và minh họa riêng; dùng checkmark/x_mark khi có đúng-sai thực sự. Nếu chỉ so sánh mức độ tự nhiên, không đánh dấu câu cơ bản là sai. Mỗi panel chỉ 1 hình chính và tối đa 2 dòng chữ."
    },
    "Mind map – sơ đồ nhánh": {
        "description": "Khái niệm trung tâm nối tới 2–4 nhánh ví dụ/nhóm ý.",
        "guide": "Dùng bố cục MIND MAP: khái niệm trung tâm trong một card/hình lớn vừa phải; 2–4 nhánh tỏa ra các thẻ nhỏ có icon semantic. Connector đi phía sau node, không xuyên qua chữ/hình. Không dùng mind map nếu quan hệ không phải dạng phân nhánh."
    },
    "Vocabulary cards – thẻ từ vựng": {
        "description": "Lưới 2x2 hoặc 1x3, mỗi thẻ ghép một hình cụ thể với từ/cụm từ.",
        "guide": "Dùng bố cục VOCABULARY CARDS: lưới 2x2 hoặc hàng 1x3; mỗi thẻ gồm một pictogram rõ ràng và một từ/cụm từ ngắn trong footer riêng. Các thẻ có cùng kích thước, cùng lề, không để label đè lên pictogram. Chỉ dùng khi có nhiều ví dụ song song."
    },
    "Timeline journey – hành trình": {
        "description": "Các mốc thời gian/hành động nối theo trình tự từ trái sang phải hoặc trên xuống dưới.",
        "guide": "Dùng bố cục TIMELINE JOURNEY: 2–4 mốc đặt theo thứ tự; dùng calendar/clock/person/object để diễn giải từng mốc. Đường timeline nối giữa các mốc nhưng nằm phía sau, không chạy qua nội dung. Mỗi mốc có một nhãn ngắn."
    },
    "Central hero + callouts – hình chính": {
        "description": "Một hình minh họa chính lớn ở một bên/giữa, kèm 2–3 chú thích ở lane riêng.",
        "guide": "Dùng bố cục CENTRAL HERO + CALLOUTS: chọn một hình chính lớn nhưng không tràn khung; đặt 2–3 callout ngắn ở các vùng trống xung quanh bằng đường chỉ dẫn ngắn. Callout không che chủ thể và connector kết thúc ở mép đối tượng."
    },
    "Editorial infographic – infographic tạp chí": {
        "description": "Tiêu đề rõ, hình/nhân vật chủ đạo, các khối thông tin phân cấp như một trang tạp chí học tập.",
        "guide": "Dùng bố cục EDITORIAL INFOGRAPHIC: tiêu đề ngắn; một hình/nhân vật chủ đạo; 2–3 khối thông tin tách biệt bằng nền/card và khoảng trắng. Dùng thứ bậc chữ display/headline/body/label nhất quán. Không biến toàn bộ cảnh thành một tấm poster chữ dày đặc."
    }
}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
KARAOKE_SFX_PRESETS = {
    "Ambient mềm (mặc định)": "sfx_ambient_soft.wav",
    "Cinematic airy": "sfx_cinematic_air.wav",
    "Tech minimal": "sfx_tech_minimal.wav",
    "Tắt SFX": None,
    "File riêng": None,
}


def ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    return subprocess.run([ffmpeg_path(), "-hide_banner", "-loglevel", "error", *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def probe_duration(path: Path) -> float:
    p = subprocess.run([ffmpeg_path(), "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, check=False)
    text = p.stderr or ""
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not m:
        raise RuntimeError("Không đọc được thời lượng audio. Hãy kiểm tra file có mở được không.")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


SUBTITLE_EXTS = {
    ".srt", ".vtt", ".ass", ".ssa", ".sbv", ".lrc", ".sub",
    ".smi", ".sami", ".ttml", ".dfxp", ".xml", ".scc"
}


def _decode_text_file(path: Path) -> str:
    """Read subtitle/text files with common Unicode and Japanese Windows encodings."""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp932", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _time_to_srt(value: str) -> Optional[str]:
    """Convert HH:MM:SS.mmm or MM:SS.mmm to SRT timestamp format."""
    value = value.strip().split()[0].replace(",", ".")
    m = re.fullmatch(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.(\d{1,6}))?", value)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    fraction = (m.group(4) or "0")
    millis = int((fraction + "000")[:3])
    total_seconds = hours * 3600 + minutes * 60 + seconds
    hh, rem = divmod(total_seconds, 3600)
    mm, ss = divmod(rem, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{millis:03d}"


def _clean_subtitle_text(value: str) -> str:
    """Remove presentation-only subtitle markup while retaining spoken wording."""
    import html
    value = re.sub(r"\{\\[^}]*\}", "", value)  # ASS override tags
    value = re.sub(r"</?(?:i|b|u|s|font|c|v|lang)(?:\s+[^>]*)?>", "", value, flags=re.I)
    value = re.sub(r"<\d{2}:\d{2}:\d{2}[.,]\d{3}>", "", value)  # WebVTT karaoke tags
    value = value.replace(r"\N", "\n").replace(r"\n", "\n").replace(r"\h", " ")
    return html.unescape(value).strip()


def _format_subtitle_cues(cues: list[tuple[str, str, str]]) -> str:
    blocks = []
    for index, (start, end, text) in enumerate(cues, 1):
        cleaned = _clean_subtitle_text(text)
        if cleaned:
            blocks.append(f"{index}\n{start} --> {end}\n{cleaned}")
    return "\n\n".join(blocks)


def _parse_srt_vtt(raw: str) -> str:
    cues: list[tuple[str, str, str]] = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n").strip()):
        lines = [line for line in block.split("\n") if line.strip()]
        time_index = next((i for i, line in enumerate(lines)
                           if "-->" in line and re.search(r"\d{1,2}:\d{2}(?::\d{2})?[.,.]\d+", line)), None)
        if time_index is None:
            continue
        left, right = lines[time_index].split("-->", 1)
        start = _time_to_srt(left)
        end_match = re.match(r"\s*([^\s]+)", right)
        end = _time_to_srt(end_match.group(1)) if end_match else None
        text = "\n".join(lines[time_index + 1:])
        if start and end and text.strip():
            cues.append((start, end, text))
    return _format_subtitle_cues(cues)


def _parse_sbv(raw: str) -> str:
    cues: list[tuple[str, str, str]] = []
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n").strip())
    for block in blocks:
        lines = block.split("\n")
        if not lines:
            continue
        m = re.match(r"\s*([^,]+),\s*([^\s]+)\s*$", lines[0])
        if not m:
            continue
        start, end = _time_to_srt(m.group(1)), _time_to_srt(m.group(2))
        text = "\n".join(lines[1:])
        if start and end and text.strip():
            cues.append((start, end, text))
    return _format_subtitle_cues(cues)


def _parse_ass_ssa(raw: str) -> str:
    cues: list[tuple[str, str, str]] = []
    fields: list[str] = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith("format:"):
            fields = [part.strip().lower() for part in stripped.split(":", 1)[1].split(",")]
        elif stripped.lower().startswith("dialogue:"):
            payload = stripped.split(":", 1)[1].lstrip()
            names = fields or ["layer", "start", "end", "style", "name", "marginl", "marginr", "marginv", "effect", "text"]
            try:
                parts = payload.split(",", max(0, len(names) - 1))
                row = dict(zip(names, parts))
                start, end = _time_to_srt(row.get("start", "")), _time_to_srt(row.get("end", ""))
                text = row.get("text", "")
                if start and end and text.strip():
                    cues.append((start, end, text))
            except Exception:
                continue
    return _format_subtitle_cues(cues)


def read_transcript_file(path: Path) -> str:
    """Load plain text or convert common subtitle formats into timestamped transcript text."""
    raw = _decode_text_file(path)
    ext = path.suffix.lower()
    if ext in {".srt", ".vtt"}:
        parsed = _parse_srt_vtt(raw)
        return parsed or raw.strip()
    if ext == ".sbv":
        parsed = _parse_sbv(raw)
        return parsed or raw.strip()
    if ext in {".ass", ".ssa"}:
        parsed = _parse_ass_ssa(raw)
        return parsed or raw.strip()
    # LRC, MicroDVD SUB, SAMI, TTML and SCC are kept in their native timestamped
    # representation rather than guessing missing end times or frame rates.
    return raw.strip()


KARAOKE_EFFECTS = {
    "Classic Karaoke – tô màu từng từ": {
        "description": "Chữ trắng, từ đang đọc chuyển tím theo tiến độ; viền tối để rõ trên nền sáng hoặc tối.",
        "mode": "karaoke", "active": "#A78BFA", "inactive": "#FFFFFF", "outline": "#172033",
        "border": 2.4, "shadow": 1.2, "blur": 0.0, "bold": -1, "box": False, "pop": False
    },
    "Neon Glow – phát sáng": {
        "description": "Từ đang đọc chuyển xanh cyan, có viền và glow nhẹ; hợp video gaming/tech.",
        "mode": "karaoke", "active": "#67E8F9", "inactive": "#F8FAFC", "outline": "#155E75",
        "border": 3.2, "shadow": 0.5, "blur": 1.1, "bold": -1, "box": False, "pop": False
    },
    "Pop Bounce – bật nảy": {
        "description": "Cả dòng có nhịp pop ngắn khi xuất hiện; từ đang đọc chuyển vàng cam, chữ đậm và viền rõ.",
        "mode": "karaoke", "active": "#FBBF24", "inactive": "#FFFFFF", "outline": "#292014",
        "border": 3.0, "shadow": 1.0, "blur": 0.0, "bold": -1, "box": False, "pop": True
    },
    "Soft Caption Card – thẻ nền mờ": {
        "description": "Phụ đề nằm trên thẻ nền xanh đen bán trong suốt, bo kiểu caption cổ điển; từ đang đọc chuyển tím.",
        "mode": "karaoke", "active": "#C4B5FD", "inactive": "#FFFFFF", "outline": "#263449",
        "border": 10.0, "shadow": 0.0, "blur": 0.0, "bold": 0, "box": True, "pop": False
    },
    "Minimal Outline – tối giản": {
        "description": "Không có thẻ nền; chữ trắng viền đen mảnh, từ đang đọc chuyển xanh lá nhẹ.",
        "mode": "karaoke", "active": "#86EFAC", "inactive": "#FFFFFF", "outline": "#000000",
        "border": 1.5, "shadow": 0.8, "blur": 0.0, "bold": 0, "box": False, "pop": False
    },
    "Typewriter – hiện lần lượt": {
        "description": "Câu xuất hiện dần theo từng từ; từ mới xuất hiện được tô màu nhấn. Hữu ích cho video học từ vựng.",
        "mode": "typewriter", "active": "#FBBF24", "inactive": "#FFFFFF", "outline": "#172033",
        "border": 2.2, "shadow": 1.0, "blur": 0.0, "bold": -1, "box": False, "pop": False
    },
}


def _subtitle_time_seconds(value: str) -> Optional[float]:
    value = value.strip().replace(',', '.')
    m = re.fullmatch(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.(\d{1,6}))?", value)
    if not m:
        return None
    hh = int(m.group(1) or 0)
    mm = int(m.group(2))
    ss = int(m.group(3))
    frac = float("0." + (m.group(4) or "0"))
    return hh * 3600 + mm * 60 + ss + frac


def _normalized_srt_to_cues(text: str) -> list[tuple[float, float, str]]:
    cues: list[tuple[float, float, str]] = []
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [x for x in block.split("\n") if x.strip()]
        ti = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if ti is None:
            continue
        left, right = lines[ti].split("-->", 1)
        start = _subtitle_time_seconds(left.strip())
        rm = re.match(r"\s*([^\s]+)", right)
        end = _subtitle_time_seconds(rm.group(1)) if rm else None
        body = _clean_subtitle_text(" ".join(lines[ti + 1:]))
        if start is not None and end is not None and end > start and body:
            cues.append((start, end, body))
    cues.sort(key=lambda x: (x[0], x[1]))
    return cues


def _parse_lrc_cues(raw: str) -> list[tuple[float, float, str]]:
    rows: list[tuple[float, str]] = []
    for line in raw.replace("\r", "").split("\n"):
        tags = list(re.finditer(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]", line))
        if not tags:
            continue
        body = re.sub(r"(?:\[\d{1,2}:\d{2}(?:\.\d{1,3})?\])+", "", line).strip()
        for tag in tags:
            mm, ss = int(tag.group(1)), int(tag.group(2))
            frac = float("0." + (tag.group(3) or "0"))
            rows.append((mm * 60 + ss + frac, body))
    rows.sort(key=lambda x: x[0])
    cues = []
    for i, (start, text) in enumerate(rows):
        end = rows[i + 1][0] if i + 1 < len(rows) else start + 3.0
        if text and end > start:
            cues.append((start, end, text))
    return cues


def load_karaoke_cues(path: Path) -> list[tuple[float, float, str]]:
    """Load timestamped SRT/VTT/ASS/SSA/SBV/LRC subtitle cues."""
    raw = _decode_text_file(path)
    ext = path.suffix.lower()
    if ext in {".srt", ".vtt"}:
        normalized = _parse_srt_vtt(raw)
    elif ext == ".sbv":
        normalized = _parse_sbv(raw)
    elif ext in {".ass", ".ssa"}:
        normalized = _parse_ass_ssa(raw)
    elif ext == ".lrc":
        cues = _parse_lrc_cues(raw)
        if cues:
            return cues
        normalized = ""
    else:
        normalized = ""
    cues = _normalized_srt_to_cues(normalized) if normalized else []
    if not cues:
        raise ValueError("Không tìm thấy cue có timestamp hợp lệ. Hãy dùng SRT, VTT, ASS, SSA, SBV hoặc LRC.")
    return cues


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    total_cs = int(round(seconds * 100))
    hh, rem = divmod(total_cs, 360000)
    mm, rem = divmod(rem, 6000)
    ss, cs = divmod(rem, 100)
    return f"{hh}:{mm:02d}:{ss:02d}.{cs:02d}"


def _ass_color(hex_color: str, alpha: int = 0) -> str:
    value = hex_color.lstrip("#")
    rr, gg, bb = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return f"&H{alpha:02X}{bb:02X}{gg:02X}{rr:02X}"


def _ass_safe_text(text: str) -> str:
    # ASS uses braces for override tags; escape user text so cue text cannot inject formatting.
    text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return text.replace("\n", " ").replace("\r", " ")


def build_karaoke_ass(cues: list[tuple[float, float, str]], width: int, height: int,
                      effect_name: str, position: str, size_name: str,
                      time_offset: float = 0.0) -> str:
    effect = KARAOKE_EFFECTS[effect_name]
    size_factor = {"Nhỏ": 0.035, "Vừa": 0.045, "Lớn": 0.056}.get(size_name, 0.045)
    font_size = max(24, min(92, int(height * size_factor)))
    align = {"Dưới": 2, "Giữa": 5, "Trên": 8}.get(position, 2)
    margin_v = max(32, int(height * (0.055 if position != "Giữa" else 0.0)))
    active = _ass_color(effect["active"])
    inactive = _ass_color(effect["inactive"])
    outline = _ass_color(effect["outline"])
    back = _ass_color("#101827", 78)
    border_style = 3 if effect["box"] else 1
    outline_width = effect["border"]
    shadow = effect["shadow"]
    bold = effect["bold"]

    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Karaoke,Segoe UI,{font_size},{active},{inactive},{outline},{back},{bold},0,0,0,100,100,0,0,{border_style},{outline_width:.1f},{shadow:.1f},{align},{int(width*.055)},{int(width*.055)},{margin_v},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for cue_start, cue_end, text in cues:
        start = max(0.0, cue_start + time_offset)
        end = max(start + 0.04, cue_end + time_offset)
        if end <= 0:
            continue
        start = max(0.0, start)
        end = max(start + 0.04, end)
        pieces = _split_mixed_caption_text(text.replace("\n", " "))
        if not pieces:
            continue
        weights = [max(1, len(token)) for token, _ in pieces]
        duration_cs = max(len(pieces), int(round((end - start) * 100)))
        weight_sum = sum(weights)
        allocated = []
        remaining = duration_cs
        for idx, weight in enumerate(weights):
            if idx == len(weights) - 1:
                centis = max(1, remaining)
            else:
                centis = max(1, int(round(duration_cs * weight / weight_sum)))
                centis = min(centis, max(1, remaining - (len(weights) - idx - 1)))
            allocated.append(centis)
            remaining -= centis
        if effect["mode"] == "typewriter":
            token_cursor = start
            prefix: list[tuple[str, bool]] = []
            for idx, ((token, has_space), centis) in enumerate(zip(pieces, allocated)):
                token_start = token_cursor
                token_cursor += (centis / 100.0)
                prefix.append((token, has_space))
                event_end = end if idx == len(pieces) - 1 else min(end, token_cursor + 0.001)
                visible = []
                for j, (part, space_before) in enumerate(prefix):
                    if space_before and visible:
                        visible.append(" ")
                    if j == len(prefix) - 1:
                        visible.append("{" + f"\\1c{active}" + "}" + _ass_safe_text(part) + "{\\1c" + inactive + "}")
                    else:
                        visible.append(_ass_safe_text(part))
                ass_text = "{\\an" + str(align) + "\\q2\\fad(60,70)}" + "".join(visible)
                if effect["pop"] and idx == 0:
                    ass_text = "{\\an" + str(align) + "\\q2\\fad(60,70)\\t(0,120,\\fscx112\\fscy112)\\t(120,240,\\fscx100\\fscy100)}" + "".join(visible)
                lines.append(f"Dialogue: 0,{_ass_time(token_start)},{_ass_time(event_end)},Karaoke,,0,0,0,,{ass_text}")
        else:
            chunks = []
            for (token, has_space), centis in zip(pieces, allocated):
                if has_space and chunks:
                    chunks.append(" ")
                chunks.append(f"{{\\kf{centis}}}{_ass_safe_text(token)}")
            override = "{\\an" + str(align) + "\\q2"
            if effect["blur"]:
                override += f"\\blur{effect['blur']:.1f}"
            if effect["pop"]:
                override += "\\t(0,120,\\fscx112\\fscy112)\\t(120,240,\\fscx100\\fscy100)"
            override += "}"
            ass_text = override + "".join(chunks)
            lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Karaoke,,0,0,0,,{ass_text}")
    return "\n".join(lines) + "\n"


def probe_video_size(path: Path) -> tuple[int, int]:
    p = subprocess.run([ffmpeg_path(), "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, check=False)
    match = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})(?:[,\s])", p.stderr or "", re.S)
    if not match:
        raise RuntimeError("Không đọc được độ phân giải video đầu vào.")
    return int(match.group(1)), int(match.group(2))


def _run_karaoke_ffmpeg(video: Path, output: Path, ass_path: Path, cancel: threading.Event,
                        progress, log, *, video_effect: str = "Fade cinematic",
                        outro_seconds: float = 3.0, outro_text: str = "Thanks for watching!",
                        mute_original: bool = False, original_volume: float = 1.0,
                        remove_dialogue: bool = False, music_path: Optional[Path] = None,
                        sfx_path: Optional[Path] = None, music_volume: float = 0.18,
                        sfx_volume: float = 0.10, voice_path: Optional[Path] = None,
                        voice_volume: float = 1.0, voice_start: float = 0.0,
                        voice_priority: bool = True) -> None:
    """Render karaoke with a prioritized voiceover and ducked background layers."""
    output.parent.mkdir(parents=True, exist_ok=True)
    progress_path = output.parent / (".evs_progress_" + str(os.getpid()) + ".txt")
    duration = probe_duration(video)
    width, height = probe_video_size(video)
    outro_seconds = max(0.0, min(float(outro_seconds), max(0.0, duration - 0.25)))
    fade_out_start = max(0.0, duration - outro_seconds) if outro_seconds else max(0.0, duration - 0.35)
    vfilters = []
    # These are whole-video visual treatments. A true scene-to-scene transition
    # needs edit points; this tab intentionally does not invent cut locations.
    if video_effect == "Fade cinematic":
        vfilters += ["fade=t=in:st=0:d=0.65", f"fade=t=out:st={fade_out_start:.3f}:d={max(.25, duration-fade_out_start):.3f}"]
    elif video_effect == "Soft vignette + fade":
        vfilters += ["vignette=PI/5", "eq=contrast=1.04:saturation=0.92", "fade=t=in:st=0:d=0.7", f"fade=t=out:st={fade_out_start:.3f}:d={max(.25, duration-fade_out_start):.3f}"]
    elif video_effect == "Warm film + fade":
        vfilters += ["eq=contrast=1.06:saturation=1.12:brightness=0.015", "colorbalance=rs=0.035:gs=0.012:bs=-0.025", "vignette=PI/6", "fade=t=in:st=0:d=0.7", f"fade=t=out:st={fade_out_start:.3f}:d={max(.25, duration-fade_out_start):.3f}"]
    elif video_effect == "Cool tech + fade":
        vfilters += ["eq=contrast=1.05:saturation=1.08", "colorbalance=rs=-0.025:gs=0.005:bs=0.035", "fade=t=in:st=0:d=0.7", f"fade=t=out:st={fade_out_start:.3f}:d={max(.25, duration-fade_out_start):.3f}"]
    elif video_effect == "Slow zoom + fade":
        fps_match = re.search(r"fps[:= ]+(\d+(?:\.\d+)?)", "")
        # zoompan preserves the input canvas and adds a restrained continuous push-in.
        vfilters += ["fps=30", f"zoompan=z='min(zoom+0.00012,1.045)':d=1:s={width}x{height}:fps=30", "fade=t=in:st=0:d=0.7", f"fade=t=out:st={fade_out_start:.3f}:d={max(.25, duration-fade_out_start):.3f}"]
    # Keep subtitle overlay after zoom/color filters so captions remain crisp and stable.
    vfilters.append(f"subtitles=filename={ass_path.name}")
    vf = ",".join(vfilters)

    cmd = [ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    input_index = 1
    music_idx = sfx_idx = voice_idx = None
    if music_path:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        music_idx = input_index; input_index += 1
    if sfx_path:
        cmd += ["-stream_loop", "-1", "-i", str(sfx_path)]
        sfx_idx = input_index; input_index += 1
    if voice_path:
        cmd += ["-i", str(voice_path)]
        voice_idx = input_index; input_index += 1

    filters = [f"[0:v:0]{vf}[vout]"]
    bed_labels = []
    probe_audio = subprocess.run([ffmpeg_path(), "-hide_banner", "-i", str(video)], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, check=False)
    has_original_audio = "Audio:" in (probe_audio.stderr or "")
    if not mute_original and has_original_audio:
        if remove_dialogue:
            audio_line = next((line for line in (probe_audio.stderr or "").splitlines() if "Audio:" in line), "")
            if "mono" in audio_line.lower() or ("stereo" not in audio_line.lower() and "2 channels" not in audio_line.lower()):
                raise RuntimeError("Giảm lời thoại thử nghiệm yêu cầu audio stereo. Video này không được nhận diện là stereo; hãy tắt tùy chọn này hoặc chọn Xóa audio gốc.")
            filters.append("[0:a:0]aformat=channel_layouts=stereo,pan=stereo|c0=FL-FR|c1=FR-FL,volume=" + f"{original_volume:.3f}[orig]")
        else:
            filters.append(f"[0:a:0]aformat=channel_layouts=stereo,volume={original_volume:.3f}[orig]")
        bed_labels.append("[orig]")
    if music_idx is not None:
        filters.append(f"[{music_idx}:a:0]aformat=channel_layouts=stereo,volume={music_volume:.3f},atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.2,afade=t=out:st={max(0,duration-1.5):.3f}:d={min(1.5,duration):.3f}[music]")
        bed_labels.append("[music]")
    if sfx_idx is not None:
        filters.append(f"[{sfx_idx}:a:0]aformat=channel_layouts=stereo,volume={sfx_volume:.3f},atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.8,afade=t=out:st={max(0,duration-2.0):.3f}:d={min(2.0,duration):.3f}[sfx]")
        bed_labels.append("[sfx]")

    if voice_idx is not None:
        delay_ms = max(0, int(round(float(voice_start) * 1000)))
        filters.append(f"[{voice_idx}:a:0]aformat=sample_rates=48000:channel_layouts=stereo,volume={max(0.0,min(2.0,float(voice_volume))):.3f},adelay={delay_ms}:all=1,apad,atrim=0:{duration:.3f},asetpts=PTS-STARTPTS[voice]")

    if bed_labels and voice_idx is not None:
        if len(bed_labels) == 1:
            filters.append(f"{bed_labels[0]}anull[bed]")
        else:
            filters.append("".join(bed_labels) + f"amix=inputs={len(bed_labels)}:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.95[bed]")
    if voice_idx is not None:
        if bed_labels:
            if voice_priority:
                # Split narration: one copy controls ducking, the other stays foreground.
                filters.append("[voice]asplit=2[voice_key][voice_mix]")
                filters.append("[bed][voice_key]sidechaincompress=threshold=0.025:ratio=10:attack=15:release=420:makeup=1[bedduck]")
                filters.append("[bedduck][voice_mix]amix=inputs=2:duration=longest:dropout_transition=0:weights='0.55 1.0':normalize=0,alimiter=limit=0.95[aout]")
            else:
                filters.append("[bed][voice]amix=inputs=2:duration=longest:dropout_transition=0:weights='0.8 1.0':normalize=0,alimiter=limit=0.95[aout]")
        else:
            filters.append("[voice]alimiter=limit=0.95[aout]")
    elif bed_labels:
        if len(bed_labels) == 1:
            filters.append(f"{bed_labels[0]}alimiter=limit=0.95[aout]")
        else:
            filters.append("".join(bed_labels) + f"amix=inputs={len(bed_labels)}:duration=longest:dropout_transition=2,alimiter=limit=0.95[aout]")

    audio_present = bool(bed_labels or voice_idx is not None)
    filter_complex = ";".join(filters)
    cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
    if audio_present:
        cmd += ["-map", "[aout]"]
    cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    if audio_present:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    cmd += ["-movflags", "+faststart", "-progress", str(progress_path), "-nostats", str(output)]
    log(f"Render karaoke + video effect '{video_effect}', outro {outro_seconds:.1f}s; audio layers={len(bed_labels) + (1 if voice_idx is not None else 0)}.")
    if remove_dialogue:
        log("Lưu ý: center-cancel chỉ là giảm giọng thử nghiệm trên stereo; có thể làm mất nhạc/âm thanh nằm giữa.")
    proc = subprocess.Popen(cmd, cwd=str(output.parent), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    last_percent = -1
    try:
        while proc.poll() is None:
            if cancel.is_set():
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill()
                raise InterruptedError("Đã hủy xuất video karaoke/effects.")
            try:
                info = progress_path.read_text(encoding="utf-8", errors="ignore")
                matches = re.findall(r"out_time_ms=(\d+)", info)
                if matches:
                    elapsed = int(matches[-1]) / 1_000_000
                    pct = min(96, max(3, int(3 + 93 * elapsed / max(0.1, duration))))
                    if pct != last_percent:
                        progress(pct, f"Đang render video/audio: {pct}%")
                        last_percent = pct
            except Exception:
                pass
            time.sleep(0.35)
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        if proc.returncode != 0 or not output.exists() or output.stat().st_size < 1024:
            output.unlink(missing_ok=True)
            raise RuntimeError("FFmpeg không thể render video/effects:\n" + stderr[-3000:])
    finally:
        progress_path.unlink(missing_ok=True)
    progress(100, "Hoàn tất video karaoke + video/audio effects.")


def _safe_output_stem(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" ._")
    return value or "educational_video"


def fmt_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    s = max(0.0, float(seconds))
    return f"{int(s//60):02d}:{s%60:05.2f}"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    return "".join(ch for ch in value if ch.isalnum() or ord(ch) >= 0x3040)


def is_cjk(text: str) -> bool:
    return any((0x3040 <= ord(c) <= 0x30FF) or (0x3400 <= ord(c) <= 0x9FFF) or
               (0xF900 <= ord(c) <= 0xFAFF) or (0xAC00 <= ord(c) <= 0xD7AF) for c in text)


def font_candidates(text: str, bold: bool = False) -> list[Path]:
    dirs = [FONTS_DIR]
    if os.name == "nt":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        dirs += [windir / "Fonts", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
        if is_cjk(text):
            names = ["meiryob.ttc", "YuGothB.ttc", "msgothic.ttc", "NotoSansJP-Bold.ttf"] if bold else ["meiryo.ttc", "YuGothR.ttc", "msgothic.ttc", "NotoSansJP-Regular.ttf"]
        else:
            names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    else:
        dirs += [Path("/usr/share/fonts/opentype/noto"), Path("/usr/share/fonts/truetype/dejavu")]
        names = ["NotoSansCJK-Bold.ttc", "DejaVuSans-Bold.ttf"] if bold else ["NotoSansCJK-Regular.ttc", "DejaVuSans.ttf"]
    files = []
    for d in dirs:
        for name in names:
            files.append(d / name)
        if d.exists() and is_cjk(text):
            for pat in ("*Noto*JP*", "*Noto*CJK*", "*Meiryo*", "*YuGoth*"):
                files.extend(d.glob(pat))
    if FONTS_DIR.exists():
        files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf")) + list(FONTS_DIR.glob("*.ttc")) + files
    seen, out = set(), []
    for p in files:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


@lru_cache(maxsize=256)
def get_font(text: str, size: int, bold: bool = False):
    for p in font_candidates(text, bold):
        try:
            if p.is_file():
                return ImageFont.truetype(str(p), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def parse_json_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    raw = raw.strip()
    # Accept a fenced JSON response from ChatGPT, then validate the object strictly.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Storyboard phải là một JSON object, không phải array.")
    return obj


def _default_visual_fallback(scene: dict[str, Any], palette: list[str]) -> dict[str, Any]:
    """Create a safe built-in 2.5D visual when upgrading older storyboards."""
    kind = scene.get("scene_type", "other")
    shape = {
        "scenario": "person", "definition": "card", "example": "speech_bubble",
        "process": "staircase", "comparison": "cube", "timeline": "cylinder",
        "diagram": "molecule", "chart": "cuboid", "quiz": "card",
        "summary": "staircase", "title_card": "sphere", "call_to_action": "speech_bubble"
    }.get(kind, "cube")
    # Use a light educational palette for newly migrated scenes; ignore legacy white-on-dark palettes.
    vivid=[]
    for candidate in palette or []:
        try:
            rgb=tuple(int(candidate.lstrip("#")[i:i+2],16) for i in (0,2,4))
            if max(rgb)-min(rgb)>35 and sum(rgb)/3<220:
                vivid.append(candidate)
        except Exception:
            pass
    primary = "#F7F8FC"
    accent = vivid[0] if vivid else "#7C3AED"
    secondary = vivid[1] if len(vivid)>1 else "#3B82F6"
    goal = (scene.get("learning_goal") or scene.get("visual_summary") or "Key concept")[:40]
    return {
        "mode": "3d_illustration",
        "background": {"primary": primary, "secondary": "#0B1422", "accent": accent, "pattern": "soft_glow"},
        "objects": [{
            "object_id": f"{scene.get('scene_id','scene')}_fallback_object",
            "shape": shape,
            "position": {"x": 0.29, "y": 0.22, "width": 0.42, "height": 0.42},
            "color": accent,
            "secondary_color": secondary,
            "label": None,
            "detail": goal,
            "depth": 0.22,
            "variant": "solid",
            "animation": "float"
        }],
        "connectors": [],
        "notes": "Fallback tự sinh khi chuyển từ storyboard cũ; pictogram vector semantic được render tự động từ JSON."
    }


def migrate_storyboard(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade v1.0–v1.2 storyboards to v1.3 with renderable visual fallbacks."""
    version = str(data.get("schema_version", ""))
    if version in ("1.0", "1.1", "1.2"):
        for asset in data.get("assets", []):
            asset.setdefault("download_url", None)
            asset.setdefault("source_page_url", None)
            asset.setdefault("fallback_download_urls", [])
            asset.setdefault("provider", None)
            asset.setdefault("creator", None)
            asset.setdefault("license_name", None)
            asset.setdefault("license_url", None)
            asset.setdefault("attribution", None)
            # Older stock-search assets may not contain the verification fields required by v1.3.
            # Do not carry an unverified URL forward as if it were trusted: keep the visual intent,
            # disable that download, and let the new JSON-defined collision-aware vector fallback render instead.
            verification = asset.get("web_verification") or {}
            verified = all(verification.get(flag) is True for flag in (
                "source_page_opened", "direct_file_opened", "visual_match_confirmed", "license_checked"
            )) and bool(asset.get("download_url")) and bool(asset.get("source_page_url")) and bool(asset.get("license_name")) and bool(asset.get("license_url"))
            if asset.get("source") == "stock_search" and not verified:
                asset["source"] = "to_be_created"
                asset["download_url"] = None
                asset["source_page_url"] = None
                asset["fallback_download_urls"] = []
                asset["provider"] = None
                asset["creator"] = None
                asset["license_name"] = None
                asset["license_url"] = None
                asset["attribution"] = None
                asset.pop("web_verification", None)
        palette = data.get("project", {}).get("visual_style", {}).get("palette", ["#14263D", "#38BDF8", "#22C55E"])
        for scene in data.get("scenes", []):
            scene.setdefault("asset_ids", [])
            if not scene.get("visual_fallback"):
                scene["visual_fallback"] = _default_visual_fallback(scene, palette)
            for el in scene.get("elements", []):
                st = el.setdefault("style", {})
                st.setdefault("text_effect", "card")
                st.setdefault("background_color", None)
                st.setdefault("font_scale", 1.0)
        data["schema_version"] = "1.3"
    return data


def validate_public_http_url(url: str) -> None:
    """Reject non-HTTP and private/local destinations before downloading media."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("URL media phải bắt đầu bằng http:// hoặc https://")
    host = parts.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        raise ValueError("Không cho phép URL trỏ tới máy nội bộ.")
    if host == "images.openai.com" or host.endswith(".bing.net") or host.endswith(".gstatic.com"):
        raise ValueError("Không dùng proxy/thumbnail tìm kiếm. Hãy lấy direct media URL từ trang nguồn gốc và giấy phép của tài nguyên.")
    try:
        records = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
        addresses = {r[4][0].split("%", 1)[0] for r in records}
        if not addresses:
            raise ValueError("Không phân giải được tên miền của URL media.")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or
                    ip.is_reserved or ip.is_unspecified):
                raise ValueError("URL media trỏ tới địa chỉ IP nội bộ/không công khai.")
    except socket.gaierror as exc:
        raise ValueError(f"Không phân giải được host {host}: {exc}") from exc


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _media_extension(url: str, content_type: str, asset_type: str) -> str:
    path_ext = Path(unquote(urlparse(url).path)).suffix.lower()
    allowed = VIDEO_EXTS if asset_type == "video" else IMAGE_EXTS
    if path_ext in allowed:
        return path_ext
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    ext = VIDEO_MIME_EXT.get(ctype) if asset_type == "video" else IMAGE_MIME_EXT.get(ctype)
    if ext:
        return ext
    guessed = mimetypes.guess_extension(ctype) if ctype else None
    if guessed and guessed.lower() in allowed:
        return guessed.lower()
    raise ValueError(f"URL không trả về định dạng {'video' if asset_type == 'video' else 'ảnh'} hợp lệ (Content-Type: {ctype or 'không rõ'}). Có thể AI đã đưa link trang web thay vì link file trực tiếp.")


def verify_downloaded_media(path: Path, asset_type: str) -> tuple[int, int]:
    """Fully decode downloaded media; a filename or HTTP Content-Type is not enough."""
    if asset_type == "video":
        try:
            import cv2
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise ValueError("OpenCV không mở được video.")
            ok, frame = cap.read()
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            cap.release()
            if not ok or frame is None or width < 64 or height < 64:
                raise ValueError("Video không giải mã được frame đầu hoặc độ phân giải quá nhỏ.")
            return width, height
        except ImportError:
            cmd = [ffmpeg_path(), "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90, check=False)
            if proc.returncode != 0:
                raise ValueError("FFmpeg không giải mã được video: " + proc.stderr.decode("utf-8", "ignore")[-500:])
            return 0, 0
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            width, height = im.size
            if width < 96 or height < 96:
                raise ValueError(f"Ảnh quá nhỏ ({width}x{height}); cần ảnh đủ độ phân giải để minh họa.")
            im.load()
            return width, height
    except Exception as exc:
        raise ValueError(f"File không phải ảnh hợp lệ hoặc không giải mã được: {exc}") from exc


def download_media_asset(asset: dict[str, Any], dest_dir: Path, cancel: threading.Event,
                         log=lambda _m: None,
                         progress=lambda _received, _total, _attempt, _attempts: None) -> Path:
    """Download a direct image/video URL with byte-level progress, then decode the media."""
    asset_id = str(asset.get("asset_id", "asset"))
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", asset_id).strip("._") or "asset"
    urls = []
    if asset.get("download_url"):
        urls.append(asset["download_url"])
    urls.extend(u for u in asset.get("fallback_download_urls", []) if u)
    if not urls:
        raise ValueError("JSON không có download_url trực tiếp cho asset này.")
    asset_type = asset.get("asset_type", "photo")
    last_error = None
    dest_dir.mkdir(parents=True, exist_ok=True)
    for idx, url in enumerate(urls, 1):
        if cancel.is_set():
            raise InterruptedError("Đã hủy tải media.")
        part = None
        try:
            validate_public_http_url(url)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36 EducationalAudioVideoStudio/1.16",
                "Accept": "image/avif,image/webp,image/apng,image/*,video/*,application/octet-stream;q=0.8,*/*;q=0.5",
            }
            if asset.get("source_page_url"):
                headers["Referer"] = asset["source_page_url"]
            request = Request(url, headers=headers)
            opener = build_opener(SafeRedirectHandler())
            with opener.open(request, timeout=60) as response:
                final_url = response.geturl()
                validate_public_http_url(final_url)
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise ValueError(f"HTTP {status} khi tải file.")
                ctype = response.headers.get("Content-Type", "")
                ctype_clean = ctype.split(";", 1)[0].strip().lower()
                if ctype_clean == "text/html" or ctype_clean == "application/xhtml+xml":
                    raise ValueError("URL trả về HTML, không phải file media trực tiếp.")
                if asset_type == "video" and not ctype_clean.startswith("video/") and Path(urlparse(final_url).path).suffix.lower() not in VIDEO_EXTS:
                    raise ValueError(f"Content-Type không phải video ({ctype_clean or 'unknown'}).")
                if asset_type != "video" and not ctype_clean.startswith("image/") and Path(urlparse(final_url).path).suffix.lower() not in IMAGE_EXTS:
                    raise ValueError(f"Content-Type không phải ảnh ({ctype_clean or 'unknown'}).")
                length = response.headers.get("Content-Length")
                expected_bytes = int(length) if length and str(length).isdigit() else None
                progress(0, expected_bytes, idx, len(urls))
                if length and int(length) > MAX_ASSET_BYTES:
                    raise ValueError(f"File quá lớn ({int(length)/1024/1024:.1f} MB; giới hạn 500 MB).")
                ext = _media_extension(final_url, ctype, asset_type)
                target = dest_dir / f"{safe_id}{ext}"
                part = target.with_suffix(target.suffix + ".part")
                total = 0
                with part.open("wb") as f:
                    while True:
                        if cancel.is_set():
                            raise InterruptedError("Đã hủy tải media.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_ASSET_BYTES:
                            raise ValueError("File vượt quá giới hạn 500 MB.")
                        f.write(chunk)
                        # Report every chunk (1 MiB) so the UI can show live byte progress.
                        progress(total, expected_bytes, idx, len(urls))
                if total < 128:
                    raise ValueError("File tải về quá nhỏ, có thể đây không phải media hợp lệ.")
                with part.open("rb") as f:
                    head = f.read(64)
                if asset_type == "video":
                    signature_ok = (b"ftyp" in head[:24] or head.startswith(b"\x1aE\xdf\xa3") or
                                    head.startswith(b"RIFF") or head.startswith(b"\x00\x00\x01\xba") or
                                    head.startswith(b"\x00\x00\x01\xb3"))
                else:
                    signature_ok = (head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n") or
                                    (head.startswith(b"RIFF") and b"WEBP" in head[:16]) or
                                    head.startswith((b"GIF87a", b"GIF89a")) or head.startswith(b"BM"))
                if not signature_ok:
                    raise ValueError("Nội dung tải về không có chữ ký file ảnh/video hợp lệ; có thể đây là trang xem hoặc trang lỗi.")
                width, height = verify_downloaded_media(part, asset_type)
                part.replace(target)
                dim_text = f", {width}x{height}" if width and height else ""
                log(f"Đã tải và giải mã thành công {asset_id}: {target.name} ({total/1024/1024:.2f} MB{dim_text})")
                return target
        except InterruptedError:
            if part and part.exists(): part.unlink(missing_ok=True)
            raise
        except Exception as exc:
            last_error = exc
            if part and part.exists(): part.unlink(missing_ok=True)
            log(f"URL {idx}/{len(urls)} không dùng được cho {asset_id}: {exc}")
    raise RuntimeError(f"Không có link media khả dụng cho {asset_id}. Đã thử {len(urls)} URL nhưng không tải/giải mã được. Hãy mở trang nguồn và yêu cầu AI tìm direct URL khác. Lỗi cuối: {last_error}")


def write_asset_credits(storyboard: dict[str, Any], asset_paths: dict[str, str], out_dir: Path) -> None:
    lines = ["MEDIA SOURCES / ATTRIBUTION", "Generated by Educational Audio Video Studio 1.9", ""]
    for asset in storyboard.get("assets", []):
        aid = asset.get("asset_id", "")
        path = asset_paths.get(aid, "")
        lines.extend([
            f"Asset: {aid}", f"Local file: {path or 'not downloaded'}",
            f"Provider: {asset.get('provider') or asset.get('source') or 'unknown'}",
            f"Creator: {asset.get('creator') or 'not specified'}",
            f"License: {asset.get('license_name') or asset.get('license_note') or 'not specified'}",
            f"License URL: {asset.get('license_url') or 'not specified'}",
            f"Source page: {asset.get('source_page_url') or 'not specified'}",
            f"Attribution: {asset.get('attribution') or 'not specified'}", ""
        ])
    (out_dir / "media_credits.txt").write_text("\n".join(lines), encoding="utf-8")


class StoryboardValidator:
    def __init__(self, schema: dict[str, Any]):
        self.schema = schema
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(self, data: dict[str, Any]) -> list[str]:
        errors = []
        for err in sorted(self.validator.iter_errors(data), key=lambda e: list(map(str, e.path))):
            path = "/".join(str(x) for x in err.path) or "root"
            errors.append(f"{path}: {err.message}")
        if errors:
            return errors
        if data.get("schema_version") != "1.3":
            errors.append("schema_version phải là 1.3. Hãy dùng prompt template mới.")
        segments = data.get("source_segments", [])
        assets = data.get("assets", [])
        scenes = data.get("scenes", [])
        seg_ids = [s["segment_id"] for s in segments]
        asset_ids = [a["asset_id"] for a in assets]
        scene_ids = [s["scene_id"] for s in scenes]
        if len(seg_ids) != len(set(seg_ids)):
            errors.append("source_segments: segment_id bị trùng.")
        if len(asset_ids) != len(set(asset_ids)):
            errors.append("assets: asset_id bị trùng.")
        if len(scene_ids) != len(set(scene_ids)):
            errors.append("scenes: scene_id bị trùng.")
        seg_map = {s["segment_id"]: s for s in segments}
        asset_map = {a["asset_id"]: a for a in assets}
        used_asset_ids = set()
        element_ids = []
        object_ids = []
        for asset in assets:
            aid = asset["asset_id"]
            if asset.get("source") == "stock_search" and asset.get("download_url"):
                for field in ("source_page_url", "provider", "license_name", "license_url", "attribution"):
                    if not asset.get(field):
                        errors.append(f"{aid}: có download_url nhưng thiếu metadata {field}.")
                verification = asset.get("web_verification") or {}
                for flag in ("source_page_opened", "direct_file_opened", "visual_match_confirmed", "license_checked"):
                    if verification.get(flag) is not True:
                        errors.append(f"{aid}: web_verification.{flag} phải là true nếu dùng stock media.")
                if asset.get("download_url") and asset.get("source_page_url") and asset["download_url"].rstrip("/") == asset["source_page_url"].rstrip("/"):
                    errors.append(f"{aid}: download_url đang trùng source_page_url.")
        for scene in scenes:
            sid = scene["scene_id"]
            fallback = scene.get("visual_fallback") or {}
            objects = fallback.get("objects", [])
            if not objects:
                errors.append(f"{sid}: visual_fallback.objects phải có ít nhất một icon vector/shape để dự phòng khi không có media.")
            if not any(el.get("kind") == "text" and (el.get("content") or "").strip() for el in scene.get("elements", [])):
                errors.append(f"{sid}: cần ít nhất một text element có nội dung để trình bày kiến thức trên hình (không tính karaoke subtitle).")
            scene_object_ids = {obj.get("object_id") for obj in objects if obj.get("object_id")}
            for obj in objects:
                oid = obj.get("object_id")
                if oid:
                    object_ids.append(oid)
                pos = obj.get("position", {})
                if float(pos.get("y", 0)) + float(pos.get("height", 0)) > 0.76:
                    errors.append(f"{sid}/{oid}: visual object đi vào vùng karaoke bên dưới (y + height > 0.76).")
            for connector in fallback.get("connectors", []):
                if connector.get("from_object") not in scene_object_ids:
                    errors.append(f"{sid}: connector from_object không tồn tại: {connector.get('from_object')}")
                if connector.get("to_object") not in scene_object_ids:
                    errors.append(f"{sid}: connector to_object không tồn tại: {connector.get('to_object')}")
            scene_asset_ids = scene.get("asset_ids", [])
            for seg_id in scene.get("segment_ids", []):
                if seg_id not in seg_map:
                    errors.append(f"{sid}: segment_id không tồn tại: {seg_id}")
            for aid in scene_asset_ids:
                used_asset_ids.add(aid)
                if aid not in asset_map:
                    errors.append(f"{sid}: asset_id không tồn tại: {aid}")
            for el in scene.get("elements", []):
                eid = el["element_id"]
                element_ids.append(eid)
                anchor = el["sync_anchor"]
                seg_id = anchor["segment_id"]
                if seg_id not in seg_map:
                    errors.append(f"{sid}/{eid}: sync_anchor trỏ tới segment không tồn tại: {seg_id}")
                quote = anchor.get("quote", "")
                if seg_id in seg_map and quote:
                    if normalize_text(quote) not in normalize_text(seg_map[seg_id]["text"]):
                        errors.append(f"{sid}/{eid}: quote không xuất hiện trong source segment {seg_id}: {quote!r}")
                if el.get("kind") == "text":
                    pos = el.get("position", {})
                    if float(pos.get("y", 0)) + float(pos.get("height", 0)) > 0.76:
                        errors.append(f"{sid}/{eid}: text overlay đi vào vùng karaoke bên dưới (y + height > 0.76).")
                aid = el.get("asset_id")
                if el.get("kind") in ("image", "video"):
                    if not aid:
                        errors.append(f"{sid}/{eid}: element image/video phải có asset_id; nếu không có media hãy dùng visual_fallback.")
                    elif aid not in asset_map:
                        errors.append(f"{sid}/{eid}: asset_id không tồn tại: {aid}")
                    else:
                        used_asset_ids.add(aid)
                        if aid not in scene_asset_ids:
                            errors.append(f"{sid}/{eid}: asset_id phải nằm trong scene.asset_ids.")
                        expected = "video" if asset_map[aid].get("asset_type") == "video" else "image"
                        if el.get("kind") != expected:
                            errors.append(f"{sid}/{eid}: asset_type={asset_map[aid].get('asset_type')} yêu cầu kind={expected}.")
            start, end = scene.get("provisional_start_s"), scene.get("provisional_end_s")
            if start is not None and end is not None and end <= start:
                errors.append(f"{sid}: provisional_end_s phải lớn hơn provisional_start_s.")
        if len(element_ids) != len(set(element_ids)):
            errors.append("elements: element_id bị trùng.")
        if len(object_ids) != len(set(object_ids)):
            errors.append("visual_fallback.objects: object_id bị trùng toàn project.")
        return errors


@dataclass
class RuntimeTiming:
    start: float
    end: float
    quality: str



# ---------------------------------------------------------------------------
# Reading Along: extract reading passages from public web pages (stdlib only)
# ---------------------------------------------------------------------------

class _ReadingWebNode:
    def __init__(self, tag: str, attrs: dict[str, str] | None = None):
        self.tag = (tag or "").lower()
        self.attrs = attrs or {}
        self.children: list[Any] = []


class _ReadingWebHTMLParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                 "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _ReadingWebNode("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _ReadingWebNode(tag, {str(k).lower(): (v or "") for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = _ReadingWebNode(tag, {str(k).lower(): (v or "") for k, v in attrs})
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        target = tag.lower()
        for idx in range(len(self.stack) - 1, 0, -1):
            if self.stack[idx].tag == target:
                del self.stack[idx:]
                break

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def _reading_web_descendants(node):
    for child in getattr(node, "children", []):
        if isinstance(child, _ReadingWebNode):
            yield child
            yield from _reading_web_descendants(child)


def _reading_web_text(node) -> str:
    parts = []
    block_tags = {"p", "div", "section", "article", "main", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
    for child in getattr(node, "children", []):
        if isinstance(child, str):
            parts.append(child)
        elif child.tag in {"script", "style", "noscript", "svg", "form", "nav", "footer", "header", "aside"}:
            continue
        else:
            value = _reading_web_text(child)
            if value:
                parts.append(value)
            if child.tag in block_tags:
                parts.append("\n")
    value = html_lib.unescape(" ".join(parts))
    value = re.sub(r"[ \t\u00a0]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _reading_web_excluded(node) -> bool:
    tag = node.tag
    attrs = node.attrs
    label = " ".join((attrs.get("id", ""), attrs.get("class", ""))).lower()
    if tag in {"script", "style", "noscript", "svg", "form", "nav", "footer", "header", "aside", "iframe"}:
        return True
    return any(word in label for word in (
        "advert", "ad-container", "breadcrumb", "related", "share", "social", "comment",
        "cookie", "menu", "sidebar", "navigation", "newsletter", "subscribe", "popup"
    ))


def _reading_web_blocks(root):
    blocks = []
    block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"}

    def walk(node):
        if not isinstance(node, _ReadingWebNode) or _reading_web_excluded(node):
            return
        if node.tag in block_tags:
            text = _reading_web_text(node)
            if text:
                blocks.append((node.tag, text))
            return
        for child in node.children:
            if isinstance(child, _ReadingWebNode):
                walk(child)

    walk(root)
    return blocks


def _reading_web_find_root(document):
    nodes = list(_reading_web_descendants(document))
    # Prefer WordPress article content containers over the full page shell.
    candidates = [n for n in nodes if n.tag in {"article", "main", "section", "div"} and
                  any(key in (n.attrs.get("class", "") + " " + n.attrs.get("id", "")).lower()
                      for key in ("entry-content", "post-content", "article-content", "content-area", "reading-content"))]
    if candidates:
        def root_score(node):
            label = (node.attrs.get("class", "") + " " + node.attrs.get("id", "")).lower()
            priority = 4 if "entry-content" in label else 3 if "post-content" in label else 2 if "article-content" in label else 1
            return (priority, len(_reading_web_text(node)))
        return max(candidates, key=root_score)
    articles = [n for n in nodes if n.tag == "article"]
    if articles:
        return max(articles, key=lambda n: len(_reading_web_text(n)))
    mains = [n for n in nodes if n.tag == "main"]
    if mains:
        return max(mains, key=lambda n: len(_reading_web_text(n)))
    bodies = [n for n in nodes if n.tag == "body"]
    return bodies[0] if bodies else document


def _reading_web_title(document, fallback: str) -> str:
    nodes = list(_reading_web_descendants(document))
    for tag in ("h1", "title"):
        for node in nodes:
            if node.tag == tag:
                value = _reading_web_text(node)
                if value:
                    value = re.sub(r"\s*[|–—-]\s*English Practice.*$", "", value, flags=re.I)
                    return value[:140]
    return fallback[:140] or "Reading Practice"


def _reading_web_links(document, page_url: str) -> list[dict[str, str]]:
    from urllib.parse import urljoin
    page_host = (urlparse(page_url).hostname or "").lower()
    found = []
    seen = set()
    for node in _reading_web_descendants(document):
        if node.tag != "a":
            continue
        href = (node.attrs.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(page_url, href)
        parts = urlparse(full)
        if parts.scheme not in {"http", "https"} or (parts.hostname or "").lower() != page_host:
            continue
        path = parts.path.lower()
        # This site's beginner reading index links to one page per reading exercise.
        is_reading_lesson = ("practice-reading-english-exercises-for-beginner-" in path and
                             path.rstrip("/") != urlparse(page_url).path.lower().rstrip("/"))
        if not is_reading_lesson:
            continue
        label = _reading_web_text(node)
        label = re.sub(r"^\d+\s*", "", label).strip(" -:|\n")
        if not label:
            label = Path(path.rstrip("/")).name.replace("practice-reading-english-exercises-for-beginner-", "").replace("-", " ").title()
        key = full.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        found.append({"title": label[:100], "url": key})
    return found


def parse_reading_web_html(html_text: str, final_url: str) -> dict[str, Any]:
    """Parse one already-downloaded page into a lesson title, content and lesson links."""
    from urllib.parse import urlparse
    parser = _ReadingWebHTMLParser()
    parser.feed(html_text)
    parser.close()
    title = _reading_web_title(parser.root, Path(urlparse(final_url).path.rstrip("/")).name.replace("-", " ").title())
    links = _reading_web_links(parser.root, final_url)
    root = _reading_web_find_root(parser.root)
    blocks = _reading_web_blocks(root)

    # Remove answer keys, navigation and comprehension-question prompts from the read-along script.
    selected_blocks = []
    reading_chars = 0
    for tag, block in blocks:
        clean = block.strip()
        lower = clean.lower()
        if tag in {"h2", "h3", "h4", "h5"} and lower in {"answer", "answers", "answer key", "related posts"}:
            break
        if reading_chars > 40 and re.match(
            r"^[A-H][.)]\s*(read|answer|choose|match|complete|write|circle|fill|tick|correct|true|false)",
            lower, re.I
        ):
            break
        if lower in {"advertisements", "advertisement", "share this", "related posts"}:
            continue
        selected_blocks.append(clean)
        if tag not in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            reading_chars += len(clean)

    content = "\n\n".join(selected_blocks)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    if links and len(content) < 120:
        content = ""
    if content:
        content = content[:30000]
    return {"title": title, "url": final_url, "links": links, "content": content}


def fetch_reading_web_page(url: str) -> dict[str, Any]:
    """Fetch one public HTML page, extract a reading lesson or same-site lesson links."""
    validate_public_http_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36 EducationalAudioVideoStudio/1.16",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }
    request = Request(url, headers=headers)
    opener = build_opener(SafeRedirectHandler())
    with opener.open(request, timeout=30) as response:
        final_url = response.geturl()
        validate_public_http_url(final_url)
        status = getattr(response, "status", 200)
        if status < 200 or status >= 300:
            raise RuntimeError(f"Trang web trả về HTTP {status}.")
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "html" not in content_type and "xhtml" not in content_type:
            raise RuntimeError(f"URL không trả về trang HTML (Content-Type: {content_type or 'không rõ'}).")
        raw = response.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise RuntimeError("Trang web quá lớn (giới hạn 5 MB cho mỗi lần nhập).")
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        html_text = raw.decode(charset, errors="replace")
    except LookupError:
        html_text = raw.decode("utf-8", errors="replace")
    return parse_reading_web_html(html_text, final_url)


# ---------------------------------------------------------------------------
# Reading Along Studio helpers (offline book layout + word-follow pointer)
# ---------------------------------------------------------------------------

def reading_tokenize(text: str, language: str = "English") -> list[str]:
    """Split reading text into visible tracking units. Japanese uses short phrase chunks."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    if language.lower().startswith("japanese"):
        raw = re.findall(r"[一-龯々〆ヵヶぁ-ゖァ-ヺー]+|[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|[^\w\s]", text, re.UNICODE)
        units: list[str] = []
        for part in raw:
            if re.fullmatch(r"[一-龯々〆ヵヶぁ-ゖァ-ヺー]+", part):
                # A short visual chunk is more readable than highlighting an entire Japanese sentence.
                units.extend(part[i:i + 3] for i in range(0, len(part), 3))
            elif part in "、。！？!?.,;:：；」』）】】":
                if units:
                    units[-1] += part
                else:
                    units.append(part)
            else:
                units.append(part)
        return units
    raw = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|[^\w\s]", text, re.UNICODE)
    units = []
    for part in raw:
        if re.fullmatch(r"[^\w\s]", part, re.UNICODE):
            if units:
                units[-1] += part
            else:
                units.append(part)
        else:
            units.append(part)
    return units


def reading_estimated_timings(tokens: list[str], duration: float) -> list[tuple[float, float]]:
    """Estimate word timing from text length and punctuation when forced alignment is unavailable."""
    if not tokens:
        return []
    weights = []
    for token in tokens:
        clean = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]", "", token, flags=re.UNICODE)
        weight = max(0.8, len(clean) ** 0.72)
        if re.search(r"[,;，、]$", token):
            weight += 0.55
        elif re.search(r"[.!?。！？]$", token):
            weight += 1.15
        weights.append(weight)
    total = sum(weights) or 1.0
    cursor = 0.0
    timings = []
    for weight in weights:
        span = duration * weight / total
        start = cursor
        cursor += span
        timings.append((start, min(duration, cursor)))
    if timings:
        timings[-1] = (timings[-1][0], duration)
    return timings


def reading_whisper_timings(audio: Path, tokens: list[str], language: str,
                            log=lambda _m: None,
                            cancel: Optional[threading.Event] = None) -> Optional[list[tuple[float, float]]]:
    """Align visible reading units to Whisper timestamps, including Japanese text.

    Characters are aligned rather than requiring the source text and ASR to use
    exactly the same word segmentation. Each matched visible unit receives the
    time span of its matched characters; missing units are interpolated between
    neighboring matched units.
    """
    try:
        from faster_whisper import WhisperModel
    except Exception:
        log("faster-whisper is not installed; using estimated word timing. Run install_alignment.bat to enable alignment.")
        return None

    is_japanese = language.lower().startswith("japanese")
    lang_code = "ja" if is_japanese else "en"
    model_dir = WHISPER_DIR / "small"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_ref = str(model_dir) if any(model_dir.iterdir()) else "small"
    log(f"Loading faster-whisper small for {'Japanese phrase' if is_japanese else 'English word'} alignment...")
    model = WhisperModel(model_ref, device="cpu", compute_type="int8", download_root=str(WHISPER_DIR))
    segments, _info = model.transcribe(str(audio), language=lang_code, beam_size=5,
                                       word_timestamps=True, vad_filter=True)

    recognized: list[tuple[str, float, float]] = []
    for segment in segments:
        if cancel and cancel.is_set():
            raise InterruptedError("Reading Along alignment cancelled.")
        words = list(getattr(segment, "words", None) or [])
        if words:
            for word in words:
                key = normalize_text(getattr(word, "word", ""))
                if key:
                    recognized.append((key, float(word.start), float(word.end)))
        else:
            # Japanese ASR may return phrase-level segments instead of word tokens.
            key = normalize_text(getattr(segment, "text", ""))
            if key:
                recognized.append((key, float(segment.start), float(segment.end)))

    if not recognized:
        log("Whisper returned no usable word/phrase timestamps; using estimated timing.")
        return None

    # Expand recognized words/phrases to character-time anchors. This tolerates
    # different segmentation between the supplied text and Whisper's transcript.
    source_chars: list[str] = []
    source_char_times: list[tuple[float, float]] = []
    for key, start_s, end_s in recognized:
        chars = list(key)
        if not chars:
            continue
        span = max(0.015, end_s - start_s)
        for char_i, char in enumerate(chars):
            a = start_s + span * char_i / len(chars)
            b = start_s + span * (char_i + 1) / len(chars)
            source_chars.append(char)
            source_char_times.append((a, max(a + 0.008, b)))

    target_chars: list[str] = []
    target_char_owner: list[int] = []
    target_char_count = [0] * len(tokens)
    for token_i, token in enumerate(tokens):
        key = normalize_text(token)
        for char in key:
            target_chars.append(char)
            target_char_owner.append(token_i)
            target_char_count[token_i] += 1
    if not target_chars or not source_chars:
        return None

    matcher = SequenceMatcher(None, target_chars, source_chars, autojunk=False)
    char_spans: dict[int, tuple[float, float]] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(min(i2 - i1, j2 - j1)):
                char_spans[i1 + offset] = source_char_times[j1 + offset]

    matched_char_count = len(char_spans)
    coverage = matched_char_count / max(1, len(target_chars))
    if coverage < 0.45:
        log(f"Whisper transcript matched only {coverage:.0%} of text characters; using estimated timing instead.")
        return None

    # Combine the matched character timestamps belonging to each visible word/chunk.
    token_spans: dict[int, tuple[float, float]] = {}
    for token_i in range(len(tokens)):
        spans = [char_spans[i] for i, owner in enumerate(target_char_owner)
                 if owner == token_i and i in char_spans]
        if spans and len(spans) >= max(1, math.ceil(target_char_count[token_i] * 0.45)):
            token_spans[token_i] = (min(x[0] for x in spans), max(x[1] for x in spans))

    duration = probe_duration(audio)
    timings: list[Optional[tuple[float, float]]] = [None] * len(tokens)
    for idx, span in token_spans.items():
        timings[idx] = span

    # Interpolate unmatched words in the gaps between known Whisper anchors.
    anchors = sorted(token_spans.items())
    boundaries = [(-1, (0.0, 0.0))] + anchors + [(len(tokens), (duration, duration))]
    for b in range(len(boundaries) - 1):
        left_i, left_span = boundaries[b]
        right_i, right_span = boundaries[b + 1]
        missing = list(range(left_i + 1, right_i))
        if not missing:
            continue
        gap_start = max(0.0, left_span[1])
        gap_end = max(gap_start, right_span[0])
        weights = [max(1.0, len(normalize_text(tokens[i]))) for i in missing]
        total = sum(weights) or 1.0
        cursor = gap_start
        for i, weight in zip(missing, weights):
            nxt = cursor + (gap_end - gap_start) * weight / total
            timings[i] = (cursor, nxt)
            cursor = nxt

    final: list[tuple[float, float]] = []
    last_start = 0.0
    for idx, span in enumerate(timings):
        if span is None:
            span = (last_start, last_start + 0.04)
        start_s, end_s = span
        start_s = max(last_start, min(duration, float(start_s)))
        end_s = max(start_s + 0.015, min(duration, float(end_s)))
        end_s = min(duration, end_s)
        if end_s <= start_s:
            end_s = min(duration, start_s + 0.015)
        final.append((start_s, end_s))
        last_start = start_s

    log(f"Whisper alignment completed: {len(token_spans)}/{len(tokens)} visible units mapped; character coverage {coverage:.0%}.")
    return final


def _reading_draw_hand(draw: ImageDraw.ImageDraw, center_x: float, top_y: float, scale: float = 1.0):
    """Draw a simple pointing hand with Pillow primitives; no external image asset required."""
    s = scale
    x = int(center_x)
    y = int(top_y)
    white = "#FFFDF7"
    outline = "#334155"
    width = max(2, int(2.2 * s))
    # Index finger points upward to the active word; palm and thumb sit below it.
    draw.rounded_rectangle((x - int(8*s), y, x + int(8*s), y + int(34*s)),
                           radius=max(3, int(7*s)), fill=white, outline=outline, width=width)
    draw.rounded_rectangle((x - int(19*s), y + int(24*s), x + int(19*s), y + int(55*s)),
                           radius=max(5, int(12*s)), fill=white, outline=outline, width=width)
    draw.line((x - int(16*s), y + int(34*s), x - int(30*s), y + int(23*s),
               x - int(36*s), y + int(30*s), x - int(20*s), y + int(48*s)),
              fill=outline, width=max(3, int(8*s)), joint="curve")
    draw.line((x - int(7*s), y + int(51*s), x + int(7*s), y + int(51*s)),
              fill="#D7DEE8", width=max(1, int(2*s)))


def _reading_draw_corner_illustration(draw: ImageDraw.ImageDraw, topic: str,
                                      left: int, top: int, size: int = 118,
                                      style: str = "2.5D"):
    """Draw a topic illustration with flat, 2.5D layered, or faux-3D cartoon depth."""
    topic_key = (topic or "reading").lower()
    is_3d = style.lower().startswith("3d")
    is_depth = is_3d or style.lower().startswith("2.5")
    if is_depth:
        draw.rounded_rectangle((left+5, top+7, left+size+5, top+size+7), radius=20, fill="#C6D2DE")
    draw.rounded_rectangle((left, top, left + size, top + size), radius=18,
                           fill="#F7FBFF" if is_depth else "#F1E8D9", outline="#B8C9D8" if is_depth else "#D9C9B2", width=2)
    cx, cy = left + size // 2, top + size // 2
    if is_3d:
        draw.arc((left+4, top+4, left+size-4, top+size-4), 190, 285, fill="#FFFFFF", width=4)
        draw.arc((left+5, top+5, left+size-5, top+size-5), 5, 95, fill="#D5E3EF", width=3)
    # Small decorative dots make the illustration feel lively without stealing focus.
    draw.ellipse((left + 12, top + 12, left + 22, top + 22), fill="#F4B860")
    draw.ellipse((left + size - 24, top + 16, left + size - 14, top + 26), fill="#8AC6C5")
    if any(k in topic_key for k in ("food", "drink", "restaurant", "cafe", "cook", "breakfast")):
        draw.ellipse((cx-37, cy-26, cx+37, cy+26), fill="#FFFDF7", outline="#60758A", width=3)
        draw.ellipse((cx-22, cy-15, cx+22, cy+15), fill="#F5C66A", outline="#D59B3B", width=2)
        draw.ellipse((cx-8, cy-8, cx+9, cy+8), fill="#D76C50")
        draw.line((cx+43, cy-28, cx+43, cy+28), fill="#66788B", width=4)
        for dy in (-18, -7, 5, 17):
            draw.line((cx+39, cy+dy, cx+47, cy+dy), fill="#66788B", width=2)
    elif any(k in topic_key for k in ("travel", "holiday", "trip", "airport", "journey")):
        draw.rounded_rectangle((cx-35, cy-27, cx+35, cy+30), radius=9,
                               fill="#6BA6C9", outline="#365B78", width=3)
        draw.arc((cx-16, cy-43, cx+16, cy-9), 180, 360, fill="#365B78", width=5)
        draw.line((cx-22, cy-2, cx+22, cy-2), fill="#EAF5F8", width=3)
        draw.ellipse((cx-24, cy+25, cx-13, cy+36), fill="#365B78")
        draw.ellipse((cx+13, cy+25, cx+24, cy+36), fill="#365B78")
    elif any(k in topic_key for k in ("work", "office", "job", "computer", "study")):
        draw.rounded_rectangle((cx-39, cy-28, cx+39, cy+20), radius=7,
                               fill="#5B86A8", outline="#36536D", width=3)
        draw.rectangle((cx-29, cy-18, cx+29, cy+10), fill="#DFF3F3")
        draw.line((cx, cy+20, cx, cy+31), fill="#36536D", width=5)
        draw.rounded_rectangle((cx-28, cy+29, cx+28, cy+36), radius=3, fill="#36536D")
        draw.ellipse((cx+12, cy-12, cx+22, cy-2), fill="#F0B45B")
    elif any(k in topic_key for k in ("home", "house", "morning", "routine", "place", "city", "daily")):
        draw.polygon([(cx-42, cy-5), (cx, cy-39), (cx+42, cy-5)],
                     fill="#D88968", outline="#8D5747")
        draw.rectangle((cx-31, cy-5, cx+31, cy+36), fill="#F7D99A", outline="#8D7250", width=2)
        draw.rectangle((cx-8, cy+10, cx+9, cy+36), fill="#7B9CB5")
        draw.rectangle((cx-24, cy+2, cx-12, cy+15), fill="#B8DDE5")
        draw.rectangle((cx+14, cy+2, cx+25, cy+15), fill="#B8DDE5")
        draw.ellipse((left+size-39, top+9, left+size-17, top+31), fill="#F4C45D")
    else:
        # Default: a friendly open book with a pencil and a tiny sparkle.
        draw.polygon([(cx-39, cy-24), (cx-3, cy-17), (cx-3, cy+31), (cx-39, cy+23)],
                     fill="#FFFDF7", outline="#5B7085")
        draw.polygon([(cx+3, cy-17), (cx+39, cy-24), (cx+39, cy+23), (cx+3, cy+31)],
                     fill="#FFFDF7", outline="#5B7085")
        draw.line((cx, cy-17, cx, cy+31), fill="#5B7085", width=3)
        for yy in (-8, 3, 14):
            draw.line((cx-31, cy+yy, cx-10, cy+yy+4), fill="#9AABBA", width=2)
            draw.line((cx+10, cy+yy+4, cx+31, cy+yy), fill="#9AABBA", width=2)
        draw.line((left+size-31, top+37, left+size-18, top+63), fill="#D98B4D", width=5)
        draw.polygon([(left+size-18, top+63), (left+size-13, top+71),
                      (left+size-23, top+66)], fill="#4B5563")


READING_BOOK_PALETTES = {
    "Sunny Yellow": {"paper":"#FFF8D9", "paper_edge":"#F0D98A", "accent":"#F4B942", "highlight":"#FFE082", "ribbon":"#FFF0B3", "ink":"#34445B", "muted":"#947A45", "progress":"#F2A93B"},
    "Ocean Blue": {"paper":"#EAF8FF", "paper_edge":"#9ED7EF", "accent":"#36A9D6", "highlight":"#B8E8FF", "ribbon":"#D5F2FF", "ink":"#24465C", "muted":"#547F96", "progress":"#36A9D6"},
    "Mint Green": {"paper":"#EEFFE9", "paper_edge":"#B8E0A8", "accent":"#65B96B", "highlight":"#CFF3A9", "ribbon":"#DFF6D5", "ink":"#31523B", "muted":"#63866A", "progress":"#65B96B"},
    "Peach Pink": {"paper":"#FFF0E9", "paper_edge":"#F2BBA8", "accent":"#F08C70", "highlight":"#FFD0B8", "ribbon":"#FFE0D3", "ink":"#68463F", "muted":"#A16F61", "progress":"#F08C70"},
    "Lavender": {"paper":"#F5F0FF", "paper_edge":"#D0BDF2", "accent":"#9A7BDB", "highlight":"#E2D4FF", "ribbon":"#EAE1FF", "ink":"#44385F", "muted":"#8171A6", "progress":"#9A7BDB"},
    "White Classic": {"paper":"#FFFFFF", "paper_edge":"#D8DEE8", "accent":"#4F86C6", "highlight":"#FFF0A6", "ribbon":"#EEF4FB", "ink":"#25374A", "muted":"#7B8794", "progress":"#60A5A0"},
}

def render_reading_book_frame(title: str, topic: str, tokens: list[str], active_index: int,
                              page_index: int, page_size: int, language: str,
                              level: str, width: int = 720, height: int = 1280,
                              book_color: str = "Sunny Yellow",
                              illustration_style: str = "2.5D") -> Image.Image:
    """Render a colorful book page with optional stylized pseudo-3D corner illustration."""
    palette = READING_BOOK_PALETTES.get(book_color, READING_BOOK_PALETTES["Sunny Yellow"])
    im = Image.new("RGB", (width, height), "#182A40")
    draw = ImageDraw.Draw(im)
    # Warm page shadow and clean single-page layout (not a two-page spread).
    for y in range(height):
        p = y / max(1, height - 1)
        a, b = (17, 31, 49), (37, 58, 78)
        rgb = tuple(int(a[i] * (1-p) + b[i] * p) for i in range(3))
        draw.line((0, y, width, y), fill=rgb)
    page = (36, 32, width-36, height-42)
    draw.rounded_rectangle((page[0]-6, page[1]+12, page[2]+6, page[3]+14), radius=26, fill="#091421")
    draw.rounded_rectangle(page, radius=24, fill=palette["paper"], outline=palette["paper_edge"], width=4)
    # Soft paper margin and editorial header.
    draw.rounded_rectangle((page[0]+17, page[1]+17, page[2]-17, page[3]-17),
                           radius=16, outline=palette["paper_edge"], width=2)
    left, right = page[0]+48, page[2]-48
    draw.text((left, page[1]+37), "READING PRACTICE", font=get_font("READING PRACTICE", 16, True), fill=palette["muted"])
    tag = f"{language.upper()}  •  {level.upper()}"
    tag_font = get_font(tag, 14, True)
    tag_w = draw.textlength(tag, font=tag_font)
    draw.rounded_rectangle((right-tag_w-22, page[1]+31, right, page[1]+58), radius=12, fill=palette["ribbon"])
    draw.text((right-tag_w-11, page[1]+36), tag, font=tag_font, fill=palette["ink"])

    title_text = (title or "Reading Practice").strip()
    is_japanese = language.lower().startswith("japanese")
    title_font = get_font(title_text, 34 if not is_japanese else 31, True)
    illustration_size = 112
    illustration_left = right-illustration_size
    illustration_top = page[1]+77
    _reading_draw_corner_illustration(draw, topic or title_text,
                                      illustration_left, illustration_top, illustration_size,
                                      style=illustration_style)
    title_left = left
    title_right = illustration_left-22
    max_title_width = max(180, title_right-title_left)
    title_words = list(title_text) if is_japanese else title_text.split()
    title_lines: list[str] = []
    current = ""
    for word in title_words:
        candidate = current + ("" if is_japanese or not current else " ") + word
        if current and draw.textlength(candidate, font=title_font) > max_title_width:
            title_lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        title_lines.append(current)
    if len(title_lines) > 2:
        title_font = get_font(title_text, 28 if not is_japanese else 26, True)
        title_lines = []
        current = ""
        for word in title_words:
            candidate = current + ("" if is_japanese or not current else " ") + word
            if current and draw.textlength(candidate, font=title_font) > max_title_width:
                title_lines.append(current); current = word
            else:
                current = candidate
        if current:
            title_lines.append(current)
    title_y = page[1]+82
    title_line_height = 43 if title_font.size >= 30 else 36
    for line in title_lines[:3]:
        draw.text((title_left, title_y), line, font=title_font, fill=palette["ink"])
        title_y += title_line_height

    # Topic ribbon and separator; body always begins below the title area.
    topic_label = (topic or "Reading lesson").strip()[:46]
    topic_font = get_font(topic_label, 15, False)
    ribbon_y = max(page[1]+204, title_y+11)
    draw.rounded_rectangle((left, ribbon_y, min(right, left+draw.textlength(topic_label, font=topic_font)+28), ribbon_y+31),
                           radius=12, fill=palette["ribbon"])
    draw.text((left+12, ribbon_y+7), topic_label, font=topic_font, fill=palette["muted"])
    draw.line((left, ribbon_y+48, right, ribbon_y+48), fill=palette["paper_edge"], width=2)

    # Reading text is laid out like normal book typography, with the active token highlighted.
    page_start = page_index * page_size
    page_tokens = tokens[page_start:page_start + page_size]
    active_local = max(0, min(len(page_tokens)-1, active_index-page_start)) if page_tokens else 0
    body_left = left+4
    body_right = right-4
    body_top = ribbon_y+78
    footer_y = page[3]-75
    # Reserve enough room for the hand graphic and the footer, but do not leave
    # the text block pinned to the top with a large unexplained gap underneath.
    hand_bottom = footer_y-24
    hand_top_limit = hand_bottom-58
    body_bottom = hand_top_limit-10
    font_size = 34 if not is_japanese else 32
    page_font = get_font(" ".join(page_tokens), font_size, False)
    line_height = 96
    gap = 4 if is_japanese else 12

    def layout_reading_tokens(font, size, line_gap):
        x, y = body_left, body_top
        result: list[tuple[float, float, float, float]] = []
        for token in page_tokens:
            bbox = draw.textbbox((0, 0), token, font=font)
            tw = draw.textlength(token, font=font)
            th = max(size+4, bbox[3]-bbox[1])
            if x > body_left and x+tw > body_right:
                x = body_left
                y += line_gap
            result.append((x, y, tw, th))
            x += tw+gap
        return result

    boxes = layout_reading_tokens(page_font, font_size, line_height)
    # Long passages get a smaller type size before any text can intrude into
    # the pointer/footer reservation.
    if boxes and max(box[1]+box[3] for box in boxes) > body_bottom:
        font_size = 24 if not is_japanese else 25
        page_font = get_font(" ".join(page_tokens), font_size, False)
        line_height = 68
        gap = 3 if is_japanese else 9
        boxes = layout_reading_tokens(page_font, font_size, line_height)

    # Keep the reading block anchored at the top of the body area. Use a larger
    # default type size and relaxed line spacing so a normal paragraph occupies
    # more of the page without drifting down into the footer.

    has_active_word = 0 <= active_index < len(tokens) and bool(page_tokens)
    for i, (token, (tx, ty, tw, th)) in enumerate(zip(page_tokens, boxes)):
        if has_active_word and i == active_local:
            draw.rounded_rectangle((tx-7, ty-5, tx+tw+8, ty+th+8), radius=8,
                                   fill=palette["highlight"], outline=palette["accent"], width=2)
        draw.text((tx, ty), token, font=page_font,
                  fill=palette["ink"] if has_active_word and i == active_local else "#526174")
    if boxes and has_active_word:
        tx, ty, tw, th = boxes[active_local]
        hand_x = min(body_right-18, max(body_left+18, tx+tw/2))
        hand_y = min(hand_top_limit, ty+th+4)
        _reading_draw_hand(draw, hand_x, hand_y, 0.46 if width < 1000 else 0.62)

    # Page footer and progress line.
    page_no = page_index+1
    pages_total = max(1, math.ceil(len(tokens)/max(1,page_size)))
    draw.line((left, footer_y-18, right, footer_y-18), fill=palette["paper_edge"], width=2)
    draw.text((left, footer_y), f"PAGE {page_no} / {pages_total}",
              font=get_font("PAGE 1 / 1", 14, True), fill=palette["muted"])
    draw.text((right-142, footer_y), f"{min(len(tokens), active_index+1)} / {len(tokens)} units",
              font=get_font("0 units", 14, False), fill=palette["muted"])
    rail_y = page[3]-29
    draw.rounded_rectangle((left, rail_y, right, rail_y+7), radius=4, fill=palette["paper_edge"])
    progress = (active_index+1)/max(1,len(tokens))
    draw.rounded_rectangle((left, rail_y, left+int((right-left)*progress), rail_y+7), radius=4, fill=palette["progress"])
    return im


def _reading_atempo_filter(speed: float) -> str:
    """Build an FFmpeg atempo chain for a combined speed multiplier."""
    speed = max(0.5, min(3.0, float(speed)))
    factors = []
    remaining = speed
    while remaining > 2.0:
        factors.append(2.0); remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5); remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def _reading_speed_value(value: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*x", str(value).lower())
    if not match:
        return 1.0
    return max(0.75, min(1.5, float(match.group(1))))


def reading_timeline_entries(timings: list[tuple[float, float]], duration: float) -> list[tuple[int, float]]:
    """Return (active_token_index, source_seconds) frames covering the full audio.

    A word remains highlighted until the next word actually begins. This preserves
    pauses and breaths instead of compressing them out of the picture timeline.
    """
    if not timings or duration <= 0:
        return []
    starts: list[float] = []
    last = 0.0
    for start_s, _end_s in timings:
        value = max(last, min(float(duration), float(start_s)))
        starts.append(value)
        last = value

    entries: list[tuple[int, float]] = []
    first_start = starts[0]
    if first_start > 0.025:
        entries.append((-1, first_start))  # blank reading state during leading silence

    for idx, start_s in enumerate(starts):
        next_start = starts[idx+1] if idx+1 < len(starts) else float(duration)
        end_s = max(start_s, min(float(duration), next_start))
        span = end_s-start_s
        if span <= 0.0005:
            # Merge effectively simultaneous ASR tokens into a one-frame transition;
            # the next token takes over at its own onset.
            continue
        entries.append((idx, span))

    # Guarantee the output video reaches the original audio end even if the ASR
    # timestamps stop slightly early due to codec/container duration differences.
    total = sum(span for _idx, span in entries)
    remainder = max(0.0, float(duration)-total)
    if entries and remainder > 0.0005:
        idx, span = entries[-1]
        entries[-1] = (idx, span+remainder)
    if not entries:
        entries = [(0, float(duration))]
    return entries


def render_reading_along_video(title: str, topic: str, text: str, audio: Path, output: Path,
                               language: str, level: str, use_whisper: bool,
                               cancel: threading.Event,
                               progress=lambda _p, _m: None,
                               log=lambda _m: None,
                               speech_speed: float = 1.0,
                               video_speed: float = 1.0,
                               book_color: str = "Sunny Yellow",
                               illustration_style: str = "2.5D") -> tuple[int, float, str]:
    """Render a reading video with timestamp-based pointer motion and pause-aware sync."""
    tokens = reading_tokenize(text, language)
    if not tokens:
        raise RuntimeError("Chưa có nội dung bài đọc.")
    original_duration = probe_duration(audio)
    effective_speed = max(0.5625, min(2.25, float(speech_speed)*float(video_speed)))
    output_duration = original_duration/effective_speed
    timings = None
    timing_method = "estimated timing (text-weighted)"
    if use_whisper:
        try:
            timings = reading_whisper_timings(audio, tokens, language, log=log, cancel=cancel)
            if timings:
                timing_method = "Whisper character/word timestamp alignment"
        except InterruptedError:
            raise
        except Exception as exc:
            log(f"Whisper alignment unavailable: {exc}. Using estimated timing.")
    if not timings:
        timings = reading_estimated_timings(tokens, original_duration)
        log("Reading timing fallback: estimated from text length/punctuation; this cannot follow real pauses as accurately as Whisper.")

    timeline = reading_timeline_entries(timings, original_duration)
    if not timeline:
        raise RuntimeError("Không tạo được timeline cho bài đọc.")

    page_size = 48
    tmp_root = Path(tempfile.mkdtemp(prefix="reading_along_", dir=str(OUTPUT_DIR)))
    try:
        concat_path = tmp_root / "frames.txt"
        lines = []
        for frame_i, (active_idx, source_span) in enumerate(timeline):
            if cancel.is_set():
                raise InterruptedError("Đã hủy xuất Reading Along.")
            visual_idx = max(0, active_idx)
            page_idx = visual_idx//page_size
            frame = render_reading_book_frame(title, topic, tokens, active_idx, page_idx, page_size,
                                              language, level, width=720, height=1280,
                                              book_color=book_color, illustration_style=illustration_style)
            frame_path = tmp_root/f"frame_{frame_i:06d}.png"
            frame.save(frame_path, format="PNG", optimize=True)
            safe_path = str(frame_path.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe_path}'")
            # Each state covers the complete interval until the next word onset,
            # including silence, breaths and natural TTS pauses.
            span_seconds = max(1.0/24.0, float(source_span)/effective_speed)
            lines.append(f"duration {span_seconds:.6f}")
            if frame_i % max(1, len(timeline)//20) == 0:
                progress(10+int(65*frame_i/max(1,len(timeline)-1)),
                         f"Căn timeline + dàn trang: {frame_i+1}/{len(timeline)}")
        last_path = str((tmp_root/f"frame_{len(timeline)-1:06d}.png").resolve()).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{last_path}'")
        concat_path.write_text("\n".join(lines), encoding="utf-8")
        if cancel.is_set():
            raise InterruptedError("Đã hủy xuất Reading Along.")
        output.parent.mkdir(parents=True, exist_ok=True)
        progress(78, f"Đang ghép video + TTS ở tốc độ {effective_speed:.2f}x...")
        cmd = ["-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
               "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0"]
        if abs(effective_speed-1.0) > 0.001:
            cmd += ["-filter:a", _reading_atempo_filter(effective_speed)]
        # tpad prevents a one-frame concat/fps rounding difference from trimming
        # the tail of the narration. -t controls both streams to the target length.
        cmd += ["-t", f"{output_duration:.3f}",
                "-vf", "fps=24,tpad=stop_mode=clone:stop_duration=1,format=yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
        result = run_ffmpeg(cmd, timeout=max(180, int(output_duration*8)))
        if result.returncode != 0 or not output.exists() or output.stat().st_size < 2048:
            detail = (result.stderr or b"").decode("utf-8", errors="replace")[-3000:]
            raise RuntimeError("FFmpeg không xuất được Reading Along video.\n"+detail)
        progress(100, "Reading Along MP4 hoàn tất.")
        log(f"Reading Along speed: speech={speech_speed:.2f}x, video={video_speed:.2f}x, combined={effective_speed:.2f}x; timeline includes pauses.")
        return len(tokens), output_duration, f"{timing_method}; pause-aware timeline; playback {effective_speed:.2f}x"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def generate_reading_lesson(topic: str, language: str, level: str) -> tuple[str, str]:
    """Create an editable offline sample lesson from built-in topic templates (no API needed)."""
    topic = (topic or "Everyday Life").strip()
    key = topic.lower()
    if language.lower().startswith("japanese"):
        templates = [
            (("restaurant", "food", "cafe", "レストラン", "食事"), "レストランでの会話", "今日は友達とレストランに行きます。\nメニューを見て、食べたい料理を選びます。\n店員におすすめを聞いて、水を一杯お願いします。\n料理が来たら、ゆっくり味わって食べます。\n最後に、お会計をして店を出ます。"),
            (("travel", "trip", "airport", "旅行", "旅"), "旅行の準備", "旅行の前に、必要なものを確認します。\nパスポートとチケットをバッグに入れます。\n空港には時間に余裕を持って到着します。\n搭乗口を確認して、飛行機に乗ります。\n新しい場所で、たくさんの経験を楽しみます。"),
            (("work", "office", "仕事", "会社"), "仕事の一日", "朝、会社に着いたら、まず今日の予定を確認します。\n必要な資料を準備して、仕事を始めます。\n分からないことがあれば、同僚に質問します。\n昼休みの後、残っている仕事を一つずつ進めます。\n最後に、明日の予定を確認して帰ります。"),
            (("animal", "cat", "dog", "動物", "猫", "犬"), "小さな動物の物語", "小さな猫が庭で遊んでいます。\n猫は白い花のそばで、蝶を見つけました。\n蝶は風に乗って、空へ飛んでいきます。\n猫は少し歩いて、日なたで休みます。\n静かな午後がゆっくり過ぎていきます。"),
        ]
        selected = next((item for item in templates if any(k in key for k in item[0])), None)
        if selected:
            return selected[1], selected[2]
        title = f"{topic}について読んでみよう"
        body = (f"今日は「{topic}」について学びます。\n"
                "まず、基本的な言葉を確認して、短い文を読んでみましょう。\n"
                "大切なのは、一つずつ意味を考えながら、声に出して読むことです。\n"
                "分からない言葉があれば、前後の文から意味を想像してみます。\n"
                "毎日少しずつ練習すると、読む力と表現力が自然に伸びていきます。")
        return title, body
    templates = [
        (("restaurant", "food", "cafe", "nhà hàng", "đồ ăn"), "A Meal at a Restaurant", "Mia goes to a small restaurant with her friend.\nThey look at the menu and choose their food.\nMia asks the waiter for a glass of water.\nThe food arrives, and they enjoy their meal.\nAfter dinner, they pay the bill and walk home."),
        (("travel", "trip", "airport", "du lịch", "traveling"), "Getting Ready for a Trip", "Daniel is getting ready for a trip.\nHe checks his passport and puts his ticket in his bag.\nHe arrives at the airport early.\nHe looks at the screen and finds his gate.\nSoon, he gets on the plane and starts his journey."),
        (("work", "office", "job", "công việc", "văn phòng"), "A Day at Work", "Anna arrives at the office at eight o'clock.\nShe checks her schedule and prepares the documents.\nWhen she has a question, she asks her teammate.\nAfter lunch, she finishes the most important tasks.\nBefore going home, she writes a short plan for tomorrow."),
        (("animal", "cat", "dog", "động vật", "mèo", "chó"), "A Little Cat in the Garden", "A little cat is playing in the garden.\nIt sees a butterfly near a yellow flower.\nThe butterfly flies away, and the cat follows it slowly.\nAfter a while, the cat sits in the warm sunshine.\nIt closes its eyes and enjoys a quiet afternoon."),
        (("daily", "routine", "everyday", "thói quen", "daily life"), "A Simple Morning Routine", "Tom wakes up early every morning.\nHe opens the window and makes his bed.\nThen he drinks a glass of water and eats breakfast.\nHe checks the time, takes his bag, and leaves home.\nA good morning helps him start the day with energy."),
    ]
    selected = next((item for item in templates if any(k in key for k in item[0])), None)
    if selected:
        title, body = selected[1], selected[2]
        if level.upper() in {"B1", "B2"}:
            body += "\nAfter reading, try to retell the story in your own words and use the new expressions."
        elif level.upper() == "BEGINNER":
            body = "\n".join(body.splitlines()[:4])
        return title, body
    title = f"Learning About {topic.title()}"
    body = (f"Today, we are learning about {topic}.\n"
            f"First, take a moment to understand the main idea of {topic}.\n"
            "Read each sentence slowly and notice the important words.\n"
            "When you meet a new word, look at the words around it for clues.\n"
            "Try reading the passage again, this time with a natural rhythm.\n"
            "Small steps every day can make a big difference.")
    return title, body


class EducationalVideoStudio:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1320x850")
        self.root.minsize(1080, 700)
        self.root.configure(bg="#0d1625")
        self.q: queue.Queue = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.cancel = threading.Event()
        self.storyboard: Optional[dict[str, Any]] = None
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = StoryboardValidator(self.schema)
        self.asset_paths: dict[str, str] = {}
        self.storyboard_path: Optional[Path] = None
        self.assets_workspace: Path = ASSETS_DIR
        self.aligned_segments: dict[str, RuntimeTiming] = {}
        self.aligned_anchors: dict[str, RuntimeTiming] = {}
        self.asr_words: list[dict[str, Any]] = []
        self.detected_language: str = "auto"
        self.subtitles_var = tk.BooleanVar(value=True)
        self.audio_duration_s: Optional[float] = None
        self.audio_var = tk.StringVar()
        self.text_var = tk.StringVar()
        self.json_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(OUTPUT_DIR / "educational_video.mp4"))
        self.output_customized = False
        self.composition_var = tk.StringVar(value="Auto theo nội dung")
        self.composition_desc_var = tk.StringVar(value=VISUAL_COMPOSITION_PRESETS["Auto theo nội dung"]["description"])
        self.resolution_var = tk.StringVar(value="720x1280 (khuyên dùng)")
        self.fps_var = tk.IntVar(value=24)
        self.status_var = tk.StringVar(value="Chọn audio, transcript và storyboard JSON để bắt đầu.")
        self.asset_progress_var = tk.StringVar(value="Chưa bắt đầu tải media.")
        self._asset_progress_running = False
        self.asset_direct_url_var = tk.StringVar(value="")
        self.asset_source_url_var = tk.StringVar(value="")
        self.project_status_var = tk.StringVar(value="Chưa tải storyboard")
        self.karaoke_video_var = tk.StringVar()
        self.karaoke_subtitle_var = tk.StringVar()
        self.karaoke_output_var = tk.StringVar()
        self.karaoke_effect_var = tk.StringVar(value="Classic Karaoke – tô màu từng từ")
        self.karaoke_position_var = tk.StringVar(value="Dưới")
        self.karaoke_size_var = tk.StringVar(value="Vừa")
        self.karaoke_video_effect_var = tk.StringVar(value="Fade cinematic")
        self.karaoke_outro_var = tk.StringVar(value="3")
        self.karaoke_outro_line1_var = tk.StringVar(value="Thanks for watching!")
        self.karaoke_outro_line2_var = tk.StringVar(value="See you next time")
        self.karaoke_watermark_enabled_var = tk.BooleanVar(value=True)
        self.karaoke_watermark_text_var = tk.StringVar(value="YOUR CHANNEL")
        self.karaoke_watermark_position_var = tk.StringVar(value="Dưới phải")
        self.karaoke_watermark_opacity_var = tk.DoubleVar(value=65.0)
        self.karaoke_mute_original_var = tk.BooleanVar(value=False)
        self.karaoke_original_volume_var = tk.DoubleVar(value=0.45)
        self.karaoke_remove_dialogue_var = tk.BooleanVar(value=False)
        self.karaoke_voice_var = tk.StringVar(value="")
        self.karaoke_voice_volume_var = tk.DoubleVar(value=1.0)
        self.karaoke_voice_start_var = tk.StringVar(value="0")
        self.karaoke_voice_priority_var = tk.BooleanVar(value=True)
        self.karaoke_music_var = tk.StringVar(value="")
        self.karaoke_sfx_preset_var = tk.StringVar(value="Ambient mềm (mặc định)")
        self.karaoke_sfx_var = tk.StringVar(value=str(ASSETS_DIR / KARAOKE_SFX_PRESETS["Ambient mềm (mặc định)"]))
        self.karaoke_music_volume_var = tk.DoubleVar(value=0.18)
        self.karaoke_sfx_volume_var = tk.DoubleVar(value=0.07)
        self.karaoke_progress_var = tk.StringVar(value="Chưa bắt đầu")
        self.karaoke_effect_desc_var = tk.StringVar(value=KARAOKE_EFFECTS[self.karaoke_effect_var.get()]["description"])
        self.karaoke_preview_image = None
        self.karaoke_preview_path = None
        # Reading Along Studio
        self.reading_topic_var = tk.StringVar(value="Daily life")
        self.reading_language_var = tk.StringVar(value="English")
        self.reading_level_var = tk.StringVar(value="A1")
        self.reading_book_color_var = tk.StringVar(value="Sunny Yellow")
        self.reading_illustration_style_var = tk.StringVar(value="2.5D - Minh họa nổi khối")
        self.reading_title_var = tk.StringVar(value="A Simple Morning Routine")
        self.reading_audio_var = tk.StringVar(value="")
        self.reading_output_var = tk.StringVar(value=str(OUTPUT_DIR / "reading_along.mp4"))
        self.reading_whisper_var = tk.BooleanVar(value=True)
        self.reading_speech_speed_var = tk.StringVar(value="1.0x - Bình thường")
        self.reading_video_speed_var = tk.StringVar(value="1.0x - Bình thường")
        self.reading_speed_summary_var = tk.StringVar(value="Tốc độ tổng: 1.00x")
        self.reading_progress_var = tk.StringVar(value="Chưa bắt đầu")
        self.reading_preview_image = None
        self.reading_source_url_var = tk.StringVar(value="https://english-practice.net/english-reading-exercises-for-beginner/")
        self.reading_web_selection_var = tk.StringVar(value="")
        self.reading_web_items: list[dict[str, str]] = []
        self.reading_web_worker: Optional[threading.Thread] = None
        self._style()
        self.merge_mode_var = tk.StringVar(value="Batch – ghép theo tên file")
        self.merge_video_var = tk.StringVar()
        self.merge_audio_var = tk.StringVar()
        self.merge_video_dir_var = tk.StringVar()
        self.merge_audio_dir_var = tk.StringVar()
        self.merge_output_dir_var = tk.StringVar(value=str(OUTPUT_DIR / "merged"))
        self.merge_outro_seconds_var = tk.StringVar(value="3")
        self.merge_outro_line1_var = tk.StringVar(value="Thanks for watching!")
        self.merge_outro_line2_var = tk.StringVar(value="See you next time")
        self.merge_watermark_enabled_var = tk.BooleanVar(value=True)
        self.merge_watermark_text_var = tk.StringVar(value="YOUR CHANNEL")
        self.merge_watermark_position_var = tk.StringVar(value="Dưới phải")
        self.merge_watermark_opacity_var = tk.DoubleVar(value=65.0)
        self.merge_progress_var = tk.StringVar(value="Chưa bắt đầu")
        self._build_ui()
        self.root.after(150, self._poll)

    def _style(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("TNotebook", background="#0d1625", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1d2a3d", foreground="#e5eefb", padding=(15, 9), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "white")])
        style.configure("Treeview", background="#111d2e", foreground="#e5eefb", fieldbackground="#111d2e", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background="#25364d", foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1d4ed8")])
        style.configure("Horizontal.TProgressbar", background="#38bdf8", troughcolor="#172235", bordercolor="#172235")

    def _create_scrollable_tab(self, master):
        """Create a tab that only shows a scrollbar and scrolls when content exceeds viewport."""
        outer = tk.Frame(master, bg="#0d1625")
        canvas = tk.Canvas(outer, bg="#0d1625", bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        content = tk.Frame(canvas, bg="#0d1625")
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        state = {"shown": False, "syncing": False}
        def update_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            bbox = canvas.bbox("all")
            needs = bool(bbox and bbox[3]-bbox[1] > canvas.winfo_height()+3)
            if needs and not state["shown"]:
                scrollbar.pack(side="right", fill="y")
                state["shown"] = True
            elif not needs and state["shown"]:
                scrollbar.pack_forget()
                state["shown"] = False
            if not needs:
                canvas.yview_moveto(0)

        def sync_content_window(_event=None):
            """Stretch short tab content to the viewport; preserve natural height when it overflows."""
            if state["syncing"]:
                return
            state["syncing"] = True
            try:
                viewport_w = max(1, canvas.winfo_width())
                viewport_h = max(1, canvas.winfo_height())
                requested_h = max(1, content.winfo_reqheight())
                target_h = max(viewport_h, requested_h)
                current = canvas.coords(window_id)
                current_w = canvas.itemcget(window_id, "width")
                current_h = canvas.itemcget(window_id, "height")
                if not current or abs(float(current_w or 0)-viewport_w) > 1 or abs(float(current_h or 0)-target_h) > 1:
                    canvas.itemconfigure(window_id, width=viewport_w, height=target_h)
                canvas.configure(scrollregion=canvas.bbox("all"))
                update_scroll()
            finally:
                state["syncing"] = False

        content.bind("<Configure>", sync_content_window)
        canvas.bind("<Configure>", sync_content_window)
        canvas.after_idle(sync_content_window)
        outer._evs_scroll_state = state
        return outer, content, canvas

    def _install_mousewheel_scrolling(self):
        """Install a wheel handler before widget-class bindings, so every tab scrolls naturally."""
        self.root.bind_class("EVSMouseWheel", "<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind_class("EVSMouseWheel", "<Button-4>", self._on_mousewheel, add="+")
        self.root.bind_class("EVSMouseWheel", "<Button-5>", self._on_mousewheel, add="+")
        for outer in self._tab_outer_frames:
            stack = [outer]
            while stack:
                widget = stack.pop()
                try:
                    tags = widget.bindtags()
                    if "EVSMouseWheel" not in tags:
                        widget.bindtags((tags[0], "EVSMouseWheel", *tags[1:]))
                    stack.extend(widget.winfo_children())
                except Exception:
                    continue

    def _on_mousewheel(self, event):
        """Scroll the nearest overflowing text/tree/canvas; otherwise scroll the active tab."""
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = -int(delta/120*3) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        if not units:
            return "break"
        widget = getattr(event, "widget", None)
        current = widget
        while current is not None and current is not self.root:
            try:
                if isinstance(current, (tk.Text, tk.Listbox, ttk.Treeview)):
                    first, last = current.yview()
                    can_scroll = (units < 0 and first > 0.001) or (units > 0 and last < 0.999)
                    if can_scroll:
                        current.yview_scroll(units, "units")
                        return "break"
                elif isinstance(current, tk.Canvas):
                    bbox = current.bbox("all")
                    first, last = current.yview()
                    can_scroll = bbox and ((units < 0 and first > 0.001) or (units > 0 and last < 0.999))
                    if can_scroll:
                        current.yview_scroll(units, "units")
                        return "break"
                current = current.master
            except Exception:
                try:
                    current = current.master
                except Exception:
                    break
        try:
            selected = self.tabs.select()
            for outer, canvas in self._tab_scroll_map:
                if str(outer) == selected:
                    bbox = canvas.bbox("all")
                    if bbox and bbox[3]-bbox[1] > canvas.winfo_height()+3:
                        first, last = canvas.yview()
                        can_scroll = (units < 0 and first > 0.001) or (units > 0 and last < 0.999)
                        if can_scroll:
                            canvas.yview_scroll(units, "units")
                            return "break"
        except Exception:
            pass
        return None

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#101e32", padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="EDUCATIONAL AUDIO VIDEO STUDIO 1.19", bg="#101e32", fg="#f8fafc", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(header, text="Audio + Text + Storyboard JSON  →  Vector illustrations + structured text + purple karaoke + MP4", bg="#101e32", fg="#9fb2cc", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=10)
        self.main_tab_outer, self.main_tab, self.main_tab_canvas = self._create_scrollable_tab(self.tabs)
        self.scenes_tab_outer, self.scenes_tab, self.scenes_tab_canvas = self._create_scrollable_tab(self.tabs)
        self.assets_tab_outer, self.assets_tab, self.assets_tab_canvas = self._create_scrollable_tab(self.tabs)
        self.karaoke_tab_outer, self.karaoke_tab, self.karaoke_tab_canvas = self._create_scrollable_tab(self.tabs)
        self.reading_tab_outer, self.reading_tab, self.reading_tab_canvas = self._create_scrollable_tab(self.tabs)
        self.merge_tab_outer, self.merge_tab, self.merge_tab_canvas = self._create_scrollable_tab(self.tabs)
        self._tab_outer_frames = [self.main_tab_outer, self.scenes_tab_outer, self.assets_tab_outer,
                                  self.karaoke_tab_outer, self.reading_tab_outer, self.merge_tab_outer]
        self._tab_scroll_map = [(outer, canvas) for outer, canvas in (
            (self.main_tab_outer, self.main_tab_canvas), (self.scenes_tab_outer, self.scenes_tab_canvas),
            (self.assets_tab_outer, self.assets_tab_canvas), (self.karaoke_tab_outer, self.karaoke_tab_canvas),
            (self.reading_tab_outer, self.reading_tab_canvas))]
        self.tabs.add(self.main_tab_outer, text="Project")
        self.tabs.add(self.scenes_tab_outer, text="Storyboard / Scenes")
        self.tabs.add(self.assets_tab_outer, text="Assets")
        self.tabs.add(self.karaoke_tab_outer, text="Add Karaoke Sub")
        self.tabs.add(self.reading_tab_outer, text="Reading Along Studio")
        self.tabs.add(self.merge_tab_outer, text="Merge Video + Audio")

        self._build_project_tab()
        self._build_scenes_tab()
        self._build_assets_tab()
        self._build_karaoke_tab()
        self._build_reading_tab()
        self._build_merge_tab()
        self._build_footer()
        self._install_mousewheel_scrolling()

    def _label(self, parent, text, color="#cfe0f5", size=9, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=("Segoe UI", size, "bold" if bold else "normal"))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=("#0876c9" if primary else "#263850"), fg="white", activebackground=("#0b88df" if primary else "#3b526f"), activeforeground="white", relief="flat", font=("Segoe UI", 9, "bold" if primary else "normal"), padx=12, pady=7, cursor="hand2")

    def _entry_row(self, parent, label, variable, browse_cmd):
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", pady=4)
        self._label(row, label, size=9, bold=True).pack(anchor="w")
        line = tk.Frame(row, bg=parent.cget("bg")); line.pack(fill="x", pady=(3, 0))
        entry = tk.Entry(line, textvariable=variable, bg="#18263a", fg="#f8fafc", insertbackground="white", relief="flat", font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self._button(line, "Chọn...", browse_cmd).pack(side="right")
        return entry

    def _build_project_tab(self):
        main = self.main_tab
        left = tk.Frame(main, bg="#0d1625", padx=16, pady=14)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(main, bg="#101e32", padx=14, pady=14, width=350)
        right.pack(side="right", fill="y", padx=(0, 12), pady=12)
        right.pack_propagate(False)

        self._label(left, "1. INPUT FILES", "#7dd3fc", 10, True).pack(anchor="w", pady=(0, 5))
        self._entry_row(left, "Audio file (MP3 / WAV / M4A / FLAC)", self.audio_var, self._pick_audio)
        self._entry_row(left, "Transcript / Subtitle (TXT, MD, SRT, VTT, ASS, SSA, SBV, LRC...)", self.text_var, self._pick_text)
        self._entry_row(left, "Storyboard JSON (schema v1.3 – media optional + vector fallback)", self.json_var, self._pick_json)

        info = tk.Frame(left, bg="#14243a", padx=12, pady=10)
        info.pack(fill="x", pady=(12, 12))
        self._label(info, "ĐỊNH DẠNG CHUẨN", "#67e8f9", 9, True).pack(anchor="w")
        tk.Label(info, text="AI phải trả về JSON schema v1.3. Media URL là tùy chọn; visual_fallback dùng pictogram semantic và bố cục panel/card theo preset. App tự kiểm soát va chạm giữa hình và chữ khi render.", bg="#14243a", fg="#c8d8ea", justify="left", wraplength=750, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        action = tk.Frame(left, bg="#0d1625")
        action.pack(fill="x", pady=6)
        self._button(action, "Mở prompt template", self._open_prompt).pack(side="left", padx=(0, 6))
        self._button(action, "Tạo prompt từ transcript", self._export_prompt).pack(side="left", padx=6)
        self._button(action, "Copy schema", self._copy_schema).pack(side="left", padx=6)

        self._label(left, "2. ILLUSTRATION COMPOSITION", "#7dd3fc", 10, True).pack(anchor="w", pady=(14, 5))
        composition_row = tk.Frame(left, bg="#0d1625")
        composition_row.pack(fill="x", pady=(0, 3))
        composition_values = list(VISUAL_COMPOSITION_PRESETS.keys())
        ttk.Combobox(composition_row, textvariable=self.composition_var, state="readonly", width=34,
                     values=composition_values).pack(side="left", padx=(0, 8))
        self._button(composition_row, "🎲 Random phối hình", self._random_composition, primary=True).pack(side="left")
        tk.Label(left, textvariable=self.composition_desc_var, bg="#0d1625", fg="#9fb2cc",
                 justify="left", wraplength=760, font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 1))
        tk.Label(left, text="Preset này được chèn vào prompt tạo storyboard mới; không tự sửa JSON đã tải.",
                 bg="#0d1625", fg="#64748b", justify="left", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 2))
        self.composition_var.trace_add("write", lambda *_: self._update_composition_description())

        self._label(left, "3. VIDEO OUTPUT", "#7dd3fc", 10, True).pack(anchor="w", pady=(16, 5))
        row = tk.Frame(left, bg="#0d1625"); row.pack(fill="x", pady=4)
        self._label(row, "Resolution:").pack(side="left")
        ttk.Combobox(row, textvariable=self.resolution_var, state="readonly", width=25,
                     values=["720x1280 (khuyên dùng)", "1080x1920 (Full HD)", "1920x1080 (Landscape)", "1080x1080 (Square)"]).pack(side="left", padx=8)
        self._label(row, "FPS:").pack(side="left", padx=(15, 0))
        ttk.Combobox(row, textvariable=self.fps_var, state="readonly", width=5, values=[24, 25, 30]).pack(side="left", padx=8)
        self._entry_row(left, "Output MP4", self.output_var, self._pick_output)
        tk.Checkbutton(left, text="Hiển thị phụ đề dưới màn hình (karaoke highlight từng từ sau ALIGN AUDIO)",
                       variable=self.subtitles_var, bg="#0d1625", fg="#e5edf7", selectcolor="#1f2937",
                       activebackground="#0d1625", activeforeground="white", font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        actions = tk.Frame(left, bg="#0d1625"); actions.pack(fill="x", pady=(13, 5))
        self.validate_btn = self._button(actions, "VALIDATE JSON", self._validate_current, primary=False)
        self.validate_btn.pack(side="left", padx=(0, 7))
        self.align_btn = self._button(actions, "ALIGN AUDIO (tùy chọn – Render tự căn nếu thiếu)", self._start_alignment)
        self.align_btn.pack(side="left", padx=7)
        self.render_btn = self._button(actions, "RENDER VIDEO", self._start_render, primary=True)
        self.render_btn.pack(side="left", padx=7)
        self.cancel_btn = self._button(actions, "Hủy", self._cancel)
        self.cancel_btn.pack(side="left", padx=7)

        tk.Label(right, text="PROJECT STATUS", bg="#101e32", fg="#7dd3fc", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(right, textvariable=self.project_status_var, bg="#101e32", fg="#e2e8f0", font=("Segoe UI", 10), wraplength=300, justify="left").pack(anchor="w", pady=(6, 12))
        tk.Label(right, text="ĐIỀU QUAN TRỌNG", bg="#101e32", fg="#7dd3fc", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        notes = (
            "• JSON có timestamp thô từ script, không phải timing từng từ.\n\n"
            "• Có thể dùng mốc script để render ngay.\n\n"
            "• ALIGN AUDIO dùng faster-whisper word timestamps rồi đối chiếu với source text; đây là căn chỉnh xấp xỉ theo mức độ khớp ASR, không cam kết chính xác tuyệt đối.\n\n"
            "• Phụ đề dưới màn hình được lấy từ lời nhận dạng; sau ALIGN AUDIO, từng từ sẽ được highlight theo timestamp. Nếu chưa ALIGN, app hiển thị phụ đề theo từng source segment, chưa có karaoke từng từ.\n\n"
            "• JSON v1.3 cho phép media tùy chọn; mỗi cảnh phải có visual_fallback để dựng icon vector và sơ đồ nếu thiếu ảnh/video.\n\n"
            "• Khi tải JSON, app có thể tải toàn bộ media vào thư mục <tên JSON>_assets.\n\n"
            "• Nếu tải được media, app đặt ảnh/video lên visual_fallback. Nếu không có hoặc media lỗi, pictogram semantic trong JSON vẫn render bình thường.\n\n"
            "• Phụ đề karaoke nằm cố định ở vùng dưới video; khi chưa có word timestamps, Render sẽ tự chạy Whisper nếu đã cài alignment."
        )
        tk.Label(right, text=notes, bg="#101e32", fg="#b9c9dc", font=("Segoe UI", 9), justify="left", wraplength=300).pack(anchor="w", pady=(6, 14))
        self._button(right, "Mở thư mục output", lambda: os.startfile(OUTPUT_DIR) if os.name == "nt" else webbrowser.open(OUTPUT_DIR.as_uri())).pack(fill="x", pady=3)
        self._button(right, "Mở thư mục ứng dụng", lambda: os.startfile(APP_DIR) if os.name == "nt" else webbrowser.open(APP_DIR.as_uri())).pack(fill="x", pady=3)

    def _build_scenes_tab(self):
        tab = self.scenes_tab
        left = tk.Frame(tab, bg="#0d1625", padx=12, pady=12, width=360)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        right = tk.Frame(tab, bg="#101e32", padx=14, pady=12)
        right.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)
        self._label(left, "SCENE LIST", "#7dd3fc", 10, True).pack(anchor="w", pady=(0, 8))
        self.scene_tree = ttk.Treeview(left, columns=("time", "type"), show="tree headings", height=24)
        self.scene_tree.heading("#0", text="Scene")
        self.scene_tree.heading("time", text="Time")
        self.scene_tree.heading("type", text="Type")
        self.scene_tree.column("#0", width=120)
        self.scene_tree.column("time", width=100)
        self.scene_tree.column("type", width=110)
        self.scene_tree.pack(fill="both", expand=True)
        self.scene_tree.bind("<<TreeviewSelect>>", self._on_scene_select)
        self._label(right, "SCENE DETAILS", "#7dd3fc", 10, True).pack(anchor="w")
        self.scene_title = tk.Label(right, text="Chưa tải storyboard", bg="#101e32", fg="white", font=("Segoe UI", 14, "bold"), anchor="w")
        self.scene_title.pack(fill="x", pady=(8, 4))
        self.scene_meta = tk.Label(right, text="", bg="#101e32", fg="#94a3b8", font=("Segoe UI", 9), anchor="w")
        self.scene_meta.pack(fill="x", pady=(0, 10))
        self.scene_text = tk.Text(right, bg="#0b1524", fg="#e2e8f0", insertbackground="white", relief="flat", wrap="word", font=("Segoe UI", 10), height=12)
        self.scene_text.pack(fill="both", expand=True)
        self.scene_text.configure(state="disabled")
        self._button(right, "Refresh scene list", self._populate_scenes).pack(anchor="e", pady=8)

    def _build_assets_tab(self):
        tab = self.assets_tab
        outer = tk.Frame(tab, bg="#0d1625", padx=14, pady=14)
        outer.pack(fill="both", expand=True)
        self._label(outer, "MEDIA TÙY CHỌN TỪ DIRECT URL TRONG JSON", "#7dd3fc", 10, True).pack(anchor="w", pady=(0, 6))
        self.asset_tree = ttk.Treeview(outer, columns=("type", "provider", "description", "url", "path"), show="tree headings", height=13)
        for col, label, width in [("#0", "Asset ID", 130), ("type", "Type", 70), ("provider", "Provider", 105), ("description", "Description", 230), ("url", "Direct media URL (preview)", 300), ("path", "Downloaded file", 190)]:
            self.asset_tree.heading(col, text=label)
            self.asset_tree.column(col, width=width, stretch=(col in ("description", "url", "path")))
        self.asset_tree.pack(fill="both", expand=True)
        self.asset_tree.bind("<<TreeviewSelect>>", self._show_asset_details)

        # Dedicated live download progress: one bar for the current file, plus the
        # footer bar which tracks the entire asset queue (and is also used by render).
        progress_box = tk.Frame(outer, bg="#101e32", padx=10, pady=8)
        progress_box.pack(fill="x", pady=(9, 5))
        tk.Label(progress_box, text="TIẾN ĐỘ FILE ĐANG TẢI", bg="#101e32", fg="#93c5fd",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.asset_file_progress = ttk.Progressbar(progress_box, mode="determinate", maximum=100)
        self.asset_file_progress.pack(fill="x", pady=(4, 3))
        tk.Label(progress_box, textvariable=self.asset_progress_var, bg="#101e32", fg="#dbeafe",
                 anchor="w", font=("Segoe UI", 9)).pack(fill="x")

        # Full URL fields are separate from the narrow table preview, so long signed
        # CDN URLs (including query strings) can be inspected and copied without loss.
        url_box = tk.Frame(outer, bg="#101e32", padx=10, pady=8)
        url_box.pack(fill="x", pady=(5, 5))
        tk.Label(url_box, text="DIRECT MEDIA URL – ĐẦY ĐỦ", bg="#101e32", fg="#93c5fd",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        direct_line = tk.Frame(url_box, bg="#101e32"); direct_line.pack(fill="x", pady=(4, 5))
        self.asset_direct_entry = tk.Entry(direct_line, textvariable=self.asset_direct_url_var,
                                           bg="#18263a", fg="#f8fafc", insertbackground="white",
                                           relief="flat", font=("Segoe UI", 8), state="readonly")
        self.asset_direct_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._button(direct_line, "Copy full URL", self._copy_asset_direct_url).pack(side="left", padx=(8, 0))
        self._button(direct_line, "Mở direct URL", self._open_asset_direct_url).pack(side="left", padx=(6, 0))

        tk.Label(url_box, text="SOURCE PAGE URL", bg="#101e32", fg="#93c5fd",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 0))
        source_line = tk.Frame(url_box, bg="#101e32"); source_line.pack(fill="x", pady=(4, 0))
        self.asset_source_entry = tk.Entry(source_line, textvariable=self.asset_source_url_var,
                                           bg="#18263a", fg="#cbd5e1", insertbackground="white",
                                           relief="flat", font=("Segoe UI", 8), state="readonly")
        self.asset_source_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._button(source_line, "Copy source URL", self._copy_asset_source_url).pack(side="left", padx=(8, 0))
        self._button(source_line, "Mở trang nguồn", self._open_asset_source).pack(side="left", padx=(6, 0))

        actions = tk.Frame(outer, bg="#0d1625"); actions.pack(fill="x", pady=8)
        self.download_btn = self._button(actions, "TẢI + KIỂM TRA TẤT CẢ MEDIA TỪ JSON", self._start_download_assets, primary=True)
        self.download_btn.pack(side="left", padx=(0, 8))
        self._button(actions, "Xem media đã tải", self._open_local_asset).pack(side="left", padx=8)
        self._button(actions, "Gán file thủ công", self._assign_asset).pack(side="left", padx=8)
        self._button(actions, "Bỏ gán", self._clear_asset).pack(side="left", padx=8)
        note = ("Direct media URL phải là URL đầy đủ trỏ thẳng tới file ảnh/video; source page URL chỉ dùng để mở trang gốc/đọc attribution. "
                "App hiển thị toàn bộ URL ở hai ô trên và có nút copy, không lấy URL rút gọn trong bảng làm đường tải. "
                "Nếu URL lỗi hoặc không có media, app tự dựng icon vector từ visual_fallback trong JSON.")
        tk.Label(outer, text=note, bg="#0d1625", fg="#9fb2cc", font=("Segoe UI", 9), wraplength=1100, justify="left").pack(anchor="w")

    def _build_karaoke_tab(self):
        tab = self.karaoke_tab
        left_outer = tk.Frame(tab, bg="#0d1625")
        left_outer.pack(side="left", fill="both", expand=True)
        left_canvas = tk.Canvas(left_outer, bg="#0d1625", highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_outer, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_scroll.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        left = tk.Frame(left_canvas, bg="#0d1625", padx=18, pady=16)
        left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>", lambda _e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfigure(left_window, width=e.width))
        right = tk.Frame(tab, bg="#101e32", padx=16, pady=16, width=360)
        right.pack(side="right", fill="y", padx=(0, 12), pady=12)
        right.pack_propagate(False)

        self._label(left, "ADD KARAOKE SUBTITLE", "#7dd3fc", 11, True).pack(anchor="w", pady=(0, 8))
        tk.Label(left, text="Burn phụ đề karaoke vào một video có sẵn. Không cần storyboard JSON hoặc audio riêng.",
                 bg="#0d1625", fg="#9fb2cc", font=("Segoe UI", 9), wraplength=760,
                 justify="left").pack(anchor="w", pady=(0, 12))

        self._entry_row(left, "1. Video đầu vào", self.karaoke_video_var, self._pick_karaoke_video)
        self._entry_row(left, "2. Subtitle có timestamp (SRT / VTT / ASS / SSA / SBV / LRC)",
                        self.karaoke_subtitle_var, self._pick_karaoke_subtitle)
        self._entry_row(left, "3. Video đầu ra", self.karaoke_output_var, self._pick_karaoke_output)

        self._label(left, "4. KARAOKE EFFECT", "#7dd3fc", 10, True).pack(anchor="w", pady=(18, 5))
        effects = ttk.Combobox(left, textvariable=self.karaoke_effect_var, state="readonly", width=48,
                               values=list(KARAOKE_EFFECTS.keys()))
        effects.pack(anchor="w", fill="x", pady=(0, 3))
        effects.bind("<<ComboboxSelected>>", lambda _e: self._update_karaoke_effect_desc())
        tk.Label(left, textvariable=self.karaoke_effect_desc_var, bg="#0d1625", fg="#9fb2cc",
                 font=("Segoe UI", 9), wraplength=760, justify="left").pack(anchor="w", pady=(3, 8))

        opts = tk.Frame(left, bg="#0d1625")
        opts.pack(fill="x", pady=(4, 8))
        self._label(opts, "Vị trí:").pack(side="left")
        ttk.Combobox(opts, textvariable=self.karaoke_position_var, state="readonly", width=12,
                     values=["Dưới", "Giữa", "Trên"]).pack(side="left", padx=(6, 18))
        self._label(opts, "Cỡ chữ:").pack(side="left")
        ttk.Combobox(opts, textvariable=self.karaoke_size_var, state="readonly", width=10,
                     values=["Nhỏ", "Vừa", "Lớn"]).pack(side="left", padx=6)

        # Video treatment, outro and audio mix controls
        self._label(left, "5. VIDEO EFFECTS / CUSTOM OUTRO / WATERMARK", "#7dd3fc", 10, True).pack(anchor="w", pady=(14, 5))
        vrow = tk.Frame(left, bg="#0d1625"); vrow.pack(fill="x", pady=3)
        self._label(vrow, "Hiệu ứng video:").pack(side="left")
        ttk.Combobox(vrow, textvariable=self.karaoke_video_effect_var, state="readonly", width=27,
                     values=["Fade cinematic", "Slow zoom + fade", "Soft vignette + fade", "Warm film + fade", "Cool tech + fade"]).pack(side="left", padx=7)
        self._label(vrow, "Outro (giây):").pack(side="left", padx=(12, 4))
        ttk.Combobox(vrow, textvariable=self.karaoke_outro_var, state="readonly", width=5,
                     values=["0", "2", "3", "4", "5", "6"]).pack(side="left")
        self._entry_row(left, "Outro dòng 1", self.karaoke_outro_line1_var, lambda: None)
        self._entry_row(left, "Outro dòng 2", self.karaoke_outro_line2_var, lambda: None)
        tk.Label(left, text="Có thể sửa riêng từng dòng hoặc xóa nội dung dòng không dùng. Đặt Outro = 0 để không hiện chữ kết thúc.",
                 bg="#0d1625", fg="#94a3b8", font=("Segoe UI", 8), wraplength=760, justify="left").pack(anchor="w", pady=(0, 5))

        self._label(left, "WATERMARK – HIỂN THỊ XUYÊN SUỐT VIDEO", "#7dd3fc", 9, True).pack(anchor="w", pady=(8, 3))
        tk.Checkbutton(left, text="Bật watermark", variable=self.karaoke_watermark_enabled_var,
                       bg="#0d1625", fg="#e5eefb", selectcolor="#1d2a3d", activebackground="#0d1625",
                       activeforeground="#ffffff").pack(anchor="w")
        self._entry_row(left, "Nội dung watermark (tên kênh / logo dạng chữ)", self.karaoke_watermark_text_var, lambda: None)
        wrow = tk.Frame(left, bg="#0d1625"); wrow.pack(fill="x", pady=2)
        self._label(wrow, "Vị trí:").pack(side="left")
        ttk.Combobox(wrow, textvariable=self.karaoke_watermark_position_var, state="readonly", width=12,
                     values=["Trên trái", "Trên phải", "Dưới trái", "Dưới phải"]).pack(side="left", padx=(6, 18))
        self._label(wrow, "Độ mờ / Opacity:").pack(side="left")
        ttk.Scale(wrow, from_=15, to=100, variable=self.karaoke_watermark_opacity_var,
                  orient="horizontal", length=180).pack(side="left", padx=8)
        self._label(wrow, "15–100%", color="#94a3b8").pack(side="left")
        tk.Label(left, text="Watermark dạng chữ nhỏ, cố định tại một góc và xuất hiện từ đầu đến hết video. Muốn tắt, bỏ chọn Bật watermark.",
                 bg="#0d1625", fg="#94a3b8", font=("Segoe UI", 8), wraplength=760, justify="left").pack(anchor="w", pady=(2, 5))

        tk.Label(left, text="Hiệu ứng áp dụng lên toàn video và fade cuối. Chuyển cảnh giữa các shot chỉ thực hiện được khi có mốc cắt/scene riêng; app không tự đoán điểm cắt.",
                 bg="#0d1625", fg="#94a3b8", font=("Segoe UI", 8), wraplength=760, justify="left").pack(anchor="w", pady=(2, 5))

        self._label(left, "6. AUDIO MIX / ÂM THANH", "#7dd3fc", 10, True).pack(anchor="w", pady=(12, 5))
        self._entry_row(left, "Giọng đọc / TTS của bạn (ưu tiên cao nhất)", self.karaoke_voice_var, self._pick_karaoke_voice)
        vvoice = tk.Frame(left, bg="#0d1625"); vvoice.pack(fill="x", pady=2)
        self._label(vvoice, "Volume voice: ").pack(side="left")
        ttk.Scale(vvoice, from_=0.0, to=1.5, variable=self.karaoke_voice_volume_var, orient="horizontal", length=180).pack(side="left", padx=8)
        self._label(vvoice, "Bắt đầu tại (giây):").pack(side="left", padx=(12, 4))
        ttk.Entry(vvoice, textvariable=self.karaoke_voice_start_var, width=7).pack(side="left")
        tk.Checkbutton(left, text="Ưu tiên voiceover: tự động hạ audio gốc / nhạc / SFX khi đang có lời đọc",
                       variable=self.karaoke_voice_priority_var, bg="#0d1625", fg="#e5eefb", selectcolor="#1d2a3d",
                       activebackground="#0d1625", activeforeground="#ffffff").pack(anchor="w", pady=(2, 4))
        tk.Label(left, text="Voiceover là track thuyết minh chính. Khi giọng đọc xuất hiện, các âm thanh nền sẽ tự giảm âm lượng (ducking) để lời đọc luôn nổi bật.",
                 bg="#14243a", fg="#a8d9ff", font=("Segoe UI", 8), wraplength=760, justify="left", padx=10, pady=6).pack(fill="x", pady=(0, 5))
        tk.Checkbutton(left, text="Xóa / tắt hoàn toàn audio gốc", variable=self.karaoke_mute_original_var,
                       bg="#0d1625", fg="#e5eefb", selectcolor="#1d2a3d", activebackground="#0d1625",
                       activeforeground="#ffffff").pack(anchor="w")
        arow = tk.Frame(left, bg="#0d1625"); arow.pack(fill="x", pady=2)
        self._label(arow, "Volume audio gốc:").pack(side="left")
        ttk.Scale(arow, from_=0.0, to=1.0, variable=self.karaoke_original_volume_var, orient="horizontal", length=180).pack(side="left", padx=8)
        self._label(arow, "(0 = mute, 1 = 100%)", color="#94a3b8").pack(side="left")
        tk.Checkbutton(left, text="Thử giảm lời thoại gốc (center-cancel stereo; có thể ảnh hưởng nhạc nền)",
                       variable=self.karaoke_remove_dialogue_var, bg="#0d1625", fg="#e5eefb", selectcolor="#1d2a3d",
                       activebackground="#0d1625", activeforeground="#ffffff").pack(anchor="w", pady=(2, 4))
        self._entry_row(left, "Nhạc nền (tùy chọn)", self.karaoke_music_var, self._pick_karaoke_music)
        mrow = tk.Frame(left, bg="#0d1625"); mrow.pack(fill="x", pady=2)
        self._label(mrow, "Volume nhạc:").pack(side="left")
        ttk.Scale(mrow, from_=0.0, to=0.6, variable=self.karaoke_music_volume_var, orient="horizontal", length=180).pack(side="left", padx=8)
        sfxrow = tk.Frame(left, bg="#0d1625"); sfxrow.pack(fill="x", pady=(6, 2))
        self._label(sfxrow, "SFX tích hợp sẵn:").pack(side="left")
        sfx_combo = ttk.Combobox(sfxrow, textvariable=self.karaoke_sfx_preset_var, state="readonly", width=27,
                                 values=list(KARAOKE_SFX_PRESETS.keys()))
        sfx_combo.pack(side="left", padx=7)
        sfx_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_karaoke_sfx_preset())
        self._entry_row(left, "Ambient SFX / file hiệu ứng riêng", self.karaoke_sfx_var, self._pick_karaoke_sfx)
        srow = tk.Frame(left, bg="#0d1625"); srow.pack(fill="x", pady=2)
        self._label(srow, "Volume SFX:").pack(side="left")
        ttk.Scale(srow, from_=0.0, to=0.35, variable=self.karaoke_sfx_volume_var, orient="horizontal", length=180).pack(side="left", padx=8)
        tk.Label(left, text="SFX tích hợp là ambience nền nhẹ, đã được tạo riêng và có sẵn trong app. Muốn tắt, chọn ‘Tắt SFX’. ‘Giảm lời thoại’ audio gốc vẫn là xử lý thử nghiệm, không phải AI source separation.",
                 bg="#14243a", fg="#fcd9a6", font=("Segoe UI", 8), wraplength=760, justify="left", padx=10, pady=7).pack(fill="x", pady=(5, 8))

        note = tk.Frame(left, bg="#14243a", padx=12, pady=10)
        note.pack(fill="x", pady=(8, 12))
        tk.Label(note, text=("LƯU Ý VỀ TIMING\n"
                             "• Giữ nguyên thời điểm bắt đầu/kết thúc của từng cue trong phụ đề.\n"
                             "• Nếu file chỉ có timestamp theo cả câu, hiệu ứng tô từng từ sẽ chia đều thời lượng cue theo độ dài từ; đây là timing ước lượng, không phải forced alignment.\n"
                             "• Với phụ đề đã có karaoke timing, nên dùng ASS/VTT tương ứng hoặc căn timestamp từng từ trước khi xuất."),
                 bg="#14243a", fg="#c8d8ea", justify="left", wraplength=760,
                 font=("Segoe UI", 9)).pack(anchor="w")

        buttons = tk.Frame(left, bg="#0d1625")
        buttons.pack(fill="x", pady=(8, 0))
        self.karaoke_preview_btn = self._button(buttons, "Xem preview effect", self._start_karaoke_preview)
        self.karaoke_preview_btn.pack(side="left", padx=(0, 8))
        self.karaoke_export_btn = self._button(buttons, "ADD KARAOKE + EXPORT MP4", self._start_karaoke_export, primary=True)
        self.karaoke_export_btn.pack(side="left", padx=8)
        self.karaoke_progress = ttk.Progressbar(left, mode="determinate", maximum=100)
        self.karaoke_progress.pack(fill="x", pady=(12, 2))
        tk.Label(left, textvariable=self.karaoke_progress_var, bg="#0d1625", fg="#9fb2cc",
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")

        tk.Label(right, text="EFFECT PREVIEW", bg="#101e32", fg="#7dd3fc",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.karaoke_preview_label = tk.Label(right, text="Chọn video + subtitle rồi bấm\nXem preview effect.",
                                              bg="#0b1524", fg="#94a3b8", font=("Segoe UI", 10),
                                              justify="center", relief="flat")
        self.karaoke_preview_label.pack(fill="both", expand=True, pady=(10, 8))
        tk.Label(right, text="Preview lấy một frame tại cue đầu tiên để kiểm tra font, vị trí và effect. Video xuất cuối cùng được render toàn bộ bằng FFmpeg/libass.",
                 bg="#101e32", fg="#94a3b8", font=("Segoe UI", 8), wraplength=320,
                 justify="left").pack(anchor="w")

    def _pick_karaoke_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mpeg *.mpg"), ("All files", "*.*")])
        if p:
            self.karaoke_video_var.set(p)
            video = Path(p)
            self.karaoke_output_var.set(str(video.with_name(video.stem + "_karaoke.mp4")))
            self.karaoke_preview_label.configure(text="Đã chọn video. Chọn file subtitle để xem preview.", image="")
            self.karaoke_preview_image = None

    def _pick_karaoke_subtitle(self):
        p = filedialog.askopenfilename(filetypes=[
            ("Timestamped subtitles", "*.srt *.vtt *.ass *.ssa *.sbv *.lrc"),
            ("All files", "*.*")])
        if p:
            self.karaoke_subtitle_var.set(p)
            if not self.karaoke_video_var.get():
                self.karaoke_output_var.set(str(Path(p).with_name(Path(p).stem + "_karaoke.mp4")))

    def _pick_karaoke_voice(self):
        p = filedialog.askopenfilename(filetypes=[("Voiceover / TTS audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma"), ("All files", "*.*")])
        if p: self.karaoke_voice_var.set(p)

    def _update_karaoke_sfx_preset(self):
        name = self.karaoke_sfx_preset_var.get()
        filename = KARAOKE_SFX_PRESETS.get(name)
        if filename:
            path = ASSETS_DIR / filename
            if path.exists():
                self.karaoke_sfx_var.set(str(path))
            else:
                messagebox.showwarning("Thiếu SFX tích hợp", f"Không tìm thấy preset: {path}")
        elif name == "Tắt SFX":
            self.karaoke_sfx_var.set("")

    def _pick_karaoke_music(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"), ("All files", "*.*")])
        if p: self.karaoke_music_var.set(p)

    def _pick_karaoke_sfx(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"), ("All files", "*.*")])
        if p:
            self.karaoke_sfx_var.set(p)
            self.karaoke_sfx_preset_var.set("File riêng")

    def _pick_karaoke_output(self):
        video = Path(self.karaoke_video_var.get()) if self.karaoke_video_var.get() else None
        initial = video.stem + "_karaoke.mp4" if video else "karaoke_output.mp4"
        p = filedialog.asksaveasfilename(defaultextension=".mp4", initialfile=initial,
                                         filetypes=[("MP4 video", "*.mp4")])
        if p:
            self.karaoke_output_var.set(p)

    def _update_karaoke_effect_desc(self):
        self.karaoke_effect_desc_var.set(KARAOKE_EFFECTS[self.karaoke_effect_var.get()]["description"])

    def _karaoke_inputs(self):
        video = Path(self.karaoke_video_var.get()) if self.karaoke_video_var.get() else None
        subtitle = Path(self.karaoke_subtitle_var.get()) if self.karaoke_subtitle_var.get() else None
        output = Path(self.karaoke_output_var.get()) if self.karaoke_output_var.get() else None
        if not video or not video.exists() or video.suffix.lower() not in VIDEO_EXTS:
            messagebox.showwarning("Thiếu video", "Chọn video đầu vào hợp lệ trước.")
            return None
        if not subtitle or not subtitle.exists():
            messagebox.showwarning("Thiếu subtitle", "Chọn file SRT/VTT/ASS/SSA/SBV/LRC có timestamp.")
            return None
        if not output:
            output = video.with_name(video.stem + "_karaoke.mp4")
            self.karaoke_output_var.set(str(output))
        if output.resolve() == video.resolve():
            messagebox.showwarning("Trùng file", "File đầu ra không được ghi đè video gốc.")
            return None
        try:
            cues = load_karaoke_cues(subtitle)
            if not cues:
                raise ValueError("File không có cue phụ đề.")
        except Exception as exc:
            messagebox.showerror("Subtitle không hợp lệ", str(exc))
            return None
        return video, subtitle, output, cues

    def _start_karaoke_preview(self):
        if self.worker and self.worker.is_alive():
            return
        inputs = self._karaoke_inputs()
        if not inputs:
            return
        video, subtitle, _output, cues = inputs
        self.cancel.clear()
        self._set_busy(True)
        self.karaoke_preview_btn.configure(state="disabled")
        self.karaoke_export_btn.configure(state="disabled")
        args = (video, cues, self.karaoke_effect_var.get(), self.karaoke_position_var.get(), self.karaoke_size_var.get())
        self.worker = threading.Thread(target=self._karaoke_preview_worker, args=args, daemon=True)
        self.worker.start()
        self.status_var.set("Đang tạo preview phụ đề...")

    def _karaoke_preview_worker(self, video: Path, cues, effect: str, position: str, size_name: str):
        ass_path = preview_path = None
        try:
            width, height = probe_video_size(video)
            cue = cues[0]
            preview_time = (cue[0] + cue[1]) / 2.0
            shift = -preview_time
            ass_path = OUTPUT_DIR / ("evs_karaoke_preview_" + str(os.getpid()) + ".ass")
            preview_path = OUTPUT_DIR / ("evs_karaoke_preview_" + str(os.getpid()) + ".png")
            ass = build_karaoke_ass(cues, width, height, effect, position, size_name, time_offset=shift)
            ass_path.write_text(ass, encoding="utf-8-sig")
            cmd = [ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{preview_time:.3f}",
                   "-i", str(video), "-vf", f"subtitles=filename={ass_path.name}", "-frames:v", "1", "-an", str(preview_path)]
            result = subprocess.run(cmd, cwd=str(OUTPUT_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=90, check=False)
            if result.returncode != 0 or not preview_path.exists():
                raise RuntimeError("Không tạo được preview: " + result.stderr.decode("utf-8", "replace")[-1600:])
            self.q.put(("karaoke_preview_done", str(preview_path)))
        except Exception as exc:
            self.q.put(("karaoke_preview_error", str(exc)))
        finally:
            if ass_path:
                ass_path.unlink(missing_ok=True)

    def _start_karaoke_export(self):
        if self.worker and self.worker.is_alive():
            return
        inputs = self._karaoke_inputs()
        if not inputs:
            return
        video, subtitle, output, cues = inputs
        if output.exists() and not messagebox.askyesno("Ghi đè video?", f"File đã tồn tại:\n{output}\n\nBạn có muốn ghi đè không?"):
            return
        voice = Path(self.karaoke_voice_var.get()) if self.karaoke_voice_var.get() else None
        music = Path(self.karaoke_music_var.get()) if self.karaoke_music_var.get() else None
        sfx = Path(self.karaoke_sfx_var.get()) if self.karaoke_sfx_var.get() else None
        for label, path in (("Giọng đọc / TTS", voice), ("Nhạc nền", music), ("Ambient SFX", sfx)):
            if path and not path.exists():
                messagebox.showwarning("Thiếu audio", f"Không tìm thấy file {label}:\n{path}")
                return
        try:
            voice_start = max(0.0, float(self.karaoke_voice_start_var.get() or 0))
        except ValueError:
            messagebox.showwarning("Sai thời điểm", "Bắt đầu voiceover phải là số giây, ví dụ 0 hoặc 2.5.")
            return
        self.cancel.clear()
        self._set_busy(True)
        self.karaoke_preview_btn.configure(state="disabled")
        self.karaoke_export_btn.configure(state="disabled")
        outro_lines = "\n".join([self.karaoke_outro_line1_var.get(), self.karaoke_outro_line2_var.get()]).strip()
        args = (video, subtitle, output, cues, self.karaoke_effect_var.get(),
                self.karaoke_position_var.get(), self.karaoke_size_var.get(),
                self.karaoke_video_effect_var.get(), float(self.karaoke_outro_var.get()),
                outro_lines, self.karaoke_watermark_enabled_var.get(), self.karaoke_watermark_text_var.get(),
                self.karaoke_watermark_position_var.get(), float(self.karaoke_watermark_opacity_var.get()),
                self.karaoke_mute_original_var.get(), float(self.karaoke_original_volume_var.get()),
                self.karaoke_remove_dialogue_var.get(), music, sfx,
                float(self.karaoke_music_volume_var.get()), float(self.karaoke_sfx_volume_var.get()),
                voice, float(self.karaoke_voice_volume_var.get()), voice_start,
                self.karaoke_voice_priority_var.get())
        self.karaoke_progress.configure(value=0); self.karaoke_progress_var.set("Đang chuẩn bị render...")
        self.worker = threading.Thread(target=self._karaoke_export_worker, args=args, daemon=True)
        self.worker.start()
        self.status_var.set("Đang burn karaoke subtitle vào video...")

    def _karaoke_export_worker(self, video: Path, subtitle: Path, output: Path, cues,
                               effect: str, position: str, size_name: str, video_effect: str,
                               outro_seconds: float, outro_text: str, watermark_enabled: bool,
                               watermark_text: str, watermark_position: str, watermark_opacity: float,
                               mute_original: bool, original_volume: float, remove_dialogue: bool,
                               music_path, sfx_path, music_volume: float, sfx_volume: float,
                               voice_path, voice_volume: float, voice_start: float,
                               voice_priority: bool):
        ass_path = None
        try:
            width, height = probe_video_size(video)
            output.parent.mkdir(parents=True, exist_ok=True)
            ass_path = output.parent / (".evs_karaoke_" + str(os.getpid()) + "_" + str(threading.get_ident()) + ".ass")
            ass = build_karaoke_ass(cues, width, height, effect, position, size_name)
            duration = probe_duration(video)
            if outro_seconds > 0 and outro_text.strip():
                outro_start = max(0.0, duration - outro_seconds)
                outro_end = max(outro_start + 0.1, duration)
                # Each user-editable line stays on its own displayed line.
                outro_safe = r"\N".join(_ass_safe_text(line.strip()) for line in outro_text.splitlines() if line.strip())
                if outro_safe:
                    ass += f"Dialogue: 2,{_ass_time(outro_start)},{_ass_time(outro_end)},Karaoke,,0,0,0,,{{\\an5\\fs{max(26, int(height*.045))}\\bord2\\shad1\\1c&H00FFFFFF&\\3c&H00202A3A&\\fad(450,500)}}{outro_safe}\n"

            if watermark_enabled and watermark_text.strip():
                watermark_safe = _ass_safe_text(watermark_text.strip())
                wm_pos = {
                    "Trên trái": (7, int(width*.025), int(height*.035)),
                    "Trên phải": (9, width-int(width*.025), int(height*.035)),
                    "Dưới trái": (1, int(width*.025), height-int(height*.035)),
                    "Dưới phải": (3, width-int(width*.025), height-int(height*.035)),
                }.get(watermark_position, (3, width-int(width*.025), height-int(height*.035)))
                align, wm_x, wm_y = wm_pos
                opacity = max(15.0, min(100.0, float(watermark_opacity)))
                alpha = int(round(255 * (1.0 - opacity / 100.0)))
                wm_size = max(14, min(40, int(height*.021)))
                wm_outline = max(1.0, height*.0012)
                # ASS alpha is inverse opacity: 00=opaque, FF=transparent.
                ass += (f"Dialogue: 1,0:00:00.00,{_ass_time(duration)},Karaoke,,0,0,0,,"
                        f"{{\\an{align}\\pos({wm_x},{wm_y})\\fs{wm_size}\\alpha&H{alpha:02X}&"
                        f"\\bord{wm_outline:.1f}\\shad0\\1c&H00FFFFFF&\\3c&H00000000&}}{watermark_safe}\n")

            ass_path.write_text(ass, encoding="utf-8-sig")
            self.q.put(("log", f"Add Karaoke: {len(cues)} cue(s); video={video_effect}; outro={outro_seconds}s; watermark={'on' if watermark_enabled and watermark_text.strip() else 'off'}."))
            _run_karaoke_ffmpeg(video, output, ass_path, self.cancel,
                                lambda pct, msg: self.q.put(("karaoke_progress", pct, msg)),
                                lambda msg: self.q.put(("log", msg)),
                                video_effect=video_effect, outro_seconds=outro_seconds,
                                outro_text=outro_text, mute_original=mute_original,
                                original_volume=original_volume, remove_dialogue=remove_dialogue,
                                music_path=music_path, sfx_path=sfx_path,
                                music_volume=music_volume, sfx_volume=sfx_volume,
                                voice_path=voice_path, voice_volume=voice_volume,
                                voice_start=voice_start, voice_priority=voice_priority)
            self.q.put(("karaoke_done", str(output)))
        except InterruptedError as exc:
            self.q.put(("cancelled", str(exc)))
        except Exception as exc:
            self.q.put(("error", str(exc)))
        finally:
            if ass_path:
                ass_path.unlink(missing_ok=True)

    def _build_merge_tab(self):
        tab = self.merge_tab
        frame = tk.Frame(tab, bg="#0d1625", padx=22, pady=18)
        frame.pack(fill="both", expand=True)
        self._label(frame, "MERGE VIDEO + AUDIO", "#7dd3fc", 12, True).pack(anchor="w")
        tk.Label(frame, text="Ghép track video và audio ngoài thành MP4 mới; thêm watermark và outro. Batch sẽ tự ghép các file có cùng tên (không tính phần mở rộng).",
                 bg="#0d1625", fg="#9fb2cc", font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", pady=(5,14))
        mode = tk.Frame(frame, bg="#0d1625"); mode.pack(fill="x", pady=5)
        self._label(mode, "Chế độ:").pack(side="left")
        ttk.Combobox(mode, textvariable=self.merge_mode_var, state="readonly", width=30,
                     values=["Batch – ghép theo tên file", "Một video + một audio"]).pack(side="left", padx=8)
        self._entry_row(frame, "Video (chế độ đơn)", self.merge_video_var, self._pick_merge_video)
        self._entry_row(frame, "Audio (chế độ đơn)", self.merge_audio_var, self._pick_merge_audio)
        tk.Label(frame, text="Hoặc ở chế độ Batch, chọn hai thư mục. Ví dụ lesson01.mp4 sẽ ghép với lesson01.mp3; lesson02.mov ghép với lesson02.wav. Không tìm thấy file trùng tên sẽ được báo và bỏ qua.",
                 bg="#14243a", fg="#c8d8ea", font=("Segoe UI", 9), wraplength=900, justify="left", padx=10, pady=8).pack(fill="x", pady=(6,8))
        self._entry_row(frame, "Thư mục video (Batch)", self.merge_video_dir_var, self._pick_merge_video_dir)
        self._entry_row(frame, "Thư mục audio (Batch)", self.merge_audio_dir_var, self._pick_merge_audio_dir)
        self._entry_row(frame, "Thư mục lưu kết quả", self.merge_output_dir_var, self._pick_merge_output_dir)
        self._label(frame, "OUTRO", "#7dd3fc", 10, True).pack(anchor="w", pady=(18,5))
        row=tk.Frame(frame,bg="#0d1625"); row.pack(fill="x",pady=3)
        self._label(row,"Thời lượng (giây):").pack(side="left")
        ttk.Combobox(row,textvariable=self.merge_outro_seconds_var,state="readonly",width=6,values=["0","2","3","4","5","6"]).pack(side="left",padx=8)
        self._entry_row(frame,"Outro dòng 1",self.merge_outro_line1_var,lambda:None)
        self._entry_row(frame,"Outro dòng 2",self.merge_outro_line2_var,lambda:None)
        self._label(frame,"WATERMARK", "#7dd3fc", 10, True).pack(anchor="w",pady=(14,5))
        tk.Checkbutton(frame,text="Bật watermark",variable=self.merge_watermark_enabled_var,bg="#0d1625",fg="#e5eefb",selectcolor="#1d2a3d",activebackground="#0d1625").pack(anchor="w")
        self._entry_row(frame,"Nội dung watermark",self.merge_watermark_text_var,lambda:None)
        wr=tk.Frame(frame,bg="#0d1625"); wr.pack(fill="x",pady=4)
        self._label(wr,"Vị trí:").pack(side="left")
        ttk.Combobox(wr,textvariable=self.merge_watermark_position_var,state="readonly",width=14,values=["Trên trái","Trên phải","Dưới trái","Dưới phải"]).pack(side="left",padx=8)
        self._label(wr,"Opacity:").pack(side="left",padx=(18,4))
        ttk.Scale(wr,from_=15,to=100,variable=self.merge_watermark_opacity_var,orient="horizontal",length=220).pack(side="left")
        self._label(wr,"15–100%").pack(side="left",padx=5)
        tk.Label(frame,text="Audio ngoài sẽ thay thế audio có sẵn trong video. Thời lượng xuất dùng phần ngắn hơn giữa video và audio để tránh phần hình không có tiếng hoặc audio bị kéo dài. Video được mã hóa lại để chèn watermark/outro.",bg="#14243a",fg="#c8d8ea",font=("Segoe UI",9),wraplength=900,justify="left",padx=10,pady=8).pack(fill="x",pady=(12,8))
        buttons=tk.Frame(frame,bg="#0d1625"); buttons.pack(fill="x",pady=8)
        self.merge_start_btn=self._button(buttons,"BẮT ĐẦU GHÉP VIDEO",self._start_merge_export,primary=True); self.merge_start_btn.pack(side="left",padx=(0,8))
        self.merge_cancel_btn=self._button(buttons,"HỦY",self._cancel_merge_export); self.merge_cancel_btn.pack(side="left")
        self.merge_progress=ttk.Progressbar(frame,mode="determinate",maximum=100); self.merge_progress.pack(fill="x",pady=(10,3))
        tk.Label(frame,textvariable=self.merge_progress_var,bg="#0d1625",fg="#9fb2cc",font=("Segoe UI",9),anchor="w").pack(fill="x")

    def _pick_merge_video(self):
        f=filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),("All files","*.*")])
        if f: self.merge_video_var.set(f)
    def _pick_merge_audio(self):
        f=filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus"),("All files","*.*")])
        if f: self.merge_audio_var.set(f)
    def _pick_merge_video_dir(self):
        f=filedialog.askdirectory()
        if f: self.merge_video_dir_var.set(f)
    def _pick_merge_audio_dir(self):
        f=filedialog.askdirectory()
        if f: self.merge_audio_dir_var.set(f)
    def _pick_merge_output_dir(self):
        f=filedialog.askdirectory()
        if f: self.merge_output_dir_var.set(f)

    def _start_merge_export(self):
        mode=self.merge_mode_var.get()
        outdir=Path(self.merge_output_dir_var.get()).expanduser()
        if mode.startswith("Một"):
            v=Path(self.merge_video_var.get()); a=Path(self.merge_audio_var.get())
            if not v.is_file() or not a.is_file():
                messagebox.showwarning("Thiếu file","Hãy chọn đúng một video và một audio."); return
            jobs=[(v,a)]
        else:
            vd=Path(self.merge_video_dir_var.get()); ad=Path(self.merge_audio_dir_var.get())
            if not vd.is_dir() or not ad.is_dir():
                messagebox.showwarning("Thiếu thư mục","Hãy chọn thư mục video và thư mục audio cho chế độ Batch."); return
            videos=[x for x in vd.iterdir() if x.is_file() and x.suffix.lower() in VIDEO_EXTS]
            audios=[x for x in ad.iterdir() if x.is_file() and x.suffix.lower() in {".mp3",".wav",".m4a",".aac",".flac",".ogg",".opus"}]
            amap={}
            for a in audios: amap.setdefault(a.stem.casefold(),[]).append(a)
            jobs=[]; missing=[]; duplicate=[]
            for v in sorted(videos):
                matches=amap.get(v.stem.casefold(),[])
                if len(matches)==1: jobs.append((v,matches[0]))
                elif not matches: missing.append(v.name)
                else: duplicate.append(v.name+" → "+", ".join(x.name for x in matches))
            if missing or duplicate:
                msg=[]
                if missing: msg.append("Không có audio trùng tên: "+", ".join(missing[:12]))
                if duplicate: msg.append("Có nhiều audio trùng tên (cần xử lý để tránh ghép nhầm): "+"; ".join(duplicate[:8]))
                if duplicate:
                    messagebox.showwarning("Tên file chưa duy nhất","\n".join(msg)); return
                self._log("Batch pairing: "+" | ".join(msg))
            if not jobs:
                messagebox.showwarning("Không có cặp file","Không tìm thấy video/audio nào trùng tên."); return
        outdir.mkdir(parents=True,exist_ok=True)
        self.cancel.clear(); self.merge_progress.configure(value=0)
        self.merge_progress_var.set(f"Chuẩn bị ghép {len(jobs)} cặp...")
        args=(jobs,outdir,float(self.merge_outro_seconds_var.get()),"\n".join([self.merge_outro_line1_var.get(),self.merge_outro_line2_var.get()]),self.merge_watermark_enabled_var.get(),self.merge_watermark_text_var.get(),self.merge_watermark_position_var.get(),float(self.merge_watermark_opacity_var.get()))
        self.merge_start_btn.configure(state="disabled")
        self.worker=threading.Thread(target=self._merge_export_worker,args=args,daemon=True); self.worker.start()

    def _cancel_merge_export(self):
        self.cancel.set(); self.merge_progress_var.set("Đang yêu cầu hủy...")

    def _merge_export_worker(self,jobs,outdir,outro_seconds,outro_text,wm_enabled,wm_text,wm_position,wm_opacity):
        outdir.mkdir(parents=True, exist_ok=True)
        done=[]; failed=[]
        try:
            for idx,(video,audio) in enumerate(jobs,1):
                if self.cancel.is_set(): raise InterruptedError("Đã hủy batch.")
                output=outdir/(video.stem+"_merged.mp4")
                ass_path=outdir/(f".evs_merge_{os.getpid()}_{idx}.ass")
                try:
                    duration=min(probe_duration(video),probe_duration(audio))
                    w,h=probe_video_size(video)
                    ass="[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,%d,&H00FFFFFF,&H000000FF,&H00101827,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,35,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"%(w,h,max(20,int(h*.045)))
                    if wm_enabled and wm_text.strip():
                        pos={"Trên trái":(7,int(w*.025),int(h*.035)),"Trên phải":(9,w-int(w*.025),int(h*.035)),"Dưới trái":(1,int(w*.025),h-int(h*.035)),"Dưới phải":(3,w-int(w*.025),h-int(h*.035))}.get(wm_position,(3,w-int(w*.025),h-int(h*.035)))
                        an,x,y=pos; alpha=int(round(255*(1-max(15,min(100,wm_opacity))/100)))
                        safe=_ass_safe_text(wm_text.strip())
                        ass+=f"Dialogue: 1,0:00:00.00,{_ass_time(duration)},Default,,0,0,0,,{{\\an{an}\\pos({x},{y})\\fs{max(14,int(h*.021))}\\alpha&H{alpha:02X}&\\bord2\\shad0}}{safe}\n"
                    if outro_seconds>0 and outro_text.strip():
                        start=max(0,duration-min(outro_seconds,max(.1,duration)))
                        safe=r"\N".join(_ass_safe_text(z.strip()) for z in outro_text.splitlines() if z.strip())
                        if safe: ass+=f"Dialogue: 2,{_ass_time(start)},{_ass_time(duration)},Default,,0,0,0,,{{\\an5\\fs{max(26,int(h*.045))}\\bord2\\shad1\\fad(450,500)}}{safe}\n"
                    ass_path.write_text(ass,encoding="utf-8-sig")
                    vf=f"subtitles=filename={ass_path.name}"
                    if outro_seconds>0: vf+=f",fade=t=out:st={max(0,duration-min(outro_seconds,duration)):.3f}:d={max(.25,min(outro_seconds,duration)):.3f}"
                    cmd=[ffmpeg_path(),"-y","-hide_banner","-loglevel","error","-i",str(video),"-i",str(audio),"-filter_complex",f"[0:v:0]{vf}[v]","-map","[v]","-map","1:a:0","-t",f"{duration:.3f}","-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",str(output)]
                    proc=subprocess.Popen(cmd,cwd=str(outdir),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
                    while proc.poll() is None:
                        if self.cancel.is_set():
                            proc.terminate()
                            try: proc.wait(timeout=3)
                            except subprocess.TimeoutExpired: proc.kill()
                            raise InterruptedError("Đã hủy khi đang render.")
                        time.sleep(.2)
                    err=proc.stderr.read() if proc.stderr else ""
                    if proc.returncode: raise RuntimeError(err[-2000:] or "FFmpeg render failed")
                    done.append(output)
                except InterruptedError: raise
                except Exception as e: failed.append((video.name,str(e))); self.q.put(("log",f"Merge lỗi {video.name}: {e}"))
                finally: ass_path.unlink(missing_ok=True)
                self.q.put(("merge_progress",int(idx*100/len(jobs)),f"Đã xử lý {idx}/{len(jobs)}: {video.name}"))
            if self.cancel.is_set(): raise InterruptedError("Đã hủy batch.")
            self.q.put(("merge_done",len(done),len(failed),str(outdir),[x.name for x in done]))
        except InterruptedError as e: self.q.put(("merge_cancelled",str(e),len(done),len(failed)))
        except Exception as e: self.q.put(("merge_error",str(e)))

    def _build_reading_tab(self):
        tab = self.reading_tab
        outer = tk.Frame(tab, bg="#0d1625", padx=12, pady=12)
        outer.pack(fill="both", expand=True)
        left_view = tk.Frame(outer, bg="#0d1625")
        left_view.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.reading_left_canvas = tk.Canvas(left_view, bg="#0d1625", bd=0, highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_view, orient="vertical", command=self.reading_left_canvas.yview)
        self.reading_left_canvas.configure(yscrollcommand=left_scroll.set)
        self.reading_left_canvas.pack(side="left", fill="both", expand=True)
        left = tk.Frame(self.reading_left_canvas, bg="#0d1625")
        left_window = self.reading_left_canvas.create_window((0, 0), window=left, anchor="nw")
        left_scroll_state = {"shown": False}
        def update_reading_left_scroll(_event=None):
            self.reading_left_canvas.configure(scrollregion=self.reading_left_canvas.bbox("all"))
            bbox = self.reading_left_canvas.bbox("all")
            needs = bool(bbox and bbox[3]-bbox[1] > self.reading_left_canvas.winfo_height()+3)
            if needs and not left_scroll_state["shown"]:
                left_scroll.pack(side="right", fill="y"); left_scroll_state["shown"] = True
            elif not needs and left_scroll_state["shown"]:
                left_scroll.pack_forget(); left_scroll_state["shown"] = False
        left.bind("<Configure>", update_reading_left_scroll)
        self.reading_left_canvas.bind("<Configure>", lambda event: (self.reading_left_canvas.itemconfigure(
            left_window, width=event.width), update_reading_left_scroll()))
        right = tk.Frame(outer, bg="#101e32", width=390, padx=14, pady=14)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)

        self._label(left, "READING ALONG STUDIO", "#7dd3fc", 12, True).pack(anchor="w", pady=(0, 4))
        tk.Label(left, text="Tự tạo trang sách, đồng bộ lời đọc và để bàn tay hoạt họa chỉ theo từng từ.",
                 bg="#0d1625", fg="#9fb2cc", font=("Segoe UI", 9), wraplength=760,
                 justify="left").pack(anchor="w", pady=(0, 10))

        web_box = tk.LabelFrame(left, text="LẤY BÀI ĐỌC TỪ WEBSITE", bg="#0d1625", fg="#7dd3fc",
                                font=("Segoe UI", 9, "bold"), bd=1, relief="groove", padx=8, pady=6)
        web_box.pack(fill="x", pady=(0, 7))
        web_line = tk.Frame(web_box, bg="#0d1625")
        web_line.pack(fill="x")
        tk.Entry(web_line, textvariable=self.reading_source_url_var, bg="#18263a", fg="#f8fafc",
                 insertbackground="white", relief="flat", font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 7))
        self.reading_web_fetch_btn = self._button(web_line, "LẤY NỘI DUNG", self._reading_fetch_web, primary=True)
        self.reading_web_fetch_btn.pack(side="left")
        web_select_line = tk.Frame(web_box, bg="#0d1625")
        web_select_line.pack(fill="x", pady=(5, 0))
        self._label(web_select_line, "Bài trên trang:", size=8).pack(side="left")
        self.reading_web_combo = ttk.Combobox(web_select_line, textvariable=self.reading_web_selection_var,
                                               state="readonly", width=35, values=[])
        self.reading_web_combo.pack(side="left", fill="x", expand=True, padx=7)
        self.reading_web_load_btn = self._button(web_select_line, "TẢI BÀI ĐÃ CHỌN", self._reading_load_web_selected)
        self.reading_web_load_btn.pack(side="left")
        tk.Label(web_box, text="Tool lấy văn bản từ trang công khai, bỏ menu/quảng cáo và phần đáp án khi nhận diện được. A có thể sửa nội dung trong ô bên dưới trước khi ghép TTS. Không cần API key.",
                 bg="#0d1625", fg="#a9bbd2", font=("Segoe UI", 7), wraplength=780,
                 justify="left").pack(anchor="w", pady=(5, 0))

        topic_row = tk.Frame(left, bg="#0d1625")
        topic_row.pack(fill="x", pady=3)
        self._label(topic_row, "Chủ đề:", size=9, bold=True).pack(side="left")
        tk.Entry(topic_row, textvariable=self.reading_topic_var, bg="#18263a", fg="#f8fafc",
                 insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True, padx=8, ipady=6)
        settings = tk.Frame(left, bg="#0d1625")
        settings.pack(fill="x", pady=4)
        self._label(settings, "Ngôn ngữ:").pack(side="left")
        ttk.Combobox(settings, textvariable=self.reading_language_var, state="readonly", width=12,
                     values=["English", "Japanese"]).pack(side="left", padx=(6, 16))
        self._label(settings, "Trình độ:").pack(side="left")
        ttk.Combobox(settings, textvariable=self.reading_level_var, state="readonly", width=8,
                     values=["Beginner", "A1", "A2", "B1", "B2"]).pack(side="left", padx=6)
        self._label(settings, "Màu sách:").pack(side="left", padx=(12, 3))
        ttk.Combobox(settings, textvariable=self.reading_book_color_var, state="readonly", width=13,
                     values=list(READING_BOOK_PALETTES.keys())).pack(side="left", padx=4)
        self._label(settings, "Minh họa:").pack(side="left", padx=(10, 3))
        ttk.Combobox(settings, textvariable=self.reading_illustration_style_var, state="readonly", width=23,
                     values=["Flat 2D - Phẳng", "2.5D - Minh họa nổi khối", "3D Cartoon - Giả lập 3D"]).pack(side="left", padx=4)
        genrow = tk.Frame(left, bg="#0d1625")
        genrow.pack(fill="x", pady=(5, 8))
        self.reading_generate_btn = self._button(genrow, "TẠO BÀI ĐỌC MẪU TỪ CHỦ ĐỀ", self._reading_generate, primary=True)
        self.reading_generate_btn.pack(side="left", padx=(0, 8))
        self._button(genrow, "Nhập sách / văn bản...", self._pick_reading_text).pack(side="left")

        self._label(left, "Tiêu đề trang sách:", size=9, bold=True).pack(anchor="w", pady=(2, 3))
        tk.Entry(left, textvariable=self.reading_title_var, bg="#18263a", fg="#f8fafc",
                 insertbackground="white", relief="flat", font=("Segoe UI", 10)).pack(fill="x", ipady=7, pady=(0, 7))
        self._label(left, "Nội dung bài đọc (có thể sửa trực tiếp):", size=9, bold=True).pack(anchor="w")
        text_frame = tk.Frame(left, bg="#0d1625")
        text_frame.pack(fill="both", expand=True, pady=(4, 8))
        self.reading_text = tk.Text(text_frame, height=10, wrap="word", bg="#18263a", fg="#f8fafc",
                                    insertbackground="white", relief="flat", font=("Segoe UI", 10),
                                    padx=10, pady=9, undo=True)
        reading_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.reading_text.yview)
        self.reading_text.configure(yscrollcommand=reading_scroll.set)
        self.reading_text.pack(side="left", fill="both", expand=True)
        reading_scroll.pack(side="right", fill="y")
        self.reading_text.insert("1.0", "Tom wakes up early every morning.\nHe opens the window and makes his bed.\nThen he drinks a glass of water and eats breakfast.\nHe checks the time, takes his bag, and leaves home.\nA good morning helps him start the day with energy.")

        self._label(left, "AUDIO TTS / GIỌNG ĐỌC", "#7dd3fc", 10, True).pack(anchor="w", pady=(7, 3))
        self._entry_row(left, "Chọn file audio đã đọc nội dung trên", self.reading_audio_var, self._pick_reading_audio)
        tk.Checkbutton(left, text="Ưu tiên căn thời gian theo giọng đọc bằng Whisper (khuyến nghị; cần faster-whisper)",
                       variable=self.reading_whisper_var, bg="#0d1625", fg="#e5eefb", selectcolor="#1d2a3d",
                       activebackground="#0d1625", activeforeground="#ffffff", wraplength=760,
                       justify="left").pack(anchor="w", pady=(2, 2))
        tk.Label(left, text="Whisper giữ timestamp thực của từng từ và khoảng nghỉ. Nếu chưa cài, chạy install_alignment.bat trong thư mục ứng dụng; nếu không có Whisper, chương trình vẫn xuất bằng timing ước lượng.",
                 bg="#0d1625", fg="#9fb2cc", font=("Segoe UI", 8), wraplength=760,
                 justify="left").pack(anchor="w", pady=(0, 6))
        speed_box = tk.Frame(left, bg="#14243a", padx=10, pady=9)
        speed_box.pack(fill="x", pady=(2, 7))
        self._label(speed_box, "TỐC ĐỘ ĐỌC & TỐC ĐỘ VIDEO", "#7dd3fc", 9, True).pack(anchor="w", pady=(0, 6))
        speed_row = tk.Frame(speed_box, bg="#14243a")
        speed_row.pack(fill="x")
        speed_values = ["0.75x - Chậm", "0.9x - Hơi chậm", "1.0x - Bình thường", "1.1x - Hơi nhanh", "1.25x - Nhanh", "1.5x - Rất nhanh"]
        self._label(speed_row, "Giọng đọc:", size=9, bold=True).pack(side="left")
        ttk.Combobox(speed_row, textvariable=self.reading_speech_speed_var, state="readonly", width=20,
                     values=speed_values).pack(side="left", padx=(7, 18))
        self._label(speed_row, "Diễn tiến video:", size=9, bold=True).pack(side="left")
        ttk.Combobox(speed_row, textvariable=self.reading_video_speed_var, state="readonly", width=20,
                     values=speed_values).pack(side="left", padx=7)
        tk.Label(speed_box, textvariable=self.reading_speed_summary_var, bg="#14243a", fg="#86efac",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 0))
        self.reading_speech_speed_var.trace_add("write", lambda *_: self._update_reading_speed_summary())
        self.reading_video_speed_var.trace_add("write", lambda *_: self._update_reading_speed_summary())
        tk.Label(left, text="Tốc độ giọng đọc và diễn tiến video được kết hợp để giữ bàn tay, highlight và TTS đồng bộ. Ví dụ 0.9x × 1.1x ≈ 0.99x tổng.",
                 bg="#14243a", fg="#c8d8ea", font=("Segoe UI", 8), wraplength=760,
                 justify="left", padx=10, pady=7).pack(fill="x", pady=(0, 6))
        self._entry_row(left, "File MP4 đầu ra", self.reading_output_var, self._pick_reading_output)
        buttons = tk.Frame(left, bg="#0d1625")
        buttons.pack(fill="x", pady=(9, 0))
        self.reading_preview_btn = self._button(buttons, "XEM TRANG SÁCH + VỊ TRÍ TAY", self._reading_preview)
        self.reading_preview_btn.pack(side="left", padx=(0, 8))
        self.reading_export_btn = self._button(buttons, "XUẤT READING ALONG MP4", self._start_reading_export, primary=True)
        self.reading_export_btn.pack(side="left")
        self.reading_progress = ttk.Progressbar(left, mode="determinate", maximum=100)
        self.reading_progress.pack(fill="x", pady=(11, 2))
        tk.Label(left, textvariable=self.reading_progress_var, bg="#0d1625", fg="#9fb2cc",
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")

        tk.Label(right, text="BOOK + POINTER PREVIEW", bg="#101e32", fg="#7dd3fc",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.reading_preview_label = tk.Label(right, text="Bấm XEM PREVIEW để xem trang sách và bàn tay chỉ vào từ đầu tiên.",
                                              bg="#0b1524", fg="#94a3b8", font=("Segoe UI", 9),
                                              justify="center", wraplength=330)
        self.reading_preview_label.pack(fill="both", expand=True, pady=(10, 8))
        tk.Label(right, text="Tool tự vẽ quyển sách và bàn tay bằng đồ họa, không cần tải ảnh bàn tay. Có thể dùng bài mẫu offline hoặc nhập TXT / MD / PDF / EPUB. Audio TTS cần được chọn riêng.",
                 bg="#101e32", fg="#94a3b8", font=("Segoe UI", 8), wraplength=330,
                 justify="left").pack(anchor="w")

    def _update_reading_speed_summary(self):
        speech = _reading_speed_value(self.reading_speech_speed_var.get())
        video = _reading_speed_value(self.reading_video_speed_var.get())
        total = speech * video
        self.reading_speed_summary_var.set(f"Tốc độ tổng: {total:.2f}x  |  Video đầu ra sẽ {'ngắn hơn' if total > 1.01 else 'dài hơn' if total < 0.99 else 'giữ nguyên thời lượng'} so với audio gốc.")

    def _reading_fetch_web(self):
        url = self.reading_source_url_var.get().strip()
        if not url:
            messagebox.showwarning("Thiếu URL", "Hãy dán địa chỉ trang web cần lấy nội dung.")
            return
        if self.reading_web_worker and self.reading_web_worker.is_alive():
            messagebox.showinfo("Đang lấy nội dung", "Một yêu cầu lấy nội dung website vẫn đang chạy.")
            return
        self.reading_web_fetch_btn.configure(state="disabled")
        self.reading_web_load_btn.configure(state="disabled")
        self.reading_progress_var.set("Đang đọc trang web và tìm các bài đọc...")
        self.reading_web_worker = threading.Thread(
            target=self._reading_web_fetch_worker, args=(url, None, []), daemon=True
        )
        self.reading_web_worker.start()

    def _reading_load_web_selected(self):
        selected = self.reading_web_selection_var.get().strip()
        item = next((x for x in self.reading_web_items if x.get("title") == selected), None)
        if not item:
            messagebox.showwarning("Chưa chọn bài", "Hãy bấm LẤY NỘI DUNG trước, sau đó chọn một bài trong danh sách.")
            return
        if self.reading_web_worker and self.reading_web_worker.is_alive():
            messagebox.showinfo("Đang lấy nội dung", "Một yêu cầu lấy nội dung website vẫn đang chạy.")
            return
        self.reading_web_fetch_btn.configure(state="disabled")
        self.reading_web_load_btn.configure(state="disabled")
        self.reading_progress_var.set("Đang tải bài: " + item["title"] + "...")
        self.reading_web_worker = threading.Thread(
            target=self._reading_web_fetch_worker, args=(item["url"], item, list(self.reading_web_items)), daemon=True
        )
        self.reading_web_worker.start()

    def _reading_web_fetch_worker(self, url, selected_item, existing_items):
        try:
            page = fetch_reading_web_page(url)
            items = list(existing_items or [])
            selected = selected_item
            is_lesson_index = "practice-reading-english-exercises-for-beginner-" not in urlparse(url).path.lower()
            if selected is None and page.get("links") and is_lesson_index:
                items = page["links"]
                selected = items[0]
                # Load the first lesson automatically so the index URL produces usable text in one click.
                article = fetch_reading_web_page(selected["url"])
            else:
                article = page
                if selected is None:
                    selected = {"title": article.get("title", "Reading Practice"), "url": article.get("url", url)}
            if not article.get("content"):
                raise RuntimeError(
                    "Đã mở được trang nhưng không tìm thấy phần văn bản bài đọc. "
                    "A có thể mở trang gốc, copy đoạn đọc và dán vào ô Nội dung bài đọc."
                )
            self.q.put(("reading_web_loaded", items, selected, article, url))
        except Exception as exc:
            self.q.put(("reading_web_error", str(exc)))

    def _reading_apply_web_content(self, items, selected, article, requested_url):
        self.reading_web_items = list(items or [])
        if self.reading_web_items:
            labels = [x.get("title", "Reading") for x in self.reading_web_items]
            self.reading_web_combo.configure(values=labels)
            self.reading_web_selection_var.set(selected.get("title", labels[0]))
            self.reading_web_load_btn.configure(state="normal")
        else:
            self.reading_web_combo.configure(values=[])
            self.reading_web_selection_var.set("")
            self.reading_web_load_btn.configure(state="disabled")
        title = article.get("title") or selected.get("title") or "Reading Practice"
        content = article.get("content", "").strip()
        self.reading_title_var.set(title)
        self.reading_topic_var.set(selected.get("title") or title)
        self.reading_text.delete("1.0", "end")
        self.reading_text.insert("1.0", content)
        source = article.get("url") or selected.get("url") or requested_url
        self.reading_progress_var.set(
            f"Đã lấy {len(content):,} ký tự từ {title}. Đã đưa vào ô văn bản để a chỉnh sửa; chọn audio TTS rồi preview/xuất video."
        )
        self._log(f"Reading Along web import: {title} | source: {source}")
        if self.reading_web_items:
            self._log(f"Found {len(self.reading_web_items)} reading pages from index: {requested_url}")

    def _reading_generate(self):
        title, body = generate_reading_lesson(self.reading_topic_var.get(),
                                              self.reading_language_var.get(),
                                              self.reading_level_var.get())
        self.reading_title_var.set(title)
        self.reading_text.delete("1.0", "end")
        self.reading_text.insert("1.0", body)
        self.reading_progress_var.set("Đã tạo bài đọc mẫu offline. A có thể sửa nội dung trước khi xuất.")
        self._log(f"Reading Along: generated an offline sample lesson for topic '{self.reading_topic_var.get()}'.")

    def _pick_reading_text(self):
        p = filedialog.askopenfilename(filetypes=[
            ("Book / text files", "*.txt *.md *.pdf *.epub"),
            ("Text files", "*.txt *.md"), ("PDF", "*.pdf"), ("EPUB", "*.epub"),
            ("All files", "*.*")])
        if not p:
            return
        path = Path(p)
        try:
            if path.suffix.lower() in {".txt", ".md"}:
                content = _decode_text_file(path)
            elif path.suffix.lower() == ".pdf":
                try:
                    from pypdf import PdfReader
                except Exception as exc:
                    raise RuntimeError("Để nhập PDF, cài thêm pypdf bằng lệnh: .venv\\Scripts\\python.exe -m pip install pypdf") from exc
                reader = PdfReader(str(path))
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif path.suffix.lower() == ".epub":
                with zipfile.ZipFile(path) as archive:
                    html_files = [n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
                    chunks = []
                    for name in html_files:
                        raw = archive.read(name).decode("utf-8", errors="replace")
                        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I|re.S)
                        raw = re.sub(r"<br\s*/?>|</p>|</div>|</h[1-6]>", "\n", raw, flags=re.I)
                        raw = re.sub(r"<[^>]+>", " ", raw)
                        chunks.append(html_lib.unescape(raw))
                    content = "\n".join(chunks)
            else:
                return
            content = re.sub(r"[ \t]+", " ", content)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
            if not content:
                raise RuntimeError("Không trích xuất được văn bản từ file này.")
            self.reading_title_var.set(path.stem.replace("_", " "))
            self.reading_text.delete("1.0", "end")
            self.reading_text.insert("1.0", content[:100000])
            self.reading_topic_var.set(path.stem)
            self.reading_progress_var.set(f"Đã nhập nội dung từ {path.name}.")
        except Exception as exc:
            messagebox.showerror("Không thể nhập nội dung", str(exc))

    def _pick_reading_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma"), ("All files", "*.*")])
        if p:
            self.reading_audio_var.set(p)
            if self.reading_output_var.get().strip() in ("", str(OUTPUT_DIR / "reading_along.mp4")):
                self.reading_output_var.set(str(Path(p).with_name(Path(p).stem + "_reading_along.mp4")))

    def _pick_reading_output(self):
        audio = Path(self.reading_audio_var.get()) if self.reading_audio_var.get() else None
        initial = (audio.stem + "_reading_along.mp4") if audio else "reading_along.mp4"
        p = filedialog.asksaveasfilename(defaultextension=".mp4", initialfile=initial,
                                         filetypes=[("MP4 video", "*.mp4")])
        if p:
            self.reading_output_var.set(p)

    def _reading_inputs(self):
        text = self.reading_text.get("1.0", "end").strip()
        audio = Path(self.reading_audio_var.get()) if self.reading_audio_var.get().strip() else None
        output = Path(self.reading_output_var.get()) if self.reading_output_var.get().strip() else None
        if not text:
            raise ValueError("Hãy tạo bài đọc hoặc nhập nội dung sách trước.")
        if not audio or not audio.is_file() or audio.suffix.lower() not in AUDIO_EXTS:
            raise ValueError("Hãy chọn file audio TTS đã đọc nội dung trong ô văn bản.")
        if output is None:
            output = OUTPUT_DIR / (audio.stem + "_reading_along.mp4")
            self.reading_output_var.set(str(output))
        if output.suffix.lower() != ".mp4":
            output = output.with_suffix(".mp4")
            self.reading_output_var.set(str(output))
        if output.resolve() == audio.resolve():
            raise ValueError("File MP4 đầu ra không được trùng với file audio đầu vào.")
        return text, audio, output

    def _reading_preview(self):
        try:
            text = self.reading_text.get("1.0", "end").strip()
            if not text:
                raise ValueError("Hãy tạo bài đọc hoặc nhập nội dung sách trước.")
            tokens = reading_tokenize(text, self.reading_language_var.get())
            frame = render_reading_book_frame(self.reading_title_var.get(), self.reading_topic_var.get(),
                                               tokens, 0, 0, 48,
                                               self.reading_language_var.get(), self.reading_level_var.get(),
                                               book_color=self.reading_book_color_var.get(),
                                               illustration_style=self.reading_illustration_style_var.get().split(" - ")[0])
            frame.thumbnail((310, 550), Image.Resampling.LANCZOS)
            self.reading_preview_image = ImageTk.PhotoImage(frame)
            self.reading_preview_label.configure(image=self.reading_preview_image, text="")
            self.reading_progress_var.set(f"Preview: {len(tokens)} đơn vị đọc; bàn tay đang chỉ vào đơn vị đầu tiên.")
        except Exception as exc:
            messagebox.showwarning("Chưa thể preview", str(exc))

    def _start_reading_export(self):
        try:
            text, audio, output = self._reading_inputs()
        except Exception as exc:
            messagebox.showwarning("Thiếu dữ liệu", str(exc))
            return
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy. Hãy đợi tác vụ đó hoàn tất.")
            return
        self.cancel.clear()
        self.reading_export_btn.configure(state="disabled")
        self.reading_preview_btn.configure(state="disabled")
        self.reading_progress.configure(value=0)
        self.reading_progress_var.set("Đang chuẩn bị Reading Along...")
        args = (self.reading_title_var.get().strip() or "Reading Practice",
                self.reading_topic_var.get().strip(), text, audio, output,
                self.reading_language_var.get(), self.reading_level_var.get(),
                bool(self.reading_whisper_var.get()),
                _reading_speed_value(self.reading_speech_speed_var.get()),
                _reading_speed_value(self.reading_video_speed_var.get()),
                self.reading_book_color_var.get(),
                self.reading_illustration_style_var.get().split(" - ")[0])
        self.worker = threading.Thread(target=self._reading_export_worker, args=args, daemon=True)
        self.worker.start()

    def _reading_export_worker(self, title, topic, text, audio, output, language, level, use_whisper,
                               speech_speed=1.0, video_speed=1.0,
                               book_color="Sunny Yellow", illustration_style="2.5D"):

        try:
            count, duration, method = render_reading_along_video(
                title, topic, text, audio, output, language, level, use_whisper, self.cancel,
                progress=lambda pct, msg: self.q.put(("reading_progress", pct, msg)),
                log=lambda msg: self.q.put(("log", msg)),
                speech_speed=speech_speed, video_speed=video_speed,
                book_color=book_color, illustration_style=illustration_style)
            self.q.put(("reading_done", str(output), count, duration, method))
        except InterruptedError as exc:
            self.q.put(("reading_cancelled", str(exc)))
        except Exception as exc:
            self.q.put(("reading_error", str(exc)))

    def _build_footer(self):
        frame = tk.Frame(self.root, bg="#0d1625", padx=12, pady=8)
        frame.pack(fill="x")
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.status = tk.Label(frame, textvariable=self.status_var, bg="#0d1625", fg="#a9bdd3", anchor="w", font=("Segoe UI", 9))
        self.status.pack(fill="x", pady=(4, 0))
        self.log = tk.Text(frame, height=5, bg="#08111e", fg="#c5d4e5", insertbackground="white", relief="flat", font=("Consolas", 8), wrap="word")
        self.log.pack(fill="x", pady=(6, 0))
        self._log("Sẵn sàng. Educational Audio Video Studio 1.19 – batch video/audio merge, smart scroll, accurate Reading Along timeline, balanced book typography and 2.5D/3D illustrations.")

    def _log(self, msg: str):
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see("end")

    def _suggested_project_stem(self) -> str:
        """Prefer the audio filename, then transcript, then storyboard filename."""
        for raw_path in (self.audio_var.get(), self.text_var.get(),
                         str(self.storyboard_path) if self.storyboard_path else ""):
            if raw_path:
                candidate = Path(raw_path)
                if candidate.name:
                    return _safe_output_stem(candidate.stem)
        return "educational_video"

    def _update_default_output_name(self):
        if not self.output_customized:
            self.output_var.set(str(OUTPUT_DIR / f"{self._suggested_project_stem()}.mp4"))

    def _pick_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma"), ("All files", "*.*")])
        if p:
            self.audio_var.set(p)
            self._update_default_output_name()
            self.status_var.set("Đã chọn audio. Tên MP4 mặc định đã lấy theo tên audio.")

    def _pick_text(self):
        subtitle_patterns = "*.srt *.vtt *.ass *.ssa *.sbv *.lrc *.sub *.smi *.sami *.ttml *.dfxp *.xml *.scc"
        p = filedialog.askopenfilename(filetypes=[
            ("Transcript / Subtitle", f"*.txt *.md {subtitle_patterns}"),
            ("Subtitle files", subtitle_patterns),
            ("Text files", "*.txt *.md"),
            ("All files", "*.*")
        ])
        if p:
            self.text_var.set(p)
            if not self.audio_var.get():
                self._update_default_output_name()
            self.status_var.set(f"Đã chọn transcript/phụ đề: {Path(p).name}")

    def _update_composition_description(self):
        preset = VISUAL_COMPOSITION_PRESETS.get(self.composition_var.get(), VISUAL_COMPOSITION_PRESETS["Auto theo nội dung"])
        self.composition_desc_var.set(preset["description"])

    def _random_composition(self):
        choices = [name for name in VISUAL_COMPOSITION_PRESETS if name != "Auto theo nội dung"]
        chosen = random.choice(choices)
        self.composition_var.set(chosen)
        self._update_composition_description()
        self.status_var.set(f"Đã chọn ngẫu nhiên bố cục: {chosen}. Bấm Tạo prompt để áp dụng.")
        self._log(f"Random illustration composition: {chosen}")

    def _pick_json(self):
        p = filedialog.askopenfilename(filetypes=[("Storyboard JSON", "*.json"), ("All files", "*.*")])
        if p:
            self.json_var.set(p)
            self._load_storyboard(Path(p))

    def _pick_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4", initialdir=OUTPUT_DIR,
                                         initialfile=f"{self._suggested_project_stem()}.mp4",
                                         filetypes=[("MP4", "*.mp4")])
        if p:
            self.output_var.set(p)
            self.output_customized = True

    def _open_prompt(self):
        if os.name == "nt": os.startfile(PROMPT_PATH)
        else: webbrowser.open(PROMPT_PATH.as_uri())

    def _copy_schema(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.status_var.set("Đã copy JSON Schema vào clipboard.")
        messagebox.showinfo("Đã copy", "JSON Schema v1.3 đã được copy.")

    def _export_prompt(self):
        transcript = ""
        tpath = Path(self.text_var.get()) if self.text_var.get() else None
        if tpath and tpath.exists():
            try:
                transcript = read_transcript_file(tpath)
            except Exception as exc:
                messagebox.showerror("Không đọc được transcript", f"Không thể đọc file {tpath.name}:\n{exc}")
                return
        elif self.storyboard:
            transcript = "\n".join(s["text"] for s in self.storyboard.get("source_segments", []))
        if not transcript.strip():
            messagebox.showwarning("Thiếu transcript", "Chọn file TXT hoặc tải storyboard JSON trước để lấy source_segments.")
            return
        template = PROMPT_PATH.read_text(encoding="utf-8")
        duration = "null"
        audio = Path(self.audio_var.get()) if self.audio_var.get() else None
        if audio and audio.exists():
            try: duration = f"{probe_duration(audio):.2f}"
            except Exception: pass
        replacements = {
            "{{AUDIO_DURATION_SECONDS_OR_NULL}}": duration,
            "{{SOURCE_LANGUAGE_CODE_OR_AUTO}}": "auto",
            "{{DISPLAY_LANGUAGE_CODE}}": "same_as_source",
            "{{ASPECT_RATIO_9_16_OR_16_9}}": "9:16",
            "{{TARGET_AUDIENCE}}": "learners; infer from script if possible",
            "{{VISUAL_STYLE}}": "clean educational motion graphics; consistent typography and palette",
            "{{LOW_MEDIUM_HIGH}}": "medium",
            "{{NO_BY_DEFAULT}}": "false",
            "{{ILLUSTRATION_COMPOSITION_GUIDE}}": VISUAL_COMPOSITION_PRESETS.get(
                self.composition_var.get(), VISUAL_COMPOSITION_PRESETS["Auto theo nội dung"])["guide"],
            "{{PASTE_TIMESTAMPED_TRANSCRIPT_HERE}}": transcript,
            "{{EXACT_SCHEMA_JSON}}": SCHEMA_PATH.read_text(encoding="utf-8").strip(),
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        prompt_name = f"{self._suggested_project_stem()}_storyboard_prompt.txt"
        out = filedialog.asksaveasfilename(defaultextension=".txt", initialdir=DATA_DIR,
                                           initialfile=prompt_name, filetypes=[("Prompt", "*.txt")])
        if out:
            Path(out).write_text(template, encoding="utf-8")
            self._log(f"Đã xuất prompt: {out}")
            messagebox.showinfo("Prompt đã tạo", "Mở file prompt, đính kèm audio nếu có, rồi yêu cầu AI xuất JSON v1.3. Mỗi cảnh phải có text overlays và visual_fallback semantic; prompt có composition preset đã chọn; media web chỉ là tùy chọn.")

    def _load_storyboard(self, path: Path):
        try:
            data = migrate_storyboard(parse_json_file(path))
            errors = self.validator.validate(data)
            if errors:
                raise ValueError("Storyboard không hợp lệ:\n\n" + "\n".join("• " + x for x in errors[:30]))
            self.storyboard = data
            self.storyboard_path = path
            if not self.audio_var.get() and not self.text_var.get():
                self._update_default_output_name()
            self.assets_workspace = path.parent / (path.stem + "_assets")
            self.assets_workspace.mkdir(parents=True, exist_ok=True)
            sidecar = path.with_suffix(".assets.json")
            if sidecar.exists():
                self.asset_paths = json.loads(sidecar.read_text(encoding="utf-8"))
            else:
                self.asset_paths = {}
            self.aligned_segments.clear(); self.aligned_anchors.clear()
            self.asr_words.clear(); self.detected_language = data["project"].get("source_language", "auto")
            self._populate_scenes(); self._populate_assets()
            proj = data["project"]
            self.project_status_var.set(f"{proj['title']}\n{len(data['scenes'])} scenes · {len(data.get('source_segments', []))} source segments · schema {data['schema_version']}")
            self._log(f"Đã tải và validate storyboard: {path.name}")
            direct_count = sum(1 for a in data.get("assets", []) if a.get("download_url"))
            self.status_var.set("Storyboard hợp lệ. Media tùy chọn; vector fallback có auto-layout và collision guard.")
            if direct_count:
                self.root.after(250, lambda n=direct_count: self._ask_download_assets(n))
            else:
                self._log("Storyboard không có media ngoài. Tất cả cảnh sẽ render bằng visual_fallback icon vector, sơ đồ và typography trong JSON.")
        except Exception as exc:
            messagebox.showerror("Không tải được storyboard", str(exc))
            self._log("Lỗi tải JSON: " + str(exc))

    def _populate_scenes(self):
        for iid in self.scene_tree.get_children(): self.scene_tree.delete(iid)
        if not self.storyboard: return
        for scene in self.storyboard["scenes"]:
            start, end = scene.get("provisional_start_s"), scene.get("provisional_end_s")
            sid = scene["scene_id"]
            self.scene_tree.insert("", "end", iid=sid, text=sid, values=(f"{fmt_time(start)}–{fmt_time(end)}", scene["scene_type"]))

    def _on_scene_select(self, _event=None):
        if not self.storyboard: return
        sel = self.scene_tree.selection()
        if not sel: return
        sid = sel[0]
        scene = next((s for s in self.storyboard["scenes"] if s["scene_id"] == sid), None)
        if not scene: return
        start, end = scene.get("provisional_start_s"), scene.get("provisional_end_s")
        self.scene_title.configure(text=f"{sid} · {scene['scene_type']}")
        self.scene_meta.configure(text=f"{fmt_time(start)} – {fmt_time(end)} | layout: {scene['layout']} | {len(scene['elements'])} elements")
        fallback = scene.get("visual_fallback", {})
        lines = ["VISUAL SUMMARY", scene["visual_summary"], "", "LEARNING GOAL", scene["learning_goal"],
                 "", "BUILT-IN VISUAL FALLBACK", f"Mode: {fallback.get('mode', 'unknown')}"]
        for obj in fallback.get("objects", []):
            lines.append(f"• Vector icon {obj.get('shape')} — {obj.get('label') or obj.get('object_id')}")
        for con in fallback.get("connectors", []):
            lines.append(f"  connector: {con.get('from_object')} → {con.get('to_object')} ({con.get('label') or ''})")
        lines.extend(["", "STRUCTURED ON-SCREEN ELEMENTS"])
        for el in scene["elements"]:
            a = el["sync_anchor"]
            lines.append(f"• {el['element_id']} [{el['kind']}] {el.get('content') or '(no text)'}")
            lines.append(f"  anchor: {a['segment_id']} / {a['anchor_type']} / {a['quote']}")
            lines.append(f"  animation: {el['animation']['in']} → {el['animation']['out']}")
        self.scene_text.configure(state="normal")
        self.scene_text.delete("1.0", "end")
        self.scene_text.insert("1.0", "\n".join(lines))
        self.scene_text.configure(state="disabled")

    def _populate_assets(self):
        for iid in self.asset_tree.get_children(): self.asset_tree.delete(iid)
        self.asset_direct_url_var.set("")
        self.asset_source_url_var.set("")
        if not self.storyboard: return
        for asset in self.storyboard.get("assets", []):
            aid = asset["asset_id"]
            self.asset_tree.insert("", "end", iid=aid, text=aid,
                                   values=(asset["asset_type"], asset.get("provider") or asset["source"],
                                           asset["description"], asset.get("download_url") or "(không có direct URL)",
                                           self.asset_paths.get(aid, "")))
        children = self.asset_tree.get_children()
        if children:
            self.asset_tree.selection_set(children[0])
            self._show_asset_details()

    def _show_asset_details(self, _event=None):
        aid = self._asset_selected()
        asset = next((a for a in (self.storyboard or {}).get("assets", []) if a.get("asset_id") == aid), None)
        self.asset_direct_url_var.set((asset or {}).get("download_url") or "")
        self.asset_source_url_var.set((asset or {}).get("source_page_url") or "")

    def _copy_text_to_clipboard(self, value: str, label: str):
        if not value:
            messagebox.showinfo("Không có URL", f"Asset này không có {label}.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update_idletasks()
        self.status_var.set(f"Đã copy {label} đầy đủ vào clipboard.")
        self._log(f"Đã copy {label} đầy đủ.")

    def _copy_asset_direct_url(self):
        self._copy_text_to_clipboard(self.asset_direct_url_var.get(), "direct media URL")

    def _copy_asset_source_url(self):
        self._copy_text_to_clipboard(self.asset_source_url_var.get(), "source page URL")

    def _open_asset_direct_url(self):
        url = self.asset_direct_url_var.get().strip()
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("Thiếu direct URL", "Asset này không có download_url trỏ trực tiếp tới file media.")

    def _ask_download_assets(self, count: int):
        if not self.storyboard or (self.worker and self.worker.is_alive()): return
        if messagebox.askyesno("Tải media từ JSON", f"Storyboard có {count} direct media URL. Tải ảnh/video về thư mục:\n{self.assets_workspace}?\n\nApp sẽ lưu cả thông tin nguồn và license vào media_credits.txt."):
            self._start_download_assets()

    def _start_download_assets(self):
        if not self.storyboard:
            messagebox.showwarning("Chưa có JSON", "Tải storyboard JSON trước."); return
        if self.worker and self.worker.is_alive(): return
        targets = [a for a in self.storyboard.get("assets", []) if a.get("download_url")]
        if not targets:
            messagebox.showinfo("Không có media ngoài", "JSON không có direct media URL. Không sao: app sẽ dựng icon vector, sơ đồ và chữ từ visual_fallback trong JSON.")
            return
        self.cancel.clear(); self._set_busy(True)
        self.asset_file_progress.configure(value=0)
        self.asset_progress_var.set(f"Đang chuẩn bị tải {len(targets)} media...")
        self.progress.configure(value=0)
        storyboard_copy = json.loads(json.dumps(self.storyboard))
        self.worker = threading.Thread(target=self._download_worker, args=(storyboard_copy,), daemon=True)
        self.worker.start()

    def _download_worker(self, storyboard: dict[str, Any]):
        downloaded = dict(self.asset_paths)
        ok, failed = 0, []
        targets = [a for a in storyboard.get("assets", []) if a.get("download_url")]
        total_assets = max(1, len(targets))
        self.q.put(("asset_progress_reset", len(targets)))
        for idx, asset in enumerate(targets, 1):
            if self.cancel.is_set(): break
            asset_id = asset["asset_id"]
            try:
                existing = downloaded.get(asset_id)
                if existing and Path(existing).exists():
                    try:
                        verify_downloaded_media(Path(existing), asset.get("asset_type", "photo"))
                        self.q.put(("log", f"File local của {asset_id} đã được giải mã/kiểm tra; bỏ qua tải lại."))
                        ok += 1
                        self.q.put(("asset_file_progress", 100, f"Đã kiểm tra file có sẵn: {asset_id}"))
                        self.q.put(("progress", int(idx * 100 / total_assets), f"Đã xử lý {idx}/{len(targets)} media"))
                        continue
                    except Exception as exc:
                        self.q.put(("log", f"File local của {asset_id} không hợp lệ ({exc}); sẽ tải lại từ URL JSON."))
                        downloaded.pop(asset_id, None)

                def report_bytes(received: int, expected: Optional[int], attempt: int, attempts: int):
                    if expected and expected > 0:
                        pct = min(100.0, received * 100.0 / expected)
                        total_pct = ((idx - 1) + pct / 100.0) * 100.0 / total_assets
                        detail = (f"Đang tải {asset_id} – {received / 1024 / 1024:.2f} / "
                                  f"{expected / 1024 / 1024:.2f} MB · link {attempt}/{attempts}")
                        self.q.put(("asset_file_progress", pct, detail))
                        self.q.put(("progress", int(total_pct),
                                    f"Tổng tiến độ: {idx - 1 + pct / 100.0:.2f}/{len(targets)} asset"))
                    else:
                        # Some servers omit Content-Length; still show live bytes received.
                        detail = (f"Đang tải {asset_id} – đã nhận {received / 1024 / 1024:.2f} MB "
                                  f"(server không cung cấp tổng dung lượng) · link {attempt}/{attempts}")
                        self.q.put(("asset_file_progress", None, detail))
                        base_pct = (idx - 1) * 100.0 / total_assets
                        self.q.put(("progress", int(base_pct), f"Đang xử lý asset {idx}/{len(targets)}"))

                self.q.put(("asset_file_progress", 0, f"Chuẩn bị tải {asset_id} ({idx}/{len(targets)})..."))
                path = download_media_asset(
                    asset, self.assets_workspace, self.cancel,
                    log=lambda m: self.q.put(("log", m)),
                    progress=report_bytes,
                )
                downloaded[asset_id] = str(path)
                ok += 1
                self.q.put(("asset_file_progress", 100, f"Đã tải xong {asset_id}"))
                self.q.put(("progress", int(idx * 100 / total_assets), f"Đã tải {idx}/{len(targets)} media"))
            except InterruptedError:
                break
            except Exception as exc:
                failed.append(f"{asset_id}: {exc}")
                self.q.put(("log", f"LỖI tải {asset_id}: {exc}"))
                self.q.put(("progress", int(idx * 100 / total_assets), f"Đã xử lý {idx}/{len(targets)} media (có lỗi)"))
        self.q.put(("downloads_done", downloaded, ok, failed, self.cancel.is_set()))

    def _open_asset_source(self):
        aid = self._asset_selected()
        if not aid or not self.storyboard: return
        asset = next((a for a in self.storyboard.get("assets", []) if a["asset_id"] == aid), None)
        if not asset: return
        url = asset.get("source_page_url") or asset.get("download_url")
        if url: webbrowser.open(url)
        else: messagebox.showinfo("Thiếu nguồn", "Asset này không có source_page_url.")

    def _open_local_asset(self):
        aid = self._asset_selected()
        if not aid:
            messagebox.showinfo("Chưa chọn asset", "Chọn asset trong bảng trước.")
            return
        local_path = self.asset_paths.get(aid)
        if not local_path or not Path(local_path).exists():
            messagebox.showwarning("Chưa có media", "Asset này chưa được tải hoặc chưa được gán file.")
            return
        try:
            if os.name == "nt":
                os.startfile(local_path)
            else:
                webbrowser.open(Path(local_path).resolve().as_uri())
        except Exception as exc:
            messagebox.showerror("Không mở được media", str(exc))

    def _asset_selected(self) -> Optional[str]:
        sel = self.asset_tree.selection()
        return sel[0] if sel else None

    def _assign_asset(self):
        if not self.storyboard:
            messagebox.showwarning("Chưa có JSON", "Tải storyboard JSON trước."); return
        aid = self._asset_selected()
        if not aid:
            messagebox.showwarning("Chưa chọn asset", "Chọn một asset trong bảng trước."); return
        path = filedialog.askopenfilename(filetypes=[("Images / Videos", "*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")])
        if path:
            self.asset_paths[aid] = path
            self._populate_assets()
            self.asset_tree.selection_set(aid)
            self._save_asset_sidecar()

    def _clear_asset(self):
        aid = self._asset_selected()
        if aid:
            self.asset_paths.pop(aid, None)
            self._populate_assets(); self._save_asset_sidecar()

    def _save_asset_sidecar(self):
        if not self.json_var.get(): return
        path = Path(self.json_var.get())
        sidecar = path.with_suffix(".assets.json")
        sidecar.write_text(json.dumps(self.asset_paths, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.storyboard:
            write_asset_credits(self.storyboard, self.asset_paths, self.assets_workspace)
        self._log(f"Đã lưu asset mapping: {sidecar.name}")

    def _search_asset(self):
        self._open_asset_source()

    def _validate_current(self):
        if not self.storyboard:
            path = Path(self.json_var.get()) if self.json_var.get() else None
            if not path or not path.exists():
                messagebox.showwarning("Chưa có storyboard", "Chọn file storyboard JSON trước."); return
            self._load_storyboard(path)
            return
        errors = self.validator.validate(self.storyboard)
        if errors:
            messagebox.showerror("JSON lỗi", "\n".join(errors[:30]))
        else:
            messagebox.showinfo("JSON hợp lệ", f"Storyboard schema {self.storyboard['schema_version']} hợp lệ.\nScenes: {len(self.storyboard['scenes'])}\nSegments: {len(self.storyboard['source_segments'])}")

    def _start_alignment(self):
        if not self._require_ready(): return
        if self.worker and self.worker.is_alive(): return
        audio = Path(self.audio_var.get())
        self._set_busy(True)
        self.cancel.clear()
        self.worker = threading.Thread(target=self._alignment_worker, args=(audio,), daemon=True)
        self.worker.start()

    def _alignment_worker(self, audio: Path):
        try:
            words, detected, aligned_seg, aligned_anchor = run_whisper_alignment(
                audio, self.storyboard, WHISPER_DIR,
                log=lambda m: self.q.put(("log",m)), cancel=self.cancel)
            self.asr_words = words
            self.detected_language = detected
            self.aligned_segments = aligned_seg
            self.aligned_anchors = aligned_anchor
            src_chars = sum(len(normalize_text(s["text"])) for s in self.storyboard.get("source_segments", []))
            asr_chars = sum(len(normalize_text(w["text"])) for w in words)
            coverage = min(1.0, asr_chars / max(1,src_chars))
            self.q.put(("align_done", coverage))
        except Exception as exc:
            self.q.put(("error", str(exc)))

    def _require_ready(self) -> bool:
        if not self.storyboard:
            messagebox.showwarning("Thiếu storyboard", "Hãy tải storyboard JSON hợp lệ trước."); return False
        audio = Path(self.audio_var.get()) if self.audio_var.get() else None
        if not audio or not audio.exists() or audio.suffix.lower() not in AUDIO_EXTS:
            messagebox.showwarning("Thiếu audio", "Chọn audio MP3/WAV/M4A... trước."); return False
        return True

    def _start_render(self):
        if not self._require_ready(): return
        if self.worker and self.worker.is_alive(): return
        output = Path(self.output_var.get())
        if output.suffix.lower() != ".mp4": output = output.with_suffix(".mp4")
        output.parent.mkdir(parents=True, exist_ok=True)
        audio = Path(self.audio_var.get())
        self.cancel.clear()
        settings = {"resolution": self.resolution_var.get(), "fps": int(self.fps_var.get()),
                    "subtitles": bool(self.subtitles_var.get())}
        missing_assets = [a for a in self.storyboard.get("assets", [])
                          if a.get("download_url") and not (self.asset_paths.get(a["asset_id"]) and Path(self.asset_paths[a["asset_id"]]).exists())]
        if missing_assets:
            ids = ", ".join(a["asset_id"] for a in missing_assets)
            if messagebox.askyesno("Media tùy chọn chưa tải", "Có media ngoài chưa tải được. Bạn có muốn thử tải trước không?\n\nNếu chọn No, app vẫn render bằng hình icon vector, sơ đồ và typography nằm trong visual_fallback của JSON.\n\n" + ids):
                self._start_download_assets()
                return
            self._log("Bỏ qua media chưa tải; renderer sẽ dùng visual_fallback cho các cảnh tương ứng.")
        self._set_busy(True)
        self.worker = threading.Thread(target=self._render_worker, args=(audio, output, settings), daemon=True)
        self.worker.start()

    def _render_worker(self, audio: Path, output: Path, settings: dict[str, Any]):
        try:
            duration = probe_duration(audio)
            self.q.put(("log", f"Audio duration: {duration:.2f}s"))
            storyboard = json.loads(json.dumps(self.storyboard))
            local_words = list(self.asr_words)
            local_detected = self.detected_language
            local_aligned_segments = self.aligned_segments
            local_aligned_anchors = self.aligned_anchors
            if settings["subtitles"] and not local_words:
                self.q.put(("log", "Chưa có word timestamps. Tự động chạy Whisper alignment để tạo karaoke subtitles..."))
                local_words, local_detected, local_aligned_segments, local_aligned_anchors = run_whisper_alignment(audio, storyboard, WHISPER_DIR,
                    log=lambda m:self.q.put(("log",m)), cancel=self.cancel)
                self.asr_words = local_words
                self.detected_language = local_detected
                self.aligned_segments = local_aligned_segments
                self.aligned_anchors = local_aligned_anchors
            timings = build_runtime_timings(storyboard, duration, local_aligned_segments, local_aligned_anchors)
            w, h = {"720x1280 (khuyên dùng)": (720,1280), "1080x1920 (Full HD)": (1080,1920), "1920x1080 (Landscape)": (1920,1080), "1080x1080 (Square)": (1080,1080)}[settings["resolution"]]
            render_storyboard_video(audio, output, storyboard, timings, self.asset_paths, (w,h), settings["fps"], duration,
                                    lambda p,m:self.q.put(("progress",p,m)), lambda m:self.q.put(("log",m)), self.cancel,
                                    caption_words=local_words, show_subtitles=settings["subtitles"],
                                    detected_language=local_detected)
            write_asset_credits(storyboard, self.asset_paths, output.parent)
            self.q.put(("done", str(output)))
        except InterruptedError as exc:
            self.q.put(("cancelled", str(exc)))
        except Exception as exc:
            self.q.put(("error", str(exc)))

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for b in (self.validate_btn, self.align_btn, self.render_btn): b.configure(state=state)
        if hasattr(self, "download_btn"):
            self.download_btn.configure(state=state)
        if hasattr(self, "karaoke_preview_btn"):
            self.karaoke_preview_btn.configure(state=state)
            self.karaoke_export_btn.configure(state=state)
        self.cancel_btn.configure(state="normal" if busy else "normal")
        self.status_var.set("Đang xử lý..." if busy else "Sẵn sàng.")

    def _cancel(self):
        self.cancel.set()
        self.status_var.set("Đang yêu cầu hủy...")

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "log": self._log(item[1])
                elif kind == "reading_progress":
                    self.reading_progress.configure(value=item[1])
                    self.reading_progress_var.set(item[2])
                    self.progress.configure(value=item[1]); self.status_var.set(item[2])
                elif kind == "reading_web_loaded":
                    self.reading_web_fetch_btn.configure(state="normal")
                    self.reading_web_load_btn.configure(state="normal" if item[1] else "disabled")
                    self._reading_apply_web_content(item[1], item[2], item[3], item[4])
                    self.status_var.set("Đã lấy nội dung bài đọc từ website.")
                elif kind == "reading_web_error":
                    self.reading_web_fetch_btn.configure(state="normal")
                    self.reading_web_load_btn.configure(state="normal" if self.reading_web_items else "disabled")
                    self.reading_progress_var.set("Không thể lấy nội dung website: " + item[1])
                    self._log("Reading Along web import error: " + item[1])
                    messagebox.showerror("Không thể lấy nội dung website", item[1])
                elif kind == "reading_done":
                    self.reading_export_btn.configure(state="normal")
                    self.reading_preview_btn.configure(state="normal")
                    self.reading_progress.configure(value=100)
                    self.reading_progress_var.set(f"Hoàn tất: {item[2]} đơn vị đọc · {item[3]:.1f}s · timing: {item[4]}")
                    self.status_var.set("Đã xuất Reading Along: " + item[1])
                    self._log(f"Reading Along exported: {item[1]} | {item[2]} units | {item[4]}.")
                    messagebox.showinfo("Hoàn tất", f"Đã tạo video Reading Along:\n{item[1]}\n\nSố đơn vị đọc: {item[2]}\nPhương pháp timing: {item[4]}")
                elif kind == "reading_error":
                    self.reading_export_btn.configure(state="normal")
                    self.reading_preview_btn.configure(state="normal")
                    self.reading_progress_var.set("Xuất video bị lỗi.")
                    self._log("Reading Along error: " + item[1])
                    messagebox.showerror("Reading Along error", item[1])
                elif kind == "reading_cancelled":
                    self.reading_export_btn.configure(state="normal")
                    self.reading_preview_btn.configure(state="normal")
                    self.reading_progress_var.set("Đã hủy xuất video.")
                    self._log(item[1])
                elif kind == "merge_progress":
                    self.merge_progress.configure(value=item[1]); self.merge_progress_var.set(item[2]); self.status_var.set(item[2])
                elif kind == "merge_done":
                    self.merge_start_btn.configure(state="normal"); self.merge_progress.configure(value=100)
                    self.merge_progress_var.set(f"Hoàn tất: {item[1]} thành công, {item[2]} lỗi. Lưu tại {item[3]}")
                    self._log(f"Merge completed: {item[1]} success, {item[2]} failed.")
                    messagebox.showinfo("Hoàn tất ghép video",f"Thành công: {item[1]}\nLỗi: {item[2]}\nThư mục: {item[3]}")
                elif kind == "merge_cancelled":
                    self.merge_start_btn.configure(state="normal"); self.merge_progress_var.set(f"Đã hủy. Thành công {item[2]}, lỗi {item[3]}."); self._log(item[1])
                elif kind == "merge_error":
                    self.merge_start_btn.configure(state="normal"); self.merge_progress_var.set("Có lỗi khi ghép video."); messagebox.showerror("Merge error",item[1])
                elif kind == "progress": self.progress.configure(value=item[1]); self.status_var.set(item[2])
                elif kind == "karaoke_progress":
                    self.karaoke_progress.configure(value=item[1]); self.karaoke_progress_var.set(item[2])
                    self.progress.configure(value=item[1]); self.status_var.set(item[2])
                elif kind == "asset_progress_reset":
                    if self._asset_progress_running:
                        self.asset_file_progress.stop()
                        self._asset_progress_running = False
                    self.asset_file_progress.configure(mode="determinate", value=0)
                    self.asset_progress_var.set(f"Bắt đầu tải {item[1]} media...")
                elif kind == "asset_file_progress":
                    if item[1] is None:
                        # Unknown Content-Length: use an animated indeterminate bar
                        # while the live byte counter in the label keeps increasing.
                        if not self._asset_progress_running:
                            self.asset_file_progress.configure(mode="indeterminate")
                            self.asset_file_progress.start(12)
                            self._asset_progress_running = True
                    else:
                        if self._asset_progress_running:
                            self.asset_file_progress.stop()
                            self._asset_progress_running = False
                        self.asset_file_progress.configure(mode="determinate", value=item[1])
                    self.asset_progress_var.set(item[2])
                elif kind == "downloads_done":
                    self.asset_paths = item[1]
                    self._save_asset_sidecar()
                    self._populate_assets()
                    self._set_busy(False)
                    if self._asset_progress_running:
                        self.asset_file_progress.stop()
                        self._asset_progress_running = False
                    self.asset_file_progress.configure(mode="determinate")
                    self.progress.configure(value=100 if not item[3] and not item[4] else self.progress.cget("value"))
                    self.asset_file_progress.configure(value=100 if not item[4] and not item[3] else self.asset_file_progress.cget("value"))
                    if item[4]:
                        self.asset_progress_var.set(f"Đã hủy. Đã tải/kiểm tra {item[2]} media; một số asset có thể chưa hoàn tất.")
                    elif item[3]:
                        self.asset_progress_var.set(f"Kết thúc với lỗi: {len(item[3])} asset không tải được.")
                    else:
                        self.asset_progress_var.set(f"Hoàn tất: {item[2]} / {len([a for a in (self.storyboard or {}).get('assets', []) if a.get('download_url')])} media.")
                    if item[3]:
                        messagebox.showwarning("Một số media không tải được", f"Đã tải {item[2]} file. Còn lỗi:\n\n" + "\n".join(item[3][:15]) + "\n\nKhông sao: khi render, app sẽ tự dùng visual_fallback icon vector trong JSON cho các asset thiếu.")
                    elif item[4]:
                        self.status_var.set("Đã hủy tải media.")
                    else:
                        self.status_var.set(f"Đã tải xong {item[2]} media.")
                        self._log(f"Tải media hoàn tất: {item[2]} file.")
                elif kind == "align_done":
                    self._set_busy(False); self.status_var.set(f"Căn chỉnh xong: {item[1]:.0%} nội dung khớp ASR.")
                    messagebox.showinfo("Audio alignment", f"Đã căn chỉnh xấp xỉ {item[1]:.0%} nội dung.\nKiểm tra log trước khi render.")
                elif kind == "done":
                    self._set_busy(False); self.progress.configure(value=100); self.status_var.set("Hoàn tất: " + item[1])
                    self._log("Render complete: " + item[1]); messagebox.showinfo("Hoàn tất", f"Đã tạo video:\n{item[1]}")
                elif kind == "karaoke_preview_done":
                    self._set_busy(False)
                    try:
                        with Image.open(item[1]) as im:
                            preview = im.convert("RGB")
                        preview.thumbnail((310, 620), Image.Resampling.LANCZOS)
                        self.karaoke_preview_image = ImageTk.PhotoImage(preview)
                        self.karaoke_preview_label.configure(image=self.karaoke_preview_image, text="")
                        self.status_var.set("Preview effect đã sẵn sàng.")
                        self._log("Karaoke effect preview rendered.")
                    finally:
                        Path(item[1]).unlink(missing_ok=True)
                elif kind == "karaoke_preview_error":
                    self._set_busy(False)
                    self.status_var.set("Preview subtitle bị lỗi.")
                    self._log("Preview error: " + item[1])
                    messagebox.showerror("Preview error", item[1])
                elif kind == "karaoke_done":
                    self._set_busy(False); self.progress.configure(value=100)
                    if hasattr(self, "karaoke_progress"):
                        self.karaoke_progress.configure(value=100); self.karaoke_progress_var.set("Hoàn tất 100%")
                    self.status_var.set("Đã xuất video karaoke: " + item[1])
                    self._log("Karaoke export complete: " + item[1])
                    messagebox.showinfo("Hoàn tất", f"Đã burn karaoke subtitle vào video:\n{item[1]}")
                elif kind == "error":
                    self._set_busy(False); self._log("LỖI: " + item[1]); self.status_var.set("Có lỗi.")
                    messagebox.showerror("Lỗi", item[1])
                elif kind == "cancelled":
                    self._set_busy(False); self._log(item[1]); self.status_var.set("Đã hủy.")
        except queue.Empty:
            pass
        self.root.after(150, self._poll)


def run_whisper_alignment(audio: Path, storyboard: dict[str, Any], model_root: Path,
                          log=lambda _m: None, cancel: Optional[threading.Event] = None):
    cancel = cancel or threading.Event()
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise RuntimeError("Chưa cài faster-whisper. Chạy install_alignment.bat; sau đó bấm Render, app sẽ tự căn timestamp karaoke.\n" + str(exc))
    model_dir = model_root / "small"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_ref = str(model_dir) if any(model_dir.iterdir()) else "small"
    log("Đang nạp faster-whisper small (CPU int8) để căn nội dung và timestamp từng từ...")
    model = WhisperModel(model_ref, device="cpu", compute_type="int8", download_root=str(model_root))
    lang = storyboard["project"].get("source_language", "auto")
    if lang in ("auto", "unknown", "same_as_source"): lang = None
    segs, info = model.transcribe(str(audio), language=lang, beam_size=5, word_timestamps=True, vad_filter=True)
    words=[]
    for seg in segs:
        if cancel.is_set(): raise InterruptedError("Đã hủy căn timestamp.")
        for word in (getattr(seg,"words",None) or []):
            if word.word:
                words.append({"text":word.word,"start":float(word.start),"end":float(word.end)})
    if not words:
        raise RuntimeError("Whisper không trả timestamp từng từ. Không thể tạo karaoke chính xác.")
    aligned_segments, aligned_anchors, coverage = align_source_to_asr(storyboard, words)
    if coverage < 0.45:
        raise RuntimeError(f"Transcript khớp ASR ở mức thấp ({coverage:.0%}). Hãy kiểm tra audio và text trước khi render karaoke.")
    log(f"Word alignment hoàn tất: {len(words)} từ; độ phủ so khớp ký tự {coverage:.0%}.")
    return words, (getattr(info,"language","auto") or "auto"), aligned_segments, aligned_anchors


def align_source_to_asr(storyboard: dict[str, Any], asr_words: list[dict[str, Any]]) -> tuple[dict[str, RuntimeTiming], dict[str, RuntimeTiming], float]:
    # Character-level sequence matching maps the supplied script to Whisper's timed words.
    src_chars, src_refs = [], []
    for seg in storyboard.get("source_segments", []):
        norm = normalize_text(seg["text"])
        for ch in norm:
            src_chars.append(ch); src_refs.append((seg["segment_id"], ch))
    asr_chars, asr_word_refs = [], []
    for idx, word in enumerate(asr_words):
        for ch in normalize_text(word["text"]):
            asr_chars.append(ch); asr_word_refs.append(idx)
    src = "".join(src_chars); tgt = "".join(asr_chars)
    if not src or not tgt: return {}, {}, 0.0
    matcher = SequenceMatcher(None, src, tgt, autojunk=False)
    mappings: dict[int, int] = {}
    matched = 0
    for block in matcher.get_matching_blocks():
        matched += block.size
        for i in range(block.size): mappings[block.a+i] = block.b+i
    coverage = matched / max(1, len(src))
    seg_positions: dict[str, list[int]] = {}
    for i, (sid, _) in enumerate(src_refs): seg_positions.setdefault(sid, []).append(i)
    seg_ranges = {}
    for seg in storyboard["source_segments"]:
        positions = seg_positions.get(seg["segment_id"], [])
        if not positions: continue
        mapped_word_ids = [asr_word_refs[mappings[p]] for p in positions if p in mappings]
        if mapped_word_ids:
            lo, hi = min(mapped_word_ids), max(mapped_word_ids)
            seg_ranges[seg["segment_id"]] = RuntimeTiming(max(0, asr_words[lo]["start"]), asr_words[hi]["end"], "whisper_word_timestamps")
    anchors: dict[str, RuntimeTiming] = {}
    for scene in storyboard["scenes"]:
        for el in scene.get("elements", []):
            aid = el["element_id"]
            anchor = el["sync_anchor"]
            sid = anchor["segment_id"]
            quote = anchor.get("quote", "")
            seg = next((s for s in storyboard["source_segments"] if s["segment_id"] == sid), None)
            if not seg: continue
            seg_norm = normalize_text(seg["text"])
            q_norm = normalize_text(quote) if quote else seg_norm
            pos = seg_norm.find(q_norm) if q_norm else -1
            if pos < 0:
                if sid in seg_ranges: anchors[aid] = seg_ranges[sid]
                continue
            # Find this segment's source character offset within the global concatenation.
            base = 0
            for s in storyboard["source_segments"]:
                if s["segment_id"] == sid: break
                base += len(normalize_text(s["text"]))
            source_indexes = range(base + pos, base + pos + len(q_norm))
            word_ids = [asr_word_refs[mappings[i]] for i in source_indexes if i in mappings]
            if word_ids:
                lo, hi = min(word_ids), max(word_ids)
                anchors[aid] = RuntimeTiming(max(0, asr_words[lo]["start"]), asr_words[hi]["end"], "whisper_word_timestamps")
    return seg_ranges, anchors, coverage


def build_runtime_timings(storyboard: dict[str, Any], duration: float, aligned_segments: dict[str, RuntimeTiming], aligned_anchors: dict[str, RuntimeTiming]):
    segments = storyboard.get("source_segments", [])
    # First prefer Whisper-aligned segment times; otherwise use timestamps from the script.
    # A final segment with end_s=null ends at the audio duration, not at zero.
    seg_times: dict[str, RuntimeTiming] = {}
    for i, s in enumerate(segments):
        sid = s["segment_id"]
        if sid in aligned_segments:
            seg_times[sid] = aligned_segments[sid]
            continue
        raw_start, raw_end = s.get("start_s"), s.get("end_s")
        next_start = None
        for nxt in segments[i+1:]:
            if nxt.get("start_s") is not None:
                next_start = float(nxt["start_s"])
                break
        if raw_start is not None:
            start = float(raw_start)
            end = float(raw_end) if raw_end is not None else (next_start if next_start is not None else duration)
            if end > start:
                seg_times[sid] = RuntimeTiming(max(0.0, start), min(duration, end), "script_timestamp")
        elif raw_end is not None:
            prev_end = 0.0
            for prev in reversed(segments[:i]):
                if prev.get("end_s") is not None:
                    prev_end = float(prev["end_s"]); break
                if prev.get("start_s") is not None:
                    prev_end = float(prev["start_s"]); break
            if float(raw_end) > prev_end:
                seg_times[sid] = RuntimeTiming(prev_end, min(duration, float(raw_end)), "estimated_start_from_previous")
    # Fill only segments with no usable timing. Keep already known time ranges intact.
    missing = [s for s in segments if s["segment_id"] not in seg_times]
    if missing:
        lengths = [max(1, len(normalize_text(s["text"]))) for s in missing]
        total = sum(lengths) or 1
        cursor = 0.0
        for s, length in zip(missing, lengths):
            span = duration * length / total
            seg_times[s["segment_id"]] = RuntimeTiming(cursor, min(duration, cursor + span), "estimated_from_text_length")
            cursor += span
    timings: dict[str, Any] = {"segments": seg_times, "anchors": dict(aligned_anchors), "scenes": {}}
    for scene in storyboard["scenes"]:
        segment_ranges = [seg_times[sid] for sid in scene["segment_ids"] if sid in seg_times]
        if segment_ranges:
            start = min(x.start for x in segment_ranges); end = max(x.end for x in segment_ranges)
        else:
            start = scene.get("provisional_start_s") if scene.get("provisional_start_s") is not None else 0.0
            end = scene.get("provisional_end_s") if scene.get("provisional_end_s") is not None else duration
        start = max(0.0, min(duration, float(start)))
        end = max(start + 0.05, min(duration, float(end)))
        timings["scenes"][scene["scene_id"]] = RuntimeTiming(start, end, "mixed")
    return timings


def hex_rgb(value: str, fallback=(22, 32, 49)):
    try:
        v = value.lstrip("#")
        return tuple(int(v[i:i+2], 16) for i in (0,2,4))
    except Exception:
        return fallback


def lerp(a, b, f): return int(a + (b-a)*max(0.0, min(1.0, f)))


def cover_image(path: Path, size: tuple[int,int]) -> Image.Image:
    if path.suffix.lower() in VIDEO_EXTS:
        with tempfile.TemporaryDirectory(prefix="evs_frame_") as td:
            out = Path(td) / "frame.jpg"
            p = run_ffmpeg(["-y", "-ss", "0.5", "-i", str(path), "-frames:v", "1", str(out)], timeout=120)
            if p.returncode != 0 or not out.exists():
                raise RuntimeError(f"Không lấy được frame từ video asset: {path.name}")
            img = Image.open(out).convert("RGB")
            return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Wrap mixed Japanese/English text by words while preserving real spaces and explicit newlines."""
    if not text:
        return []

    def tokenise(paragraph: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        while i < len(paragraph):
            ch = paragraph[i]
            if ch.isspace():
                j = i + 1
                while j < len(paragraph) and paragraph[j].isspace():
                    j += 1
                tokens.append(paragraph[i:j])
                i = j
                continue
            # Keep English / numeric words intact so wrapping never removes spaces or splits words.
            if ch.isascii() and (ch.isalnum() or ch in "'’"):
                j = i + 1
                while j < len(paragraph):
                    c = paragraph[j]
                    if c.isascii() and (c.isalnum() or c in "'’-"):
                        j += 1
                    else:
                        break
                tokens.append(paragraph[i:j])
                i = j
                continue
            # CJK scripts are naturally written without inter-word spaces; wrap at glyph boundaries.
            tokens.append(ch)
            i += 1
        return tokens

    lines: list[str] = []
    paragraphs = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for paragraph in paragraphs:
        tokens = tokenise(paragraph)
        current = ""
        for token in tokens:
            # Avoid carrying leading whitespace to a new visual line, but preserve all spaces between words.
            if not current and token.isspace():
                continue
            candidate = current + token
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if current and width > max_width:
                lines.append(current.rstrip())
                current = token.lstrip() if token.isspace() else token
            else:
                current = candidate
        if current.strip():
            lines.append(current.rstrip())
        elif not lines:
            lines.append("")
    return lines


def element_timing(el: dict[str, Any], timings: dict[str, Any], seg_map: dict[str, dict], scene_time: RuntimeTiming) -> RuntimeTiming:
    aid = el["element_id"]
    if aid in timings["anchors"]:
        return timings["anchors"][aid]
    anchor = el["sync_anchor"]
    sid = anchor["segment_id"]
    if sid not in timings["segments"]:
        return scene_time
    seg_time = timings["segments"][sid]
    quote = anchor.get("quote", "")
    if not quote:
        return seg_time
    source_text = seg_map.get(sid, {}).get("text", "")
    normalized, q = normalize_text(source_text), normalize_text(quote)
    at = normalized.find(q)
    if at < 0 or not normalized:
        return RuntimeTiming(seg_time.start, seg_time.end, "segment_estimate")
    # Approximate phrase location within a timestamped segment. This remains marked as an estimate.
    start_ratio = at / len(normalized)
    end_ratio = min(1.0, (at + len(q)) / len(normalized))
    return RuntimeTiming(seg_time.start + (seg_time.end-seg_time.start)*start_ratio,
                         seg_time.start + (seg_time.end-seg_time.start)*end_ratio, "phrase_position_estimate")


def draw_gradient(size: tuple[int,int], base: tuple[int,int,int], t: float) -> Image.Image:
    # Build a 1-pixel-wide vertical gradient and scale it; avoid Python per-pixel loops.
    w, h = size
    c1 = base
    c2 = (max(0, base[0]-10), max(0, base[1]-8), max(0, base[2]-12))
    strip = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(strip)
    for y in range(h):
        f = y / max(1, h-1)
        drift = 0.025 * math.sin(t*0.3 + f*4)
        col = tuple(lerp(c1[i], c2[i], min(1, max(0, f+drift))) for i in range(3))
        d.point((0, y), fill=col)
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def draw_asset_placeholder(img: Image.Image, rect: tuple[int,int,int,int], text: str, accent: tuple[int,int,int]):
    x,y,w,h=rect
    d=ImageDraw.Draw(img,"RGBA")
    d.rounded_rectangle((x,y,x+w,y+h), radius=max(12,w//40), fill=(255,255,255,24), outline=(*accent,190), width=max(2,w//360))
    font=get_font(text, max(18,min(34,w//18)), True)
    lines=wrap_text(d,text,font,w-40)
    yy=y+h//2-(len(lines)*(font.size+8))//2
    for line in lines:
        box=d.textbbox((0,0),line,font=font)
        d.text((x+(w-(box[2]-box[0]))//2,yy),line,font=font,fill=(240,246,255,235))
        yy += font.size+8


@dataclass
class CaptionToken:
    text: str
    start: float
    end: float
    space_before: bool = False


@dataclass
class CaptionLine:
    words: list[CaptionToken]
    start: float
    end: float


def _is_cjk_char(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    return ((0x3040 <= code <= 0x30FF) or (0x3400 <= code <= 0x9FFF) or
            (0xF900 <= code <= 0xFAFF) or (0xAC00 <= code <= 0xD7AF))


def _is_latin_word(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+)*[.,!?;:]*", text or ""))


def caption_needs_space(previous: Optional[CaptionToken], current: CaptionToken) -> bool:
    """Use spaces for English word boundaries even when a line also contains Japanese text."""
    if previous is None:
        return False
    if current.space_before:
        return True
    return _is_latin_word(previous.text) and _is_latin_word(current.text)


def _split_mixed_caption_text(text: str) -> list[tuple[str, bool]]:
    """Split mixed Japanese/English transcript into caption tokens without losing English spaces."""
    result: list[tuple[str, bool]] = []
    i = 0
    pending_space = False
    closing = set("、。，．！？!?：；）)]］】〕〉》」』,.!?;:")
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            pending_space = True
            i += 1
            continue
        if ch.isascii() and ch.isalnum():
            match = re.match(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+)*", text[i:])
            token = match.group(0) if match else ch
            result.append((token, pending_space))
            pending_space = False
            i += len(token)
            continue
        if _is_cjk_char(ch):
            j = i
            while j < len(text) and _is_cjk_char(text[j]) and (j - i) < 8:
                j += 1
            token = text[i:j]
            result.append((token, pending_space))
            pending_space = False
            i = j
            continue
        if ch in closing and result:
            previous, prior_space = result[-1]
            result[-1] = (previous + ch, prior_space)
            pending_space = False
            i += 1
            continue
        result.append((ch, pending_space))
        pending_space = False
        i += 1
    return result


def build_caption_lines(asr_words: list[dict[str, Any]], source_segments: list[dict[str, Any]],
                        segment_timings: dict[str, RuntimeTiming], detected_language: str,
                        duration: float) -> list[CaptionLine]:
    """Build karaoke captions with word-level timestamps, preserving English spaces in mixed Japanese speech."""
    tokens: list[CaptionToken] = []
    if asr_words:
        for item in asr_words:
            raw_text = str(item.get("text", ""))
            text = raw_text.strip()
            if text:
                start = max(0.0, float(item.get("start", 0.0)))
                end = max(start + 0.04, float(item.get("end", start + 0.1)))
                tokens.append(CaptionToken(text, start, end, raw_text[:1].isspace()))
    else:
        # Segment-level fallback: keep English lexical tokens separate; chunk Japanese by glyphs.
        for seg in source_segments:
            timing = segment_timings.get(seg["segment_id"])
            if not timing:
                continue
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            pieces = _split_mixed_caption_text(text)
            if not pieces:
                continue
            weights = [max(1, len(piece)) for piece, _ in pieces]
            total_w = sum(weights)
            cursor = timing.start
            span = max(0.05, timing.end - timing.start)
            for (piece, space_before), weight in zip(pieces, weights):
                part = span * weight / total_w
                tokens.append(CaptionToken(piece, cursor, min(timing.end, cursor + part), space_before))
                cursor += part

    if not tokens:
        return []

    all_text = "".join(x.text for x in tokens)
    has_cjk = any(_is_cjk_char(ch) for ch in all_text) or detected_language in ("ja", "zh", "ko")
    max_chars = 18 if has_cjk else 30
    max_words = 14 if has_cjk else 7
    lines: list[CaptionLine] = []
    current: list[CaptionToken] = []
    current_len = 0
    for tok in tokens:
        extra = len(tok.text) + (1 if caption_needs_space(current[-1] if current else None, tok) else 0)
        gap = tok.start - current[-1].end if current else 0.0
        closing = tok.text[:1] in "、。，．！？!?：；）)]］】〕〉》」』,.!?;:"
        if current and not closing and (current_len + extra > max_chars or len(current) >= max_words or gap > 0.9):
            lines.append(CaptionLine(current, current[0].start, current[-1].end))
            current, current_len = [], 0
            extra = len(tok.text)
        current.append(tok)
        current_len += extra
    if current:
        lines.append(CaptionLine(current, current[0].start, current[-1].end))
    return lines


def draw_bottom_karaoke_caption(img: Image.Image, line: Optional[CaptionLine], t: float,
                                detected_language: str = "auto") -> None:
    """Clean educational karaoke: inactive words black, spoken word purple, on a light caption card."""
    if not line:
        return
    draw = ImageDraw.Draw(img, "RGBA")
    words = line.words
    text_all = "".join(w.text for w in words)
    size = max(25, int(img.width * (0.046 if img.width < 1000 else 0.041)))
    font = get_font(text_all, size, True)
    max_width = int(img.width * 0.88)

    # Wrap into at most two rows, preserving CJK glyph flow.
    rows: list[list[CaptionToken]] = [[]]
    row_widths = [0]
    for token in words:
        bb = draw.textbbox((0, 0), token.text, font=font)
        tw = bb[2] - bb[0]
        gap = int(size * 0.22) if rows[-1] and caption_needs_space(rows[-1][-1], token) else 0
        if rows[-1] and row_widths[-1] + gap + tw > max_width:
            rows.append([]); row_widths.append(0); gap = 0
        rows[-1].append(token)
        row_widths[-1] += gap + tw
    rows = [r for r in rows if r][:2]
    if not rows:
        return

    line_h = int(size * 1.38)
    pad_x, pad_y = int(size * 0.62), int(size * 0.38)
    row_measures = []
    max_row_width = 0
    for row in rows:
        measures, total_w = [], 0
        for token in row:
            bb = draw.textbbox((0, 0), token.text, font=font)
            tw = bb[2] - bb[0]
            previous = measures[-1][0] if measures else None
            gap = int(size * 0.22) if caption_needs_space(previous, token) else 0
            measures.append((token, tw, gap))
            total_w += tw + gap
        row_measures.append((measures, total_w))
        max_row_width = max(max_row_width, total_w)

    total_h = len(rows) * line_h
    center_y = int(img.height * 0.855)
    top0 = center_y - total_h // 2
    card_left = (img.width - max_row_width) // 2 - pad_x
    card_right = (img.width + max_row_width) // 2 + pad_x
    card_top = top0 - pad_y
    card_bottom = top0 + total_h - int(size * .12) + pad_y

    # Subtle drop shadow and white caption panel.
    shadow = (0, 0, 0, 30)
    draw.rounded_rectangle((card_left, card_top + 7, card_right, card_bottom + 7),
                           radius=max(14, size // 2), fill=shadow)
    draw.rounded_rectangle((card_left, card_top, card_right, card_bottom),
                           radius=max(14, size // 2), fill=(255, 255, 255, 246),
                           outline=(226, 219, 248, 255), width=max(2, size // 24))

    purple = (124, 58, 237, 255)       # #7C3AED
    purple_pale = (245, 240, 255, 255)
    ink = (25, 32, 45, 255)
    for ridx, (measures, total_w) in enumerate(row_measures):
        x = (img.width - total_w) // 2
        y = top0 + ridx * line_h
        for token, tw, gap in measures:
            x += gap
            active = token.start <= t <= token.end + 0.025
            if active:
                # A quiet lavender capsule, with purple text; inactive text remains black.
                draw.rounded_rectangle((x - 5, y - 4, x + tw + 5, y + size + 6),
                                       radius=max(7, size // 5), fill=purple_pale)
                fill = purple
            else:
                fill = ink
            draw.text((x, y), token.text, font=font, fill=fill)
            x += tw


def current_caption(lines: list[CaptionLine], t: float) -> Optional[CaptionLine]:
    # Use the first line active at time t; a short tail avoids captions disappearing abruptly.
    for line in lines:
        if line.start - 0.06 <= t <= line.end + 0.28:
            return line
    return None


def read_video_asset_frame(cap, local_time: float, target_size: tuple[int, int]) -> Optional[Image.Image]:
    try:
        import cv2
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1
        clip_duration = max(0.04, frame_count / max(1.0, fps))
        seek_time = max(0.0, local_time) % clip_duration
        cap.set(cv2.CAP_PROP_POS_MSEC, seek_time * 1000.0)
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        return ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS)
    except Exception:
        return None


def _mix_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    if factor >= 0:
        return tuple(lerp(c, 255, min(1.0, factor)) for c in color)
    return tuple(lerp(c, 0, min(1.0, -factor)) for c in color)


def _draw_arrow_head(draw: ImageDraw.ImageDraw, tip: tuple[int, int], angle: float,
                     color: tuple[int, int, int, int], size: int) -> None:
    a1 = angle + math.radians(150)
    a2 = angle - math.radians(150)
    p1 = (tip[0] + math.cos(a1) * size, tip[1] + math.sin(a1) * size)
    p2 = (tip[0] + math.cos(a2) * size, tip[1] + math.sin(a2) * size)
    draw.polygon([tip, p1, p2], fill=color)


def _draw_bootstrap_style_icon(draw: ImageDraw.ImageDraw, shape: str,
                               rect: tuple[int, int, int, int], accent: tuple[int, int, int],
                               ink: tuple[int, int, int], t: float = 0.0) -> None:
    """Draw a crisp, flat, Bootstrap-inspired educational icon using Pillow vector primitives."""
    x1, y1, x2, y2 = rect
    w, h = max(1, x2-x1), max(1, y2-y1)
    cx, cy = x1+w/2, y1+h/2
    unit = max(2, int(min(w, h) / 18))
    sw = max(3, int(min(w, h) / 24))
    def xy(px, py): return (int(x1+px*w), int(y1+py*h))
    def line(points, fill=ink, width=sw):
        draw.line([xy(a,b) for a,b in points], fill=(*fill,255), width=width, joint="curve")
    def rr(box, radius, fill=None, outline=ink, width=sw):
        a,b,c,d=box
        draw.rounded_rectangle((int(x1+a*w),int(y1+b*h),int(x1+c*w),int(y1+d*h)),
                               radius=max(2,int(min(w,h)*radius)),
                               fill=(*fill,255) if fill else None,
                               outline=(*outline,255) if outline else None, width=width)
    def ellipse(box, fill=None, outline=ink, width=sw):
        a,b,c,d=box
        draw.ellipse((int(x1+a*w),int(y1+b*h),int(x1+c*w),int(y1+d*h)),
                     fill=(*fill,255) if fill else None,
                     outline=(*outline,255) if outline else None, width=width)
    def poly(points, fill=None, outline=ink, width=sw):
        pts=[xy(a,b) for a,b in points]
        draw.polygon(pts, fill=(*fill,255) if fill else None)
        if outline:
            draw.line(pts+[pts[0]], fill=(*outline,255), width=width, joint="curve")

    # Semantic teaching pictograms: use concrete visual metaphors, not decorative cubes.
    if shape == "eye":
        draw.ellipse((int(x1+.08*w),int(y1+.25*h),int(x1+.92*w),int(y1+.75*h)), fill=(255,255,255,255), outline=(*ink,255), width=sw)
        draw.ellipse((int(x1+.36*w),int(y1+.29*h),int(x1+.64*w),int(y1+.71*h)), fill=(*accent,255), outline=(*ink,255), width=max(2,sw//2))
        draw.ellipse((int(x1+.44*w),int(y1+.39*h),int(x1+.56*w),int(y1+.61*h)), fill=(255,255,255,255))
    elif shape == "calendar":
        rr((.15,.17,.85,.88),.08,fill=(255,255,255),outline=ink)
        rr((.15,.17,.85,.38),.07,fill=accent,outline=ink)
        for px in (.32,.50,.68):
            for py in (.51,.66,.79): ellipse((px-.035,py-.025,px+.035,py+.025),fill=(100,116,139),outline=None,width=0)
        line([(.32,.10),(.32,.27)],fill=ink,width=max(3,sw))
        line([(.68,.10),(.68,.27)],fill=ink,width=max(3,sw))
    elif shape == "photo_album":
        rr((.15,.12,.85,.88),.07,fill=(255,255,255),outline=ink)
        rr((.23,.20,.77,.80),.04,fill=(222,238,255),outline=(160,180,205),width=max(2,sw//2))
        ellipse((.31,.29,.47,.45),fill=(255,207,92),outline=None,width=0)
        poly([(.27,.70),(.43,.50),(.55,.62),(.65,.48),(.75,.70)],fill=(92,174,128),outline=None,width=0)
        line([(.15,.30),(.85,.30)],fill=accent,width=max(3,sw//2))
    elif shape == "thought_bubble":
        ellipse((.12,.12,.82,.70),fill=(255,255,255),outline=ink)
        ellipse((.23,.72,.40,.88),fill=(255,255,255),outline=ink)
        ellipse((.12,.87,.20,.95),fill=accent,outline=ink)
        for px in (.34,.50,.66): ellipse((px-.035,.39,px+.035,.46),fill=accent,outline=None,width=0)
    elif shape == "bird":
        ellipse((.25,.30,.72,.72),fill=accent,outline=ink)
        ellipse((.58,.20,.82,.45),fill=(255,207,92),outline=ink)
        poly([(.78,.29),(.96,.36),(.78,.42)],fill=(245,158,11),outline=ink)
        poly([(.29,.48),(.05,.27),(.16,.62),(.39,.67)],fill=(104,164,220),outline=ink)
        ellipse((.70,.26,.74,.30),fill=ink,outline=None,width=0)
        line([(.45,.70),(.42,.84)],fill=ink,width=max(3,sw//2))
        line([(.58,.70),(.61,.84)],fill=ink,width=max(3,sw//2))
    elif shape == "clock":
        ellipse((.12,.12,.88,.88),fill=(255,255,255),outline=ink)
        line([(.50,.50),(.50,.27)],fill=accent,width=max(4,sw))
        line([(.50,.50),(.70,.62)],fill=accent,width=max(4,sw))
        ellipse((.46,.46,.54,.54),fill=ink,outline=None,width=0)
    elif shape in ("checkmark", "x_mark"):
        if shape == "checkmark":
            line([(.18,.53),(.40,.75),(.84,.22)],fill=(22,163,74),width=max(7,sw+3))
        else:
            line([(.24,.24),(.76,.76)],fill=(220,65,75),width=max(7,sw+3))
            line([(.76,.24),(.24,.76)],fill=(220,65,75),width=max(7,sw+3))

    # The icon area is intentionally generous; each glyph has consistent stroke weight.
    if shape == "person":
        ellipse((.39,.08,.61,.30), fill=(255,226,205), outline=ink)
        # shoulders / torso silhouette
        poly([(.22,.84),(.25,.60),(.36,.43),(.50,.38),(.64,.43),(.75,.60),(.78,.84)], fill=accent, outline=ink)
        line([(.50,.39),(.50,.77)], fill=tuple(max(0,c-25) for c in accent), width=max(2,sw//2))
    elif shape in ("cup", "glass"):
        # Water glass / cup with a soft accent fill.
        poly([(.27,.28),(.73,.28),(.67,.86),(.33,.86)], fill=(255,255,255), outline=ink)
        line([(.31,.47),(.69,.47)], fill=accent, width=max(4,sw+2))
        # small specular edge and handle
        line([(.38,.34),(.35,.76)], fill=(185,197,215), width=max(2,sw//2))
        draw.arc((int(x1+.64*w),int(y1+.38*h),int(x1+.91*w),int(y1+.72*h)),270,90,fill=(*ink,255),width=sw)
    elif shape == "speech_bubble":
        rr((.12,.16,.88,.68),.14,fill=(255,255,255),outline=ink,width=sw)
        poly([(.31,.66),(.28,.88),(.50,.69)],fill=(255,255,255),outline=ink,width=sw)
        for px in (.34,.50,.66): ellipse((px-.035,.38,px+.035,.45),fill=accent,outline=None,width=0)
    elif shape == "staircase":
        # Three rounded steps, using a single accent ladder hierarchy.
        colors=[(87,185,137), (78,145,220), (142,96,218)]
        for i,c in enumerate(colors):
            left=.10+i*.27; bottom=.86-i*.24; top=bottom-.22; right=left+.29
            rr((left,top,right,bottom),.05,fill=c,outline=ink,width=max(2,sw//2))
            draw.line([xy(left+.05,top+.08),xy(right-.05,top+.08)],fill=(255,255,255,170),width=max(2,sw//2))
    elif shape == "plant":
        rr((.30,.68,.70,.91),.08,fill=accent,outline=ink)
        line([(.50,.68),(.50,.25)],fill=(48,132,91),width=max(4,sw))
        ellipse((.19,.25,.51,.49),fill=(111,203,143),outline=(46,132,89))
        ellipse((.49,.12,.82,.37),fill=(111,203,143),outline=(46,132,89))
        ellipse((.30,.43,.60,.63),fill=(143,218,160),outline=(46,132,89))
        line([(.30,.39),(.47,.32)],fill=(46,132,89),width=max(2,sw//2))
        line([(.54,.34),(.72,.23)],fill=(46,132,89),width=max(2,sw//2))
    elif shape == "sun":
        for deg in range(0,360,45):
            a=math.radians(deg); r1=.34; r2=.46
            line([(.5+math.cos(a)*r1,.48+math.sin(a)*r1),(.5+math.cos(a)*r2,.48+math.sin(a)*r2)],fill=accent,width=max(4,sw))
        ellipse((.29,.27,.71,.69),fill=(255,207,92),outline=ink)
    elif shape == "leaf":
        poly([(.16,.57),(.30,.28),(.63,.12),(.88,.22),(.82,.55),(.56,.82),(.27,.78)],fill=(137,211,153),outline=(50,135,88))
        line([(.22,.73),(.77,.25)],fill=(50,135,88),width=max(3,sw//2))
        line([(.44,.55),(.39,.33)],fill=(50,135,88),width=max(2,sw//2))
        line([(.57,.44),(.77,.45)],fill=(50,135,88),width=max(2,sw//2))
    elif shape == "book":
        poly([(.50,.24),(.12,.14),(.12,.80),(.50,.91)],fill=(255,255,255),outline=ink)
        poly([(.50,.24),(.88,.14),(.88,.80),(.50,.91)],fill=(235,242,255),outline=ink)
        line([(.50,.24),(.50,.91)],fill=ink)
        for yy in (.39,.53,.67):
            line([(.20,yy-.04),(.43,yy)],fill=accent,width=max(2,sw//2))
            line([(.57,yy),(.80,yy-.04)],fill=accent,width=max(2,sw//2))
    elif shape in ("molecule", "atom"):
        pts=[(.50,.16),(.22,.46),(.78,.46),(.35,.82),(.68,.82)]
        for a,b in ((0,1),(0,2),(1,3),(2,4),(1,2),(3,4)):
            line([pts[a],pts[b]],fill=(124,139,163),width=max(4,sw))
        for i,(px,py) in enumerate(pts):
            r=.075 if i else .10
            ellipse((px-r,py-r,px+r,py+r),fill=accent if i%2==0 else (115,160,230),outline=ink)
    elif shape == "light_bulb":
        ellipse((.30,.10,.70,.53),fill=(255,218,110),outline=ink)
        poly([(.37,.48),(.63,.48),(.59,.68),(.41,.68)],fill=accent,outline=ink)
        line([(.42,.73),(.58,.73)],fill=ink)
        line([(.44,.80),(.56,.80)],fill=ink)
        for a in (0,45,90,135,180):
            r=math.radians(a); line([(.5+math.cos(r)*.34,.31+math.sin(r)*.34),(.5+math.cos(r)*.46,.31+math.sin(r)*.46)],fill=(223,163,49),width=max(3,sw//2))
    elif shape in ("monitor", "phone"):
        if shape=="monitor":
            rr((.12,.16,.88,.68),.06,fill=(255,255,255),outline=ink)
            rr((.19,.23,.81,.61),.035,fill=(222,235,255),outline=(177,193,217),width=max(2,sw//2))
            poly([(.43,.70),(.57,.70),(.63,.83),(.37,.83)],fill=(190,202,221),outline=ink,width=max(2,sw//2))
            rr((.29,.83,.71,.89),.05,fill=accent,outline=ink,width=max(2,sw//2))
        else:
            rr((.30,.05,.70,.95),.10,fill=(255,255,255),outline=ink)
            rr((.35,.14,.65,.82),.035,fill=(222,235,255),outline=(177,193,217),width=max(2,sw//2))
            ellipse((.47,.86,.53,.92),fill=accent,outline=None,width=0)
    elif shape == "globe":
        ellipse((.12,.12,.88,.88),fill=(226,241,255),outline=ink)
        draw.arc((int(x1+.32*w),int(y1+.12*h),int(x1+.68*w),int(y1+.88*h)),90,270,fill=(*accent,255),width=sw)
        draw.arc((int(x1+.32*w),int(y1+.12*h),int(x1+.68*w),int(y1+.88*h)),270,90,fill=(*accent,255),width=sw)
        draw.arc((int(x1+.12*w),int(y1+.34*h),int(x1+.88*w),int(y1+.66*h)),0,180,fill=(*accent,255),width=sw)
        draw.arc((int(x1+.12*w),int(y1+.34*h),int(x1+.88*w),int(y1+.66*h)),180,360,fill=(*accent,255),width=sw)
    elif shape == "magnifier":
        ellipse((.12,.08,.68,.64),fill=(241,247,255),outline=ink)
        line([(.60,.60),(.90,.90)],fill=accent,width=max(7,sw+2))
        ellipse((.26,.22,.44,.40),fill=(255,255,255),outline=None,width=0)
    elif shape in ("cube", "cuboid", "pyramid", "cone", "cylinder", "card", "arrow3d"):
        if shape in ("cube", "cuboid"):
            poly([(.50,.12),(.84,.30),(.50,.49),(.16,.30)],fill=(226,238,255),outline=ink)
            poly([(.16,.30),(.50,.49),(.50,.88),(.16,.67)],fill=(190,215,250),outline=ink)
            poly([(.50,.49),(.84,.30),(.84,.67),(.50,.88)],fill=accent,outline=ink)
        elif shape=="pyramid":
            poly([(.50,.10),(.88,.78),(.12,.78)],fill=(225,235,251),outline=ink)
            line([(.50,.10),(.50,.78)],fill=accent)
        elif shape=="cone":
            poly([(.50,.10),(.85,.78),(.15,.78)],fill=(225,235,251),outline=ink)
            draw.arc((int(x1+.15*w),int(y1+.68*h),int(x1+.85*w),int(y1+.88*h)),0,180,fill=(*accent,255),width=sw)
        elif shape=="cylinder":
            rr((.20,.25,.80,.78),.10,fill=(223,238,255),outline=ink)
            draw.ellipse((int(x1+.20*w),int(y1+.14*h),int(x1+.80*w),int(y1+.37*h)),fill=(*accent,255),outline=(*ink,255),width=sw)
            draw.arc((int(x1+.20*w),int(y1+.65*h),int(x1+.80*w),int(y1+.88*h)),0,180,fill=(*ink,255),width=sw)
        elif shape=="card":
            rr((.23,.08,.77,.92),.07,fill=(255,255,255),outline=ink)
            rr((.32,.22,.68,.30),.035,fill=accent,outline=None,width=0)
            for yy in (.43,.57,.71): rr((.33,yy,.68 if yy!=.57 else .60,yy+.035),.02,fill=(165,180,200),outline=None,width=0)
        else:
            line([(.16,.50),(.74,.50)],fill=accent,width=max(7,sw+2))
            poly([(.63,.24),(.91,.50),(.63,.76)],fill=accent,outline=ink)
    elif shape == "speech_bubble":
        rr((.12,.14,.88,.68),.12,fill=(255,255,255),outline=ink)
        poly([(.27,.65),(.25,.88),(.49,.68)],fill=(255,255,255),outline=ink)
        for px in (.34,.50,.66): ellipse((px-.035,.38,px+.035,.45),fill=accent,outline=None,width=0)
    else:
        rr((.15,.15,.85,.85),.12,fill=(255,255,255),outline=ink)
        ellipse((.35,.35,.65,.65),fill=accent,outline=None,width=0)


def draw_3d_object(img: Image.Image, obj: dict[str, Any], t: float, scene_start: float) -> tuple[int, int, int, int]:
    """Render a polished Bootstrap-inspired educational icon tile (flat vector, soft 2.5D depth)."""
    w, h = img.size
    p = obj.get("position", {})
    x = int(float(p.get("x", 0.3)) * w)
    y = int(float(p.get("y", 0.2)) * h)
    ow = max(58, int(float(p.get("width", 0.35)) * w))
    oh = max(58, int(float(p.get("height", 0.35)) * h))
    x = max(4, min(w - 8, x)); y = max(4, min(int(h * .74) - 8, y))
    ow = max(42, min(ow, w - x - 4)); oh = max(42, min(oh, int(h * .74) - y - 4))
    shape_name = obj.get("shape", "cube")
    # Most pictograms live in balanced icon tiles; only process/staircase shapes keep a wide box.
    if shape_name not in ("staircase", "arrow3d"):
        side = min(ow, oh)
        x += (ow - side) // 2
        y += (oh - side) // 2
        ow = oh = side
    anim = obj.get("animation", "none")
    local = max(0.0, t - scene_start)
    progress = min(1.0, max(.0, local / .45))
    if anim in ("rise", "draw_in", "float"):
        y += int((1-progress) * min(24, h*.022)) if anim in ("rise", "draw_in") else int(math.sin(local*1.2)*3)
    pulse = 1.0 + (0.012 * math.sin(local * 2.0) if anim in ("pulse", "glow") else 0.0)
    if pulse != 1.0:
        nw, nh = int(ow*pulse), int(oh*pulse)
        x -= (nw-ow)//2; y -= (nh-oh)//2; ow,oh=nw,nh
    rect=(x,y,x+ow,y+oh)
    d=ImageDraw.Draw(img,"RGBA")
    accent=hex_rgb(obj.get("color", "#7C3AED"),(124,58,237))
    ink=(45,55,72)
    variant = obj.get("variant", "soft")
    tile_variant = variant in ("soft", "glass", "outlined")
    radius=max(14,min(30,int(min(ow,oh)*.10)))
    pale=tuple(lerp(c,255,.88) for c in accent)
    if tile_variant:
        # Card-style vocabulary/panel mode.
        d.rounded_rectangle((x+3,y+7,x+ow+3,y+oh+7),radius=radius,fill=(31,41,55,24))
        fill_alpha = 220 if variant == "glass" else 255
        d.rounded_rectangle(rect,radius=radius,fill=(*pale,fill_alpha),
                            outline=((*accent,180) if variant == "outlined" else (225,231,240,255)),
                            width=max(1,w//650))
        d.rounded_rectangle((x+int(ow*.08),y+int(oh*.08),x+int(ow*.16),y+int(oh*.92)),
                            radius=max(4,ow//70),fill=(*accent,210))
    else:
        # Free-standing semantic pictogram mode for coherent character/object scenes.
        shadow_r = max(12, int(min(ow,oh)*.38))
        d.ellipse((x+ow//2-shadow_r+3,y+oh//2-shadow_r+6,x+ow//2+shadow_r+3,y+oh//2+shadow_r+6),
                  fill=(31,41,55,14))
        if variant == "wireframe":
            d.ellipse((x+ow//2-shadow_r,y+oh//2-shadow_r,x+ow//2+shadow_r,y+oh//2+shadow_r),
                      outline=(*accent,75),width=max(2,w//500))
    shape=obj.get("shape","cube")
    if shape == "staircase" and ow > oh * 1.18:
        icon_rect=(x+int(ow*.10),y+int(oh*.14),x+int(ow*.90),y+int(oh*.86))
    else:
        has_label = bool(obj.get("label"))
        factor = (.58 if tile_variant else .68) if has_label else (.66 if tile_variant else .84)
        side=max(32,int(min(ow,oh)*factor))
        icx=x+ow//2
        icy=y+int(oh*(.40 if has_label else .50))
        icon_rect=(icx-side//2,icy-side//2,icx+side//2,icy+side//2)
    _draw_bootstrap_style_icon(d,shape,icon_rect,accent,ink,local)
    label=obj.get("label")
    if label:
        # Labels remain in their own narrow badge, never over the pictogram.
        band_top = y + int(oh*.79)
        d.rounded_rectangle((x+int(ow*.17), band_top, x+int(ow*.91), y+oh-int(oh*.04)),
                            radius=max(5,int(oh*.035)), fill=(255,255,255,230))
        font_size=max(12,min(23,int(w*.019)))
        font=get_font(str(label),font_size,True)
        label_text=str(label)
        while d.textbbox((0,0),label_text,font=font)[2] > ow*.68 and font_size>11:
            font_size-=1; font=get_font(label_text,font_size,True)
        bb=d.textbbox((0,0),label_text,font=font); tw,th=bb[2]-bb[0],bb[3]-bb[1]
        lx=x+int(ow*.54)-tw//2; ly=band_top+max(0,(int(oh*.15)-th)//2)
        d.text((lx,ly),label_text,font=font,fill=(39,50,67,255))
    return rect


def _rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int], gap: int = 0) -> bool:
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def _fallback_object_slots(count: int, layout: str = "hero_illustration") -> list[tuple[float, float, float, float]]:
    """Layout-aware normalized slots; all patterns have built-in separation."""
    if count <= 0:
        return []
    if count == 1:
        if layout in ("two_column", "comparison_cards"):
            return [(0.15, .30, .24, .24)]
        if layout == "three_column":
            return [(0.39, .31, .22, .20)]
        if layout == "summary_grid":
            return [(0.14, .18, .22, .20)]
        if layout == "process_flow":
            return [(0.39, .31, .22, .20)]
        if layout == "timeline":
            return [(0.36, .33, .28, .20)]
        if layout == "staircase":
            return [(0.41, .42, .18, .18)]
        return [(0.36, 0.27, 0.28, 0.28)]

    def horizontal(n: int, y: float = .30, cell: float | None = None):
        gap = .04
        width = min(cell or .22, (0.82 - gap * (n - 1)) / n)
        total = n * width + (n - 1) * gap
        left = (1.0 - total) / 2
        return [(left + i * (width + gap), y, width, .20) for i in range(n)]

    def grid(n: int):
        cols = 2 if n <= 4 else 3 if n <= 9 else 4
        rows = math.ceil(n / cols)
        cell_w = 0.23 if cols == 2 else 0.22 if cols == 3 else 0.18
        cell_h = min(0.20, 0.52 / rows)
        gap_x = (0.82 - cols * cell_w) / max(1, cols - 1)
        gap_y = (0.56 - rows * cell_h) / max(1, rows - 1)
        return [(0.09 + col * (cell_w + gap_x),
                 0.145 + row * (cell_h + gap_y), cell_w, cell_h)
                for row in range(rows) for col in range(cols)][:n]

    if layout in ("three_column", "timeline", "process_flow") and count <= 4:
        return horizontal(count, .31, .22 if count <= 3 else .18)
    if layout in ("two_column", "comparison_cards") and count <= 4:
        if count == 2:
            return [(0.15, .30, .24, .24), (0.61, .30, .24, .24)]
        if count == 3:
            return [(0.15, .21, .24, .22), (0.61, .21, .24, .22), (0.38, .48, .24, .22)]
        return [(0.15, .19, .24, .22), (0.61, .19, .24, .22),
                (0.15, .48, .24, .22), (0.61, .48, .24, .22)]
    if layout == "staircase" and count <= 4:
        return [(0.10 + i * .20, .49 - i * .10, .18, .18) for i in range(count)]
    if layout in ("hero_illustration", "full_screen_diagram") and count <= 5:
        slots = [(0.35, .29, .30, .27)]
        satellites = [(0.08, .18, .18, .18), (0.74, .18, .18, .18),
                      (0.08, .51, .18, .18), (0.74, .51, .18, .18)]
        return slots + satellites[:count - 1]
    if layout == "summary_grid":
        if count == 1:
            return [(0.36, .31, .28, .25)]
        if count == 2:
            return [(0.14, .22, .22, .20), (0.64, .22, .22, .20)]
        if count == 3:
            return [(0.14, .18, .22, .20), (0.64, .18, .22, .20), (0.14, .48, .22, .20)]
        if count == 4:
            return [(0.14, .18, .22, .20), (0.64, .18, .22, .20),
                    (0.14, .48, .22, .20), (0.64, .48, .22, .20)]
        return grid(count)
    return grid(count)


def _draw_composition_panels(img: Image.Image, layout: str, accent: tuple[int, int, int]) -> None:
    """Render subtle layout-specific panels so schema layout choices visibly affect the composition."""
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    top, bottom = int(h * .155), int(h * .705)
    pale = (*tuple(lerp(c, 255, .94) for c in accent), 220)
    line = (*tuple(lerp(c, 255, .66) for c in accent), 210)

    def panel(box, tint=0):
        x1, y1, x2, y2 = box
        fill = pale if tint == 0 else (250, 252, 255, 230)
        d.rounded_rectangle((x1 + 2, y1 + 5, x2 + 2, y2 + 5), radius=max(16, w // 48), fill=(31, 41, 55, 12))
        d.rounded_rectangle(box, radius=max(16, w // 48), fill=fill, outline=line, width=max(1, w // 700))
        d.rounded_rectangle((x1 + int((x2-x1)*.08), y1 + 10, x1 + int((x2-x1)*.32), y1 + 15), radius=4, fill=(*accent, 145))

    if layout in ("two_column", "comparison_cards"):
        gap = int(w * .035)
        left, right = int(w * .085), int(w * .915)
        mid = w // 2
        panel((left, top, mid-gap, bottom), 0)
        panel((mid+gap, top, right, bottom), 1)
        if layout == "comparison_cards":
            d.line((mid, top + 20, mid, bottom - 20), fill=(*accent, 100), width=max(2, w//500))
    elif layout == "three_column":
        gap = int(w * .025)
        left, right = int(w * .07), int(w * .93)
        pw = int((right-left-2*gap)/3)
        for i in range(3):
            x1=left+i*(pw+gap)
            panel((x1, top+int(h*.025), x1+pw, bottom-int(h*.02)), i%2)
    elif layout == "summary_grid":
        gap_x, gap_y = int(w*.035), int(h*.025)
        left, right = int(w*.08), int(w*.92)
        mid = w//2
        mid_y = (top+bottom)//2
        panel((left, top, mid-gap_x//2, mid_y-gap_y//2), 0)
        panel((mid+gap_x//2, top, right, mid_y-gap_y//2), 1)
        panel((left, mid_y+gap_y//2, mid-gap_x//2, bottom), 1)
        panel((mid+gap_x//2, mid_y+gap_y//2, right, bottom), 0)
    elif layout == "timeline":
        yy = int(h*.43)
        d.line((int(w*.16), yy, int(w*.84), yy), fill=(*accent, 65), width=max(6,w//180))
        for x in (int(w*.20), int(w*.40), int(w*.60), int(w*.80)):
            r=max(8,w//55)
            d.ellipse((x-r, yy-r, x+r, yy+r), fill=(255,255,255,245), outline=(*accent,230), width=max(3,w//300))
    elif layout == "process_flow":
        yy=int(h*.43)
        for i,x in enumerate((.20,.50,.80)):
            xx=int(w*x); rw=int(w*.19); rh=int(h*.17)
            panel((xx-rw//2, yy-rh//2, xx+rw//2, yy+rh//2), i%2)
        for x in (.34,.66):
            xx=int(w*x)
            d.line((xx-int(w*.035),yy,xx+int(w*.035),yy),fill=(*accent,210),width=max(3,w//260))
            _draw_arrow_head(d,(xx+int(w*.035),yy),0,(*accent,220),max(8,w//55))
    elif layout == "staircase":
        x0,y0=int(w*.13),int(h*.64)
        for i in range(3):
            x=x0+i*int(w*.22); y=y0-i*int(h*.14)
            d.rounded_rectangle((x,y-int(h*.12),x+int(w*.24),y),radius=12,fill=(*tuple(lerp(c,255,.90) for c in accent),180),outline=(*accent,100),width=2)
    elif layout == "quiz_card":
        panel((int(w*.12),top+int(h*.04),int(w*.88),bottom-int(h*.04)),0)
    elif layout == "hero_illustration":
        d.ellipse((int(w*.23),int(h*.21),int(w*.77),int(h*.68)),fill=(*accent,10),outline=(*accent,40),width=max(2,w//450))
        d.ellipse((int(w*.31),int(h*.27),int(w*.69),int(h*.62)),outline=(*accent,35),width=max(2,w//600))
    elif layout == "full_screen_diagram":
        cx,cy=int(w*.5),int(h*.43)
        d.ellipse((cx-int(w*.16),cy-int(w*.16),cx+int(w*.16),cy+int(w*.16)),fill=(*accent,12),outline=(*accent,90),width=max(2,w//500))
        d.ellipse((cx-int(w*.31),cy-int(w*.31),cx+int(w*.31),cy+int(w*.31)),outline=(*accent,28),width=max(2,w//600))
    elif layout == "title_and_subtitle":
        panel((int(w*.11),top+int(h*.12),int(w*.89),bottom-int(h*.12)),0)
    # hero_illustration / diagram variants keep the board open; text and pictograms form the real content.
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"))


def draw_visual_fallback(img: Image.Image, visual: dict[str, Any], t: float, scene_start: float, layout: str = "hero_illustration") -> dict[str, tuple[int, int, int, int]]:
    """Draw semantic icon compositions with deterministic no-overlap slots and connectors behind tiles."""
    if not visual:
        return {}
    w, h = img.size
    bg = visual.get("background", {})
    accent = hex_rgb(bg.get("accent", "#7C3AED"), (124, 58, 237))
    stage_top, stage_bottom = int(h * .115), int(h * .735)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    pattern = bg.get("pattern", "soft_glow")
    if pattern in ("grid", "blueprint"):
        step = max(44, w // 16)
        for gx in range(0, w, step):
            d.line((gx, stage_top, gx, stage_bottom), fill=(90, 105, 130, 12), width=1)
        for gy in range(stage_top, stage_bottom, step):
            d.line((0, gy, w, gy), fill=(90, 105, 130, 12), width=1)
    elif pattern == "dots":
        step = max(36, w // 18)
        for gx in range(step // 2, w, step):
            for gy in range(stage_top + step // 2, stage_bottom, step):
                d.ellipse((gx - 1, gy - 1, gx + 1, gy + 1), fill=(113, 96, 170, 25))
    else:
        d.ellipse((int(w * .68), int(h * .12), int(w * 1.08), int(h * .43)), fill=(*accent, 13))
        d.ellipse((-int(w * .18), int(h * .49), int(w * .20), int(h * .78)), fill=(59, 130, 246, 10))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    board = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(board, "RGBA")
    bx1, by1, bx2, by2 = int(w * .045), int(h * .105), int(w * .955), int(h * .735)
    bd.rounded_rectangle((bx1 + 2, by1 + 9, bx2 + 2, by2 + 9), radius=max(22, w // 28), fill=(30, 41, 59, 20))
    bd.rounded_rectangle((bx1, by1, bx2, by2), radius=max(22, w // 28), fill=(255, 255, 255, 245), outline=(229, 233, 241, 255), width=max(1, w // 650))
    bd.rounded_rectangle((bx1 + int(w * .035), by1 + int(h * .018), bx1 + int(w * .15), by1 + int(h * .024)), radius=5, fill=(*accent, 210))
    img.paste(Image.alpha_composite(img.convert("RGBA"), board).convert("RGB"))
    _draw_composition_panels(img, layout, accent)

    objects = list(visual.get("objects", []))[:16]
    slots = _fallback_object_slots(len(objects), layout)
    occupied: list[tuple[int, int, int, int]] = []
    planned: list[tuple[dict[str, Any], tuple[int, int, int, int]]] = []
    gap = max(10, int(w * .018))

    # Retain AI coordinates if they are clear. Otherwise use deterministic grid slots.
    for index, original_obj in enumerate(objects):
        obj = dict(original_obj)
        preferred = dict(obj.get("position", {}))
        # Panel/card layouts use their matching reserved slots. Freeform hero/diagram
        # layouts may retain AI coordinates, provided they pass the same collision guard.
        freeform_layout = layout in ("hero_illustration", "full_screen_diagram", "custom")
        candidates = []
        if freeform_layout:
            candidates.append((float(preferred.get("x", slots[index][0])),
                               float(preferred.get("y", slots[index][1])),
                               min(.34, max(.12, float(preferred.get("width", slots[index][2])))),
                               min(.30, max(.12, float(preferred.get("height", slots[index][3]))))))
        candidates.extend(slots)
        chosen = None
        def normalized_object_rect(nx, ny, nw, nh):
            side = min(int(nw * w), int(nh * h))
            left = int(nx * w) + (int(nw * w) - side) // 2
            top = int(ny * h) + (int(nh * h) - side) // 2
            return (left, top, left + side, top + side)
        for nx, ny, nw, nh in candidates:
            nx = max(.055, min(.945 - nw, nx))
            ny = max(.125, min(.72 - nh, ny))
            rect = normalized_object_rect(nx, ny, nw, nh)
            if any(_rects_overlap(rect, other, gap) for other in occupied):
                continue
            # Do not let a preferred large object occupy the reserved slot of a later object.
            blocks_future_slot = False
            for fx, fy, fw, fh in slots[index + 1:]:
                future_rect = normalized_object_rect(fx, fy, fw, fh)
                if _rects_overlap(rect, future_rect, gap):
                    blocks_future_slot = True
                    break
            if not blocks_future_slot:
                chosen = (nx, ny, nw, nh, rect)
                break
        if chosen is None:
            # Last-resort: search every fixed slot for an actually free cell; never knowingly stack objects.
            for nx, ny, nw, nh in slots:
                rect = normalized_object_rect(nx, ny, nw, nh)
                if not any(_rects_overlap(rect, other, gap) for other in occupied):
                    chosen = (nx, ny, nw, nh, rect)
                    break
        if chosen is None:
            # With a valid schema the 16-cell maximum always fits; this branch is defensive.
            nx, ny, nw, nh = slots[-1]
            rect = normalized_object_rect(nx, ny, nw, nh)
            chosen = (nx, ny, nw, nh, rect)
        nx, ny, nw, nh, rect = chosen
        obj["position"] = {"x": nx, "y": ny, "width": nw, "height": nh}
        occupied.append(rect)
        planned.append((obj, rect))

    object_rects: dict[str, tuple[int, int, int, int]] = {}
    icon_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for obj, _ in planned:
        oid = str(obj.get("object_id", ""))
        actual = draw_3d_object(icon_layer, obj, t, scene_start)
        object_rects[oid] = actual

    # Draw connectors behind icons and stop at object edges so they do not cross the pictograms.
    connector_draw = ImageDraw.Draw(img, "RGBA")
    for connector in visual.get("connectors", []):
        a = object_rects.get(connector.get("from_object"))
        b = object_rects.get(connector.get("to_object"))
        if not a or not b:
            continue
        ac = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
        bc = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        dx, dy = bc[0] - ac[0], bc[1] - ac[1]
        length = math.hypot(dx, dy)
        if length < 2:
            continue
        ux, uy = dx / length, dy / length
        def edge_point(rect, cx, cy, ux, uy):
            half_w = max(1, (rect[2] - rect[0]) / 2 - 3)
            half_h = max(1, (rect[3] - rect[1]) / 2 - 3)
            scale_x = half_w / abs(ux) if abs(ux) > 1e-6 else float("inf")
            scale_y = half_h / abs(uy) if abs(uy) > 1e-6 else float("inf")
            scale = min(scale_x, scale_y)
            return (int(cx + ux * scale), int(cy + uy * scale))
        p1 = edge_point(a, *ac, ux, uy)
        p2 = edge_point(b, *bc, -ux, -uy)
        # Skip a connector if it would pass through a third object.
        path_box = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
        third_hit = any(_rects_overlap(path_box, r, 0) for oid, r in object_rects.items()
                        if oid not in (connector.get("from_object"), connector.get("to_object")))
        if third_hit:
            continue
        color = (*hex_rgb(connector.get("color", "#94A3B8")), 215)
        width = max(2, w // 420)
        connector_draw.line((p1, p2), fill=(*color[:3], 55), width=width + 5)
        connector_draw.line((p1, p2), fill=color, width=width)
        line_pad = max(8, w // 110)
        object_rects[f"__connector_path_{len(object_rects)}"] = (
            min(p1[0], p2[0]) - line_pad, min(p1[1], p2[1]) - line_pad,
            max(p1[0], p2[0]) + line_pad, max(p1[1], p2[1]) + line_pad)
        if connector.get("style", "arrow") in ("arrow", "curved_arrow"):
            angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            _draw_arrow_head(connector_draw, p2, angle, color, max(8, w // 58))
        label = connector.get("label")
        if label and length > w * .22:
            mx, my = (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2
            font = get_font(str(label), max(12, int(w * .017)), True)
            bb = connector_draw.textbbox((0, 0), str(label), font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            label_rect = (mx - tw // 2 - 7, my - th // 2 - 5, mx + tw // 2 + 7, my + th // 2 + 5)
            if not any(_rects_overlap(label_rect, r, 4) for r in object_rects.values()):
                connector_draw.rounded_rectangle(label_rect, radius=8, fill=(255, 255, 255, 245), outline=(225, 231, 240, 255), width=1)
                connector_draw.text((mx - tw // 2, my - th // 2), str(label), font=font, fill=(55, 65, 81, 255))
                object_rects[f"__connector_label_{len(object_rects)}"] = label_rect

    img.paste(Image.alpha_composite(img.convert("RGBA"), icon_layer).convert("RGB"))
    return object_rects


def render_scene_frame(scene: dict, project: dict, timings: dict, seg_map: dict, asset_paths: dict[str,str],
                       asset_images: dict[str, Image.Image], asset_video_caps: dict[str, Any],
                       fit_cache: dict[tuple[str, int, int], Image.Image],
                       t: float, size: tuple[int,int], scene_time: RuntimeTiming) -> Image.Image:
    w,h=size
    fallback=scene.get("visual_fallback",{})
    visual_bg=fallback.get("background",{})
    palette=project.get("visual_style",{}).get("palette",["#7C3AED","#0EA5A4","#3B82F6"])
    accent=hex_rgb(visual_bg.get("accent",palette[0] if palette else "#7C3AED"),(124,58,237))

    # Modern light editorial canvas; use a scanline gradient to keep rendering efficient.
    img=draw_gradient(size,(250,251,255),t)
    # Soft accent atmosphere in opposite corners.
    deco=Image.new("RGBA",size,(0,0,0,0)); dd=ImageDraw.Draw(deco,"RGBA")
    dd.ellipse((int(w*.69),int(h*.02),int(w*1.12),int(h*.33)),fill=(*accent,15))
    dd.ellipse((-int(w*.16),int(h*.48),int(w*.23),int(h*.80)),fill=(59,130,246,10))
    img.paste(Image.alpha_composite(img.convert("RGBA"),deco).convert("RGB"))
    object_rects=draw_visual_fallback(img,fallback,t,scene_time.start,scene.get("layout", "hero_illustration"))

    # Optional external media is framed like an editorial media card, while the JSON 2.5D icon scene remains underneath.
    for el in scene.get("elements",[]):
        if el.get("kind") not in ("image","video"):
            continue
        anch=element_timing(el,timings,seg_map,scene_time)
        anim=el.get("animation",{})
        appear=max(scene_time.start,anch.start)
        if t<appear: continue
        aid=el.get("asset_id"); apath=asset_paths.get(aid or "")
        if not apath or not Path(apath).exists(): continue
        ap=Path(apath); pos=el.get("position",{})
        x,y=int(pos.get("x",.1)*w),int(pos.get("y",.15)*h)
        ew,eh=int(pos.get("width",.8)*w),int(pos.get("height",.5)*h)
        x=max(int(w*.055),min(int(w*.945)-ew,x)); y=max(int(h*.12),min(int(h*.735)-eh,y))
        ew=max(1,min(int(w*.89),ew)); eh=max(1,min(int(h*.615),eh))
        # Media must not cover an object/connector or another media tile. Reposition if possible, otherwise skip.
        media_rect = (x, y, x+ew, y+eh)
        media_candidates = [(x, y)]
        for dy in (-.10, .10, -.18, .18, -.26, .26):
            media_candidates.append((x, y + int(dy*h)))
        media_candidates.extend((int(w*fx), int(h*fy)) for fx, fy in ((.06,.13),(.48,.13),(.06,.45),(.48,.45)))
        placed_media = False
        for mx, my in media_candidates:
            mx=max(int(w*.055),min(int(w*.945)-ew,mx))
            my=max(int(h*.12),min(int(h*.735)-eh,my))
            candidate=(mx,my,mx+ew,my+eh)
            if not any(_rects_overlap(candidate, rr, max(8,int(h*.008))) for rr in object_rects.values()):
                x,y=mx,my; media_rect=candidate; placed_media=True; break
        if not placed_media:
            continue
        try:
            if ap.suffix.lower() in VIDEO_EXTS and str(ap) in asset_video_caps:
                media=read_video_asset_frame(asset_video_caps[str(ap)],max(0.0,t-appear),(ew,eh))
                if media is None: continue
            else:
                key=(str(ap),ew,eh)
                if key not in fit_cache:
                    source_img=asset_images.get(str(ap))
                    if source_img is None: source_img=Image.open(ap).convert("RGB")
                    fit_cache[key]=ImageOps.fit(source_img,(ew,eh),method=Image.Resampling.LANCZOS)
                media=fit_cache[key]
            alpha=1.0; dur=max(.05,float(anim.get("duration_s",.3)))
            if anim.get("in") not in (None,"none"):
                alpha=min(1.0,max(0.0,(t-appear)/dur))
            media_rgba=media.convert("RGBA")
            if alpha<1: media_rgba.putalpha(int(alpha*255))
            mask=Image.new("L",(ew,eh),0); md=ImageDraw.Draw(mask)
            md.rounded_rectangle((0,0,ew,eh),radius=max(12,w//42),fill=255)
            img.paste(media_rgba.convert("RGB"),(x,y),mask)
            ImageDraw.Draw(img,"RGBA").rounded_rectangle((x,y,x+ew,y+eh),radius=max(12,w//42),outline=(255,255,255,230),width=max(2,w//300))
            object_rects[f"__media_{aid or len(object_rects)}"] = media_rect
        except Exception:
            continue

    # Section title as a quiet editorial label, not a large hard-shadow heading.
    title_text=scene.get("learning_goal","")
    d=ImageDraw.Draw(img,"RGBA")
    if title_text:
        title_font=get_font(title_text,max(18,int(w*.026)),True)
        label=str(title_text)
        label_lines=wrap_text(d,label,title_font,int(w*.86))[:2]
        ty=int(h*.045)
        for line in label_lines:
            bb=d.textbbox((0,0),line,font=title_font); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
            d.rounded_rectangle((int(w*.065)-10,ty-5,int(w*.065)+tw+14,ty+th+7),radius=12,fill=(255,255,255,225),outline=(228,232,241,255),width=1)
            d.text((int(w*.065),ty),line,font=title_font,fill=(55,65,81,255))
            ty+=title_font.size+7

    text_elements=[el for el in scene.get("elements",[]) if el.get("kind") not in ("image","video") and el.get("content")]
    element_windows={}
    # Repeated items with the same semantic role and overlapping positions are treated as sequential cards.
    # Example sentences replace one another; quiz options with different roles stay visible together.
    for idx, el in enumerate(text_elements):
        current=element_timing(el,timings,seg_map,scene_time)
        appear=max(scene_time.start,current.start)
        visible_until=scene_time.end
        role=el.get("role")
        pos=el.get("position",{})
        ex1,ey1=float(pos.get("x",0)),float(pos.get("y",0))
        ex2,ey2=ex1+float(pos.get("width",1)),ey1+float(pos.get("height",1))
        for later in text_elements[idx+1:]:
            if not role or later.get("role")!=role:
                continue
            lp=later.get("position",{})
            lx1,ly1=float(lp.get("x",0)),float(lp.get("y",0))
            lx2,ly2=lx1+float(lp.get("width",1)),ly1+float(lp.get("height",1))
            overlap_w=max(0.0,min(ex2,lx2)-max(ex1,lx1))
            overlap_h=max(0.0,min(ey2,ly2)-max(ey1,ly1))
            if overlap_w*overlap_h <= 0:
                continue
            later_time=element_timing(later,timings,seg_map,scene_time)
            if later_time.start>appear+0.03:
                visible_until=min(visible_until,later_time.start)
                break
        element_windows[el.get("element_id")]=(appear,visible_until)

    reserved_text_rects: list[tuple[int, int, int, int]] = []
    text_drawn = 0
    for el in text_elements:
        content = el.get("content")
        appear, visible_until = element_windows.get(el.get("element_id"), (scene_time.start, scene_time.end))
        if t < appear or t >= visible_until:
            continue
        anim = el.get("animation", {})
        anim_dur = max(.05, float(anim.get("duration_s", .35)))
        alpha = 1.0
        mode = anim.get("in", "none")
        if mode != "none":
            alpha = min(1.0, max(0.0, (t - appear) / anim_dur))
        if visible_until < scene_time.end and t > visible_until - .22:
            alpha = min(alpha, max(0.0, (visible_until - t) / .22))
        elif anim.get("out", "none") != "none" and t > scene_time.end - anim_dur:
            alpha = min(alpha, max(0.0, (scene_time.end - t) / anim_dur))
        if alpha <= 0:
            continue

        pos = dict(el.get("position", {}))
        role_name = el.get("role") or ""
        if role_name == "option_a":
            pos.update({"x": .09, "y": .535, "width": .82, "height": .075})
        elif role_name == "option_b":
            pos.update({"x": .09, "y": .625, "width": .82, "height": .075})
        x = int(float(pos.get("x", .1)) * w)
        y = int(float(pos.get("y", .2)) * h)
        ew = max(70, int(float(pos.get("width", .8)) * w))
        eh = max(45, int(float(pos.get("height", .12)) * h))
        x = max(int(w * .055), min(int(w * .945) - ew, x))
        y = max(int(h * .12), min(int(h * .72), y))
        if mode == "fade_up":
            y += int((1 - alpha) * min(26, h * .022))
        elif mode == "slide_left":
            x += int((1 - alpha) * min(40, w * .04))
        elif mode == "slide_right":
            x -= int((1 - alpha) * min(40, w * .04))

        text = str(content)
        if mode == "reveal" and alpha < 1:
            text = text[:max(1, int(len(text) * alpha))]
        style = el.get("style", {})
        size_role = style.get("size_role", "body")
        scale = float(style.get("font_scale", 1.0) or 1.0)
        size_px = int(min(w, h) * {"display": .080, "headline": .054, "body": .036, "caption": .029, "label": .026}.get(size_role, .040) * scale)
        size_px = max(15, min(int(h * .105), size_px))
        if mode == "scale_in":
            size_px = max(12, int(size_px * (.86 + .14 * alpha)))
        d = ImageDraw.Draw(img, "RGBA")
        align = style.get("alignment", "center")
        effect = style.get("text_effect", "card")
        is_card = effect in ("pill", "card") or bool(style.get("background_color"))
        pad = max(9, int(size_px * .26))
        font = get_font(text, size_px, style.get("weight") in ("bold", "black"))
        max_text_width = max(48, ew - 2 * pad - 12)
        lines = wrap_text(d, text, font, max_text_width)
        # Keep English phrases legible. Shrink progressively before using a third line.
        while (len(lines) > 2 or max((d.textbbox((0, 0), ln, font=font)[2] for ln in lines), default=0) > max_text_width) and size_px > 15:
            size_px = max(15, int(size_px * .92))
            font = get_font(text, size_px, style.get("weight") in ("bold", "black"))
            max_text_width = max(48, ew - 2 * pad - 12)
            lines = wrap_text(d, text, font, max_text_width)
        line_h = int(size_px * 1.25)
        text_h = max(line_h, len(lines) * line_h)
        card_h = text_h + 2 * pad
        card_w = ew if is_card else min(ew, max((d.textbbox((0, 0), ln, font=font)[2] for ln in lines), default=ew) + 2 * pad)
        # Generate close-to-requested locations, followed by a fine grid scan. The stage ends at y=.735.
        x_candidates = [x, int(w * .07), int(w * .12), int(w * .20), int(w * .28), int(w * .36)]
        y_candidates = [y]
        for dy in (-.08, .08, -.16, .16, -.24, .24, -.32, .32):
            y_candidates.append(y + int(dy * h))
        step_y = max(22, int(h * .025))
        grid_ys = list(range(int(h * .125), max(int(h * .125) + 1, int(h * .735) - card_h), step_y))
        y_candidates.extend(sorted(grid_ys, key=lambda cy: abs(cy - y)))
        candidates = []
        seen = set()
        for cy in y_candidates:
            for cx in x_candidates:
                cx = max(int(w * .055), min(int(w * .945) - card_w, cx))
                cy = max(int(h * .12), min(int(h * .735) - card_h, cy))
                key = (cx, cy)
                if key not in seen:
                    seen.add(key)
                    candidates.append(key)
        best_xy = None
        best_score = None
        gap = max(8, int(h * .008))
        for cx, cy in candidates:
            rect = (cx, cy, cx + card_w, cy + card_h)
            if any(_rects_overlap(rect, rr, gap) for rr in object_rects.values()):
                continue
            if any(_rects_overlap(rect, rr, gap) for rr in reserved_text_rects):
                continue
            score = abs(cx - x) + abs(cy - y) * 1.15
            if best_score is None or score < best_score:
                best_score, best_xy = score, (cx, cy)
                break  # candidate order is already near-to-far
        if best_xy is None:
            # Compact width/height fallback. It is preferable to omit an overcrowded overlay to drawing it on top of another element.
            compact_w = int(w * .70)
            compact_x = int((w - compact_w) / 2)
            for cy in sorted(grid_ys, key=lambda cy: abs(cy - y)):
                cy = max(int(h * .12), min(int(h * .735) - card_h, cy))
                rect = (compact_x, cy, compact_x + compact_w, cy + card_h)
                if not any(_rects_overlap(rect, rr, gap) for rr in list(object_rects.values()) + reserved_text_rects):
                    best_xy = (compact_x, cy)
                    card_w = compact_w
                    max_text_width = compact_w - 2 * pad - 12
                    lines = wrap_text(d, text, font, max_text_width)
                    text_h = max(line_h, len(lines) * line_h)
                    card_h = text_h + 2 * pad
                    break
        if best_xy is None:
            # Hard guard: do not allow an overlapping text block into the final render.
            continue

        x, y = best_xy
        top = y + max(0, (card_h - text_h) // 2)
        raw_color = hex_rgb(style.get("color", "#263246"), (38, 50, 70))
        luminance = (.2126 * raw_color[0] + .7152 * raw_color[1] + .0722 * raw_color[2]) / 255
        if luminance > .82:
            color = (36, 47, 66)
        elif raw_color[0] > 200 and raw_color[1] > 140 and raw_color[2] < 130:
            color = (145, 91, 13)
        else:
            color = raw_color
        bg_value = style.get("background_color")
        if is_card:
            if bg_value:
                fill_rgb = hex_rgb(bg_value, (255, 255, 255))
                if sum(fill_rgb) / 3 < 120:
                    fill_rgb = (255, 255, 255)
            elif effect == "pill":
                fill_rgb = tuple(lerp(c, 255, .88) for c in accent)
            else:
                fill_rgb = (255, 255, 255)
            d.rounded_rectangle((x + 2, top - pad + 5, x + card_w + 2, top + text_h + pad + 5),
                                radius=max(12, size_px // 4), fill=(30, 41, 59, int(22 * alpha)))
            border_color = tuple(lerp(c, 255, .68) for c in color)
            d.rounded_rectangle((x, top - pad, x + card_w, top + text_h + pad),
                                radius=max(12, size_px // 4), fill=(*fill_rgb, int(246 * alpha)),
                                outline=(*border_color, int(170 * alpha)), width=max(1, w // 500))
            if effect == "card":
                d.rounded_rectangle((x + int(card_w * .025), top - pad + int(pad * .55),
                                     x + int(card_w * .025) + max(4, w // 220), top + text_h + pad - int(pad * .55)),
                                    radius=4, fill=(*accent, int(220 * alpha)))

        actual_widths = []
        for line in lines:
            bb = d.textbbox((0, 0), line, font=font)
            tw = bb[2] - bb[0]
            if align == "left":
                tx = x + pad + (int(card_w * .025) if effect == "card" else 0)
            elif align == "right":
                tx = x + card_w - pad - tw
            else:
                tx = x + (card_w - tw) // 2
            d.text((tx, top), line, font=font, fill=(*color, int(255 * alpha)))
            actual_widths.append((tx, tx + tw))
            top += line_h
        # Reserve the visual footprint, not merely the original JSON rectangle.
        text_rect = (min((a for a, _ in actual_widths), default=x) - (pad if is_card else 3),
                     y, max((b for _, b in actual_widths), default=x + card_w) + (pad if is_card else 3),
                     y + card_h)
        reserved_text_rects.append(text_rect)
        text_drawn += 1

    # Progress track above the caption zone, aligned to the light visual system.
    d=ImageDraw.Draw(img,"RGBA")
    d.rounded_rectangle((int(w*.08),int(h*.955),int(w*.92),int(h*.961)),radius=6,fill=(148,163,184,70))
    scene_fraction=(t-scene_time.start)/max(.01,scene_time.end-scene_time.start)
    d.rounded_rectangle((int(w*.08),int(h*.955),int(w*(.08+.84*max(0,min(1,scene_fraction)))),int(h*.961)),radius=6,fill=(*accent,225))
    return img.convert("RGB")


def render_storyboard_video(audio_path: Path, output: Path, storyboard: dict, timings: dict, asset_paths: dict,
                            size: tuple[int,int], fps: int, duration: float, progress, log, cancel: threading.Event,
                            caption_words: Optional[list[dict[str, Any]]] = None, show_subtitles: bool = True,
                            detected_language: str = "auto"):
    w,h=size
    fps=max(15,min(30,int(fps)))
    total=max(1,math.ceil(duration*fps))
    temp=output.with_name(output.stem+"_silent.mp4")
    ff=[ffmpeg_path(),"-y","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{w}x{h}","-r",str(fps),"-i","pipe:0","-an","-c:v","libx264","-preset","ultrafast","-crf","22","-pix_fmt","yuv420p",str(temp)]
    log("Rendering scene-based visual timeline...")
    proc=subprocess.Popen(ff,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    seg_map={s["segment_id"]:s for s in storyboard["source_segments"]}
    scenes=storyboard["scenes"]
    captions = build_caption_lines(caption_words or [], storyboard.get("source_segments", []),
                                   timings["segments"], detected_language, duration) if show_subtitles else []
    if show_subtitles:
        mode = "word-level purple karaoke" if caption_words else "segment-level fallback (chưa ALIGN AUDIO)"
        log(f"Phụ đề dưới màn hình: {mode}; {len(captions)} caption lines.")
    active_index=0
    asset_images: dict[str, Image.Image] = {}
    asset_video_caps: dict[str, Any] = {}
    fit_cache: dict[tuple[str, int, int], Image.Image] = {}
    used_paths = {str(Path(p)) for p in asset_paths.values() if p and Path(p).exists()}
    for scene in scenes:
        for el in scene.get("elements", []):
            aid = el.get("asset_id")
            if aid and asset_paths.get(aid) and Path(asset_paths[aid]).exists():
                used_paths.add(str(Path(asset_paths[aid])))
    for raw_path in used_paths:
        pp = Path(raw_path)
        try:
            if pp.suffix.lower() in VIDEO_EXTS:
                try:
                    import cv2
                except Exception as exc:
                    raise RuntimeError("Để phát video asset theo timeline, hãy cài opencv-python-headless từ requirements.txt.") from exc
                cap = cv2.VideoCapture(str(pp))
                if not cap.isOpened():
                    raise RuntimeError(f"OpenCV không mở được video asset {pp.name}.")
                ok, first_frame = cap.read()
                if not ok or first_frame is None:
                    cap.release()
                    raise RuntimeError(f"Video asset {pp.name} không giải mã được frame đầu.")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                asset_video_caps[raw_path] = cap
            else:
                with Image.open(pp) as im:
                    im.verify()
                asset_images[raw_path] = Image.open(pp).convert("RGB").copy()
            log(f"Đã nạp và kiểm tra media: {pp.name}")
        except Exception as exc:
            # External media is optional in v1.3. Keep rendering with each scene's JSON-defined visual_fallback.
            log(f"Media {pp.name} không dùng được ({exc}); sẽ thay bằng collision-aware vector visual_fallback của cảnh.")
    try:
        for frame in range(total):
            if cancel.is_set(): raise InterruptedError("Đã hủy render.")
            t=frame/fps
            while active_index < len(scenes)-1 and t >= timings["scenes"][scenes[active_index]["scene_id"]].end:
                active_index += 1
            scene=scenes[active_index]
            st=timings["scenes"][scene["scene_id"]]
            # If there are gaps between scenes, show current scene until next starts.
            if t < st.start and active_index > 0:
                scene=scenes[active_index-1]; st=timings["scenes"][scene["scene_id"]]
            img=render_scene_frame(scene,storyboard["project"],timings,seg_map,asset_paths,asset_images,asset_video_caps,fit_cache,t,size,st)
            if show_subtitles:
                draw_bottom_karaoke_caption(img, current_caption(captions, t), t, detected_language)
            # Short fade-in on scene transition.
            if t-st.start < .28 and scene.get("transition_in") in ("fade","dissolve"):
                alpha=max(0,min(1,(t-st.start)/.28))
                img=Image.blend(Image.new("RGB",size,(0,0,0)),img,alpha)
            proc.stdin.write(img.tobytes())
            if frame % fps == 0 or frame == total-1:
                progress(5+int(84*(frame+1)/total),f"Render frame {frame+1}/{total}")
        proc.stdin.close()
        err=proc.stderr.read().decode("utf-8","ignore") if proc.stderr else ""
        code=proc.wait()
        if code != 0 or not temp.exists(): raise RuntimeError("FFmpeg render lỗi: "+err[-1800:])
    finally:
        if proc.poll() is None: proc.kill()
        if cancel.is_set(): temp.unlink(missing_ok=True)
    log("Ghép audio gốc vào video...")
    mux=run_ffmpeg(["-y","-i",str(temp),"-i",str(audio_path),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(output)],timeout=1800)
    temp.unlink(missing_ok=True)
    if mux.returncode != 0 or not output.exists():
        output.unlink(missing_ok=True)
        raise RuntimeError("Không ghép được audio: "+mux.stderr.decode("utf-8","ignore")[-1600:])
    for cap in asset_video_caps.values():
        try: cap.release()
        except Exception: pass
    for cached in asset_images.values():
        try: cached.close()
        except Exception: pass
    for cached in fit_cache.values():
        try: cached.close()
        except Exception: pass
    progress(100,"Hoàn tất")


def main():
    if not SCHEMA_PATH.exists():
        messagebox.showerror("Thiếu schema", f"Không tìm thấy {SCHEMA_PATH}")
        return
    root=tk.Tk()
    EducationalVideoStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
