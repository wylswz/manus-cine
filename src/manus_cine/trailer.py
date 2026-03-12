"""Save trailer Markdown files."""

import re
from datetime import datetime
from pathlib import Path

TRAILERS_DIR = Path(__file__).resolve().parent.parent.parent / "trailers"


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text)
    s = re.sub(r"[-\s]+", "_", s).strip().lower()
    return s[:32] if s else "unknown"


def save_trailer(markdown: str, director: str, movie: str) -> Path:
    TRAILERS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    name = f"{date}_{_slug(director)}_{_slug(movie)}.md"
    path = TRAILERS_DIR / name
    path.write_text(markdown, encoding="utf-8")
    return path
