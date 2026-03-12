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
    director = data.get("director", "未知导演")
    movie = data.get("movie", "未知电影")
    original_title = data.get("original_title", "")
    year = data.get("year", "")
    country = data.get("country", "")
    synopsis = data.get("synopsis", "")
    visual_style = data.get("visual_style", "")
    narrative = data.get("narrative", "")
    why_watch = data.get("why_watch", "")

    title_line = f"{movie}"
    if original_title and original_title != movie:
        title_line += f"  /  {original_title}"

    meta_parts = [str(year) if year else "", country]
    meta = "  ·  ".join(p for p in meta_parts if p)

    sections = []

    if synopsis:
        sections.append(f"**故事**\n\n{synopsis}")

    if visual_style:
        sections.append(f"**影像**\n\n{visual_style}")

    if narrative:
        sections.append(f"**叙事**\n\n{narrative}")

    if why_watch:
        sections.append(f"**为何值得一看**\n\n{why_watch}")

    body = "\n\n---\n\n".join(sections)

    return f"""# {title_line}

导演 {director}　{meta}

---

{body}

---

*{datetime.now().strftime("%Y.%m.%d")}　manus-cine*
"""


def save_trailer(data: dict) -> Path:
    TRAILERS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    d = _slug(data.get("director", ""))
    m = _slug(data.get("movie", ""))
    name = f"{date}_{d}_{m}.md"
    path = TRAILERS_DIR / name
    path.write_text(generate_trailer(data), encoding="utf-8")
    return path
