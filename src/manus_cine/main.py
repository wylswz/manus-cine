"""manus-cine main entry: recommend movie, generate trailer, send to Feishu."""

import logging
import os
import sys

from .feishu import send_trailer_to_feishu
from .manus import recommend_movie
from .storage import get_recommended_ids, save_recommendation
from .trailer import generate_trailer, save_trailer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise SystemExit(f"Missing required env: {name}")
    return val


def main() -> None:
    """Run the full pipeline."""
    api_key = _env("MANUS_API_KEY")
    app_id = _env("FEISHU_APP_ID")
    app_secret = _env("FEISHU_APP_SECRET")
    chat_id = _env("FEISHU_CHAT_ID")

    excluded = get_recommended_ids()
    logger.info("Excluding %d already recommended movies", len(excluded))

    try:
        data = recommend_movie(api_key, excluded)
    except Exception as e:
        logger.exception("Manus API failed: %s", e)
        sys.exit(2)

    director = data.get("director", "?")
    movie = data.get("movie", "?")
    logger.info("Recommended: %s - %s", director, movie)

    # Persist
    save_recommendation(data)
    trailer_path = save_trailer(data)
    content = generate_trailer(data)

    # Send to Feishu
    try:
        send_trailer_to_feishu(app_id, app_secret, chat_id, content)
    except Exception as e:
        logger.exception("Feishu send failed: %s", e)
        sys.exit(2)

    logger.info("Trailer saved to %s", trailer_path)


if __name__ == "__main__":
    main()
