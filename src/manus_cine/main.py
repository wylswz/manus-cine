"""manus-cine main entry: recommend movie, generate trailer, send to Feishu."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .feishu import send_trailer_to_feishu
from .manus import recommend_movie
from .storage import get_recommended_movies, save_recommendation
from .trailer import generate_trailer, save_trailer

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise SystemExit(f"Missing required env: {name}")
    return val


MOCK_RECOMMENDATION: dict = {
    "director": "斯坦利·库布里克",
    "movie": "2001太空漫游",
    "year": 1968,
    "reason": "影史经典，探讨人类进化与技术的哲学命题。",
    "brief": "人类从猿到太空的进化史诗，AI HAL 9000 的叛变成为科幻经典。",
}


def main() -> None:
    """Run the full pipeline."""
    root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local")

    mock_mode = os.environ.get("MOCK_MODE", "").lower() in ("1", "true", "yes")
    if mock_mode:
        logger.info("MOCK_MODE enabled: skipping Manus API call")

    app_id = _env("FEISHU_APP_ID")
    app_secret = _env("FEISHU_APP_SECRET")
    chat_id = _env("FEISHU_CHAT_ID")
    receive_id_type = os.environ.get("FEISHU_RECEIVE_ID_TYPE", "chat_id")

    excluded_movies = get_recommended_movies()
    logger.info("Excluding %d already recommended movies", len(excluded_movies))

    if mock_mode:
        data = MOCK_RECOMMENDATION.copy()
    else:
        api_key = _env("MANUS_API_KEY")
        try:
            data = recommend_movie(api_key, excluded_movies)
        except Exception as e:
            logger.exception("Manus API failed: %s", e)
            sys.exit(2)

    director = data.get("director", "?")
    movie = data.get("movie", "?")
    logger.info("Recommended: %s - %s", director, movie)

    if not mock_mode:
        save_recommendation(data)
    trailer_path = save_trailer(data)
    content = generate_trailer(data)

    try:
        send_trailer_to_feishu(app_id, app_secret, chat_id, content, receive_id_type)
    except Exception as e:
        logger.exception("Feishu send failed: %s", e)
        sys.exit(2)

    logger.info("Trailer saved to %s", trailer_path)


if __name__ == "__main__":
    main()
