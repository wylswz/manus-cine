"""manus-cine main entry: recommend movie, generate trailer, send to Feishu."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import httpx

from .feishu import get_tenant_access_token, send_trailer_to_feishu, upload_image
from .manus import extract_image_urls, recommend_movie, strip_fig_section
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
# 撒旦探戈 / Sátántangó
导演：贝拉·塔尔（Béla Tarr）　年份：1994　国家：匈牙利

## 故事

在匈牙利一个阴郁破败的集体农庄里，秋雨连绵，泥泞不堪。村民们在绝望与贪婪中挣扎，企图带着微薄的积蓄逃离这片被诅咒的土地。此时，传闻早已死去的神秘人物伊里米亚什突然归来，宛如救世主般降临。他用虚伪的承诺与煽动性的言辞，将这些迷途的灵魂引入了更深的深渊，上演了一出荒诞而悲凉的末世群像剧。

## 影像

纯粹的黑白影像剥离了现实的浮华，将阴郁的氛围推向极致。贝拉·塔尔以其标志性的超长镜头，冷酷地凝视着荒原、破败的建筑与泥泞的道路。光影在阴暗中缓慢流转，镜头如幽灵般平缓推拉，构建出一种极具压迫感与雕塑感的视觉空间，每一帧都如同末日降临前的废墟挽歌。

## 叙事

影片打破了线性时间，采用探戈舞步般"退六步，进六步"的非线性环状结构，多视角重构了同一时间段内的事件。长达七个半小时的缓慢节奏，将时间的流逝具象化，强迫观众沉浸于那份凝滞与绝望之中。它不仅是对集体主义破灭的哀叹，更是对人类永恒的精神困境与存在虚无的深刻剖析。

## 为何值得一看

这是一次对观影耐力的极限挑战，也是一场洗涤灵魂的朝圣之旅。它将电影的时间与空间属性推向了极致，留下了一种超越语言的纯粹电影体验。在这个碎片化的时代，它以其沉重与缓慢，赋予了我们直面现实荒芜与人性深渊的勇气。

## 预告片（如有）
https://www.youtube.com/watch?v=SlLCphjFGrk

## 同行评价（如有）
"对于《撒旦探戈》长达七个半小时的每一分钟，我都感到震撼和着迷。如果可能的话，我愿意在有生之年，每年都看一遍。"—— 苏珊·桑塔格（Susan Sontag，著名作家、评论家）
"贝拉·塔尔是这个时代少数几个真正具有远见的电影人之一。"—— Gus Van Sant（格斯·范·桑特，美国知名导演）
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
        result = {
            "markdown": MOCK_MARKDOWN,
            "director": "贝拉·塔尔",
            "movie": "撒旦探戈",
            "year": "1994",
            "original_title": "Sátántangó",
            "image_files": [
                {
                    "file_url": "https://testimages.org/img/testimages_screenshot.jpg",
                    "file_name": "test_image.jpg",
                    "mime_type": "image/jpeg",
                },
            ],
        }
    else:
        api_key = _env("MANUS_API_KEY")
        resume_task_id = os.environ.get("MANUS_TASK_ID") or None
        if resume_task_id:
            logger.info("MANUS_TASK_ID=%s: resuming existing task", resume_task_id)
        try:
            result = recommend_movie(api_key, excluded_movies, resume_task_id=resume_task_id)
        except Exception as e:
            logger.exception("Manus API failed: %s", e)
            sys.exit(2)

    director = result["director"]
    movie = result["movie"]
    markdown = result["markdown"]
    image_files = result.get("image_files") or []
    logger.info("Recommended: %s - %s", director, movie)

    if not mock_mode:
        save_recommendation(director, movie)
    trailer_path = save_trailer(markdown, director, movie)
    logger.info("Trailer saved to %s", trailer_path)

    image_key: str | None = None
    manus_api_key = os.environ.get("MANUS_API_KEY", "")

    def _try_upload_image(image_bytes: bytes, source_label: str) -> str | None:
        """Upload image bytes to Feishu; return image_key or None on failure."""
        try:
            logger.info("Uploading image to Feishu (%d bytes) from %s", len(image_bytes), source_label)
            tok = get_tenant_access_token(app_id, app_secret)
            key = upload_image(tok, image_bytes)
            logger.info("Feishu image_key: %s", key)
            return key
        except Exception as upload_err:
            logger.warning("Feishu image upload failed [%s]: %s", source_label, upload_err)
            return None

    def _download_image(url: str) -> bytes | None:
        """Download image from URL; return bytes or None."""
        try:
            headers: dict[str, str] = {"User-Agent": "manus-cine/1.0 (movie trailer bot)"}
            if manus_api_key and "manus" in url.lower():
                headers["API_KEY"] = manus_api_key
            r = httpx.get(url, timeout=20.0, follow_redirects=True, headers=headers)
            if r.status_code != 200:
                logger.debug("Image download got HTTP %d for %s", r.status_code, url[:60])
                return None
            ct = (r.headers.get("content-type") or "").lower()
            if ct and not ct.startswith("image/"):
                logger.debug("Unexpected content-type %r for %s", ct, url[:60])
                return None
            data = r.content
            if not data:
                return None
            if len(data) > 10 * 1024 * 1024:
                logger.warning("Image too large (%d bytes), skipping", len(data))
                return None
            logger.info("Downloaded image %d bytes (ct=%s) from %s", len(data), ct, url[:70])
            return data
        except Exception as dl_err:
            logger.warning("Image download failed [%s]: %s", url[:60], dl_err)
            return None

    # 1) Prefer image file(s) from Manus output_file
    if not image_files:
        logger.info("Manus returned no image files; will try markdown links if any")
    for f in image_files:
        url = f.get("file_url", "")
        if not url:
            continue
        data = _download_image(url)
        if data:
            image_key = _try_upload_image(data, "manus-output-file")
            if image_key:
                break

    # 2) Fallback: image URLs embedded in the markdown text
    if not image_key:
        for url in extract_image_urls(markdown):
            data = _download_image(url)
            if data:
                image_key = _try_upload_image(data, "markdown-link")
                if image_key:
                    break

    markdown_for_feishu = strip_fig_section(markdown)
    try:
        send_trailer_to_feishu(app_id, app_secret, chat_id, markdown_for_feishu, receive_id_type, image_key=image_key)
    except Exception as e:
        logger.exception("Feishu send failed: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
