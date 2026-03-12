"""manus-cine main entry: recommend movie, generate trailer, send to Feishu."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .feishu import send_trailer_to_feishu
from .manus import recommend_movie
from .storage import get_recommended_movies, save_recommendation
from .trailer import save_trailer

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


MOCK_MARKDOWN = """\
# 潜行者 / Stalker
导演：安德烈·塔可夫斯基　年份：1979　国家：苏联

## 故事

三个男人穿越名为「禁区」的神秘地带，前往据说能实现内心最深处愿望的「房间」。旅途漫长而沉默，他们带着各自的疑惑，在荒草与积水之间一步步走向某种无法命名的边界。

## 影像

全片几乎使用手持长镜头，镜头贴近地面游移，锈迹、积水、枯草构成腐败的诗意。色彩在黑白与土黄之间切换，禁区内部微微泛绿，仿佛一切处于缓慢的生长与消解之中。

## 叙事

叙事拒绝戏剧性，以沉默和等待代替事件。三个人物代表三种对意义的渴求，却在抵达终点时陷入彼此不同的虚无。时间在片中被拉伸，成为一种物质。

## 为何值得一看

一部关于信仰本身的电影——不是信仰什么，而是信仰这件事还能否成立。它让你在结束后很久仍然坐着。
"""


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local")

    mock_mode = os.environ.get("MOCK_MODE", "").lower() in ("1", "true", "yes")
    if mock_mode:
        logger.info("MOCK_MODE: skipping Manus API call")

    app_id = _env("FEISHU_APP_ID")
    app_secret = _env("FEISHU_APP_SECRET")
    chat_id = _env("FEISHU_CHAT_ID")
    receive_id_type = os.environ.get("FEISHU_RECEIVE_ID_TYPE", "chat_id")

    excluded_movies = get_recommended_movies()
    logger.info("Excluding %d already recommended movies", len(excluded_movies))

    if mock_mode:
        result = {"markdown": MOCK_MARKDOWN, "director": "安德烈·塔可夫斯基", "movie": "潜行者"}
    else:
        api_key = _env("MANUS_API_KEY")
        try:
            result = recommend_movie(api_key, excluded_movies)
        except Exception as e:
            logger.exception("Manus API failed: %s", e)
            sys.exit(2)

    director = result["director"]
    movie = result["movie"]
    markdown = result["markdown"]
    logger.info("Recommended: %s - %s", director, movie)

    if not mock_mode:
        save_recommendation(director, movie)
    trailer_path = save_trailer(markdown, director, movie)
    logger.info("Trailer saved to %s", trailer_path)

    try:
        send_trailer_to_feishu(app_id, app_secret, chat_id, markdown, receive_id_type)
    except Exception as e:
        logger.exception("Feishu send failed: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
