"""Feishu (Lark) API client."""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
IMAGE_UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/images"


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret})
        r.raise_for_status()
        data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    return data["tenant_access_token"]


def _image_content_type(image_bytes: bytes) -> tuple[str, str]:
    """Return (filename, content_type) for Feishu upload."""
    if image_bytes[:8].startswith(b"\x89PNG"):
        return "poster.png", "image/png"
    if image_bytes[:2] == b"\xff\xd8":
        return "poster.jpg", "image/jpeg"
    return "poster.jpg", "image/jpeg"


def upload_image(token: str, image_bytes: bytes) -> str:
    """Upload image to Feishu, return image_key for use in post."""
    fname, content_type = _image_content_type(image_bytes)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            IMAGE_UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files={
                "image_type": (None, "message"),
                "image": (fname, image_bytes, content_type),
            },
        )
    if r.status_code != 200:
        raise RuntimeError(
            f"Feishu image upload HTTP {r.status_code}: {r.text[:300]}"
        )
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu image upload error code {data.get('code')}: {data}")
    image_key = data.get("data", {}).get("image_key")
    if not image_key:
        raise ValueError("Feishu did not return image_key")
    return image_key


def _md_to_post(markdown: str, image_key: str | None = None) -> dict:
    """Convert simple Markdown report to Feishu post (富文本) format. Optionally insert poster image at top."""
    title = ""
    lines: list[list[dict]] = []

    for line in markdown.splitlines():
        stripped = line.strip()

        if stripped.startswith("# "):
            title = stripped[2:].strip()
            continue

        if stripped.startswith("## "):
            section = stripped[3:].strip()
            if lines:
                lines.append([{"tag": "text", "text": ""}])
            lines.append([{"tag": "text", "text": section, "style": ["bold"]}])
            continue

        if stripped in ("---", ""):
            continue

        lines.append([{"tag": "text", "text": stripped}])

    content = lines
    if image_key:
        content = [[{"tag": "img", "image_key": image_key}], [{"tag": "text", "text": ""}]] + content

    return {"zh_cn": {"title": title or "今日推荐", "content": content}}


def send_message(
    token: str,
    receive_id: str,
    receive_id_type: str,
    msg_type: str,
    content: str,
) -> dict[str, Any]:
    payload = json.dumps(
        {"receive_id": receive_id, "msg_type": msg_type, "content": content},
        ensure_ascii=False,
    )
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
    markdown: str,
    receive_id_type: str = "chat_id",
    image_key: str | None = None,
) -> None:
    token = get_tenant_access_token(app_id, app_secret)
    post = _md_to_post(markdown, image_key=image_key)
    send_message(
        token,
        chat_id,
        receive_id_type,
        msg_type="post",
        content=json.dumps(post, ensure_ascii=False),
    )
    logger.info("Sent to Feishu %s %s (with image: %s)", receive_id_type, chat_id, bool(image_key))
