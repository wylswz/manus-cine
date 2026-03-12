"""Feishu (Lark) API client for sending messages."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """Get Feishu tenant_access_token."""
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            TOKEN_URL,
            json={"app_id": app_id, "app_secret": app_secret},
        )
        r.raise_for_status()
        data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    return data["tenant_access_token"]


def send_text_message(
    token: str, chat_id: str, text: str, receive_id_type: str = "chat_id"
) -> dict[str, Any]:
    """Send text message to Feishu chat."""
    import json as _json
    content_json = _json.dumps({"text": text}, ensure_ascii=False)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{MESSAGE_URL}?receive_id_type={receive_id_type}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": content_json,
            },
        )
        r.raise_for_status()
        return r.json()


def send_trailer_to_feishu(
    app_id: str, app_secret: str, chat_id: str, markdown_content: str
) -> None:
    """
    Get token and send trailer content to Feishu.
    Uses text message; Feishu text supports basic formatting.
    """
    token = get_tenant_access_token(app_id, app_secret)
    # Truncate if too long (Feishu text limit ~4k)
    if len(markdown_content) > 3500:
        markdown_content = markdown_content[:3500] + "\n\n...(内容过长已截断)"
    send_text_message(token, chat_id, markdown_content)
    logger.info("Sent trailer to Feishu chat %s", chat_id)
