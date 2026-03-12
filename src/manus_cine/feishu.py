"""Feishu (Lark) API client."""

import json
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret})
        r.raise_for_status()
        data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    return data["tenant_access_token"]


def _post_content(data: dict) -> dict:
    """Build Feishu post (富文本) content from movie recommendation data."""
    director = data.get("director", "")
    movie = data.get("movie", "")
    original_title = data.get("original_title", "")
    year = data.get("year", "")
    country = data.get("country", "")
    synopsis = data.get("synopsis", "")
    visual_style = data.get("visual_style", "")
    narrative = data.get("narrative", "")
    why_watch = data.get("why_watch", "")

    title = movie
    if original_title and original_title != movie:
        title = f"{movie}  /  {original_title}"

    meta_parts = [str(year) if year else "", country, f"导演：{director}"]
    meta = "　".join(p for p in meta_parts if p)

    def section(label: str, body: str) -> list[list[dict]]:
        return [
            [{"tag": "text", "text": label, "style": ["bold"]}],
            [{"tag": "text", "text": body}],
            [{"tag": "text", "text": ""}],
        ]

    lines: list[list[dict]] = [
        [{"tag": "text", "text": meta}],
        [{"tag": "text", "text": ""}],
    ]

    if synopsis:
        lines += section("故事", synopsis)
    if visual_style:
        lines += section("影像", visual_style)
    if narrative:
        lines += section("叙事", narrative)
    if why_watch:
        lines += section("为何值得一看", why_watch)

    lines.append([{"tag": "text", "text": datetime.now().strftime("%Y.%m.%d") + "　manus-cine"}])

    return {"zh_cn": {"title": title, "content": lines}}


def send_message(
    token: str,
    receive_id: str,
    receive_id_type: str,
    msg_type: str,
    content: str,
) -> dict[str, Any]:
    payload = json.dumps({
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": content,
    }, ensure_ascii=False)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            MESSAGE_URL,
            params={"receive_id_type": receive_id_type},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            content=payload.encode("utf-8"),
        )
    logger.debug("Feishu response: %s %s", r.status_code, r.text)
    resp = r.json()
    if resp.get("code") != 0:
        raise RuntimeError(f"Feishu send error: {resp}")
    return resp


def send_trailer_to_feishu(
    app_id: str,
    app_secret: str,
    chat_id: str,
    data: dict,
    receive_id_type: str = "chat_id",
) -> None:
    token = get_tenant_access_token(app_id, app_secret)
    post = _post_content(data)
    send_message(
        token,
        chat_id,
        receive_id_type,
        msg_type="post",
        content=json.dumps(post, ensure_ascii=False),
    )
    logger.info("Sent to Feishu %s %s", receive_id_type, chat_id)
