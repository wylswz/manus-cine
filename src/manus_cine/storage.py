"""Persist and query recommended movies to avoid duplicates."""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

RECOMMENDED_DIR = Path(__file__).resolve().parent.parent.parent / "recommended"


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text)
    s = re.sub(r"[-\s]+", "_", s).strip().lower()
    return s[:64] if s else "unknown"


def get_recommended_ids() -> set[str]:
    ids: set[str] = set()
    if not RECOMMENDED_DIR.exists():
        return ids
    for f in RECOMMENDED_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            d = _slug(data.get("director", ""))
            m = _slug(data.get("movie", ""))
            if d and m:
                ids.add(f"{d}_{m}")
        except Exception as e:
            logger.warning("Skip %s: %s", f, e)
    return ids


def get_recommended_movies() -> list[str]:
    """Return 'Director - Movie' list to pass to Manus."""
    movies: list[str] = []
    if not RECOMMENDED_DIR.exists():
        return movies
    for f in RECOMMENDED_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            d = data.get("director", "")
            m = data.get("movie", "")
            if d and m:
                movies.append(f"{d} - {m}")
        except Exception as e:
            logger.warning("Skip %s: %s", f, e)
    return sorted(movies)


def save_recommendation(director: str, movie: str) -> Path:
    RECOMMENDED_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{_slug(director)}_{_slug(movie)}.json"
    path = RECOMMENDED_DIR / name
    path.write_text(
        json.dumps({"director": director, "movie": movie}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved recommendation: %s", path)
    return path
