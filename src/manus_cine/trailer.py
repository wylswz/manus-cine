"""Generate trailer-style Markdown from movie recommendation."""

from datetime import datetime
from pathlib import Path
import re

TRAILERS_DIR = Path(__file__).resolve().parent.parent.parent / "trailers"


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text)
    s = re.sub(r"[-\s]+", "_", s).strip().lower()
    return s[:32] if s else "unknown"


def generate_trailer(data: dict) -> str:
    """Generate Markdown trailer content from recommendation data."""
    director = data.get("director", "未知导演")
    movie = data.get("movie", "未知电影")
    year = data.get("year", "")
    reason = data.get("reason", "")
    brief = data.get("brief", "")

    return f"""# 🎬 {movie}

**导演**：{director}  
**年份**：{year}

---

## 推荐理由

{reason}

---

## 剧情简介

{brief}

---

*由 manus-cine 推荐 · {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""


def save_trailer(data: dict) -> Path:
    """Save trailer Markdown to trailers/ and return path."""
    TRAILERS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    d = _slug(data.get("director", ""))
    m = _slug(data.get("movie", ""))
    name = f"{date}_{d}_{m}.md"
    path = TRAILERS_DIR / name
    content = generate_trailer(data)
    path.write_text(content, encoding="utf-8")
    return path
