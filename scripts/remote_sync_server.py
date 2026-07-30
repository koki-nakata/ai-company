#!/usr/bin/env python3
"""Remote-hosted MCP server exposing Chatwork + Slack (sankei/concierge) read-only tools
over HTTP, for use as a custom connector on claude.ai Remote Triggers.

This mirrors the local stdio-based MCP servers (mcp_chatwork_server.py, and the
slack-sankei/slack-concierge servers) but uses direct API calls with tokens supplied
via environment variables, and runs over streamable-http so it can be deployed to a
persistent host (e.g. Render.com) instead of running as a local subprocess.

Required environment variables:
  CHATWORK_API_TOKEN
  SLACK_SANKEI_TOKEN
  SLACK_CONCIERGE_TOKEN
  MCP_AUTH_SECRET   -- shared secret; requests must send header
                       "Authorization: Bearer <MCP_AUTH_SECRET>"
"""
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

CHATWORK_TOKEN = os.environ.get("CHATWORK_API_TOKEN", "")
SLACK_TOKENS = {
    "sankei": os.environ.get("SLACK_SANKEI_TOKEN", ""),
    "concierge": os.environ.get("SLACK_CONCIERGE_TOKEN", ""),
}
AUTH_SECRET = os.environ.get("MCP_AUTH_SECRET", "")

# Bearer-token auth (below) already gates access, so the Host-header based
# DNS-rebinding protection (which otherwise only allows localhost) is disabled
# here rather than trying to allow-list Render's public hostname.
mcp = FastMCP(
    "ai-company-remote-sync",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


# ---------- Chatwork ----------

def _cw_get(path: str) -> object:
    req = urllib.request.Request(
        f"https://api.chatwork.com/v2{path}",
        headers={"X-ChatWorkToken": CHATWORK_TOKEN},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


@mcp.tool()
def chatwork_list_rooms() -> str:
    """List all Chatwork rooms the authenticated user belongs to."""
    if not CHATWORK_TOKEN:
        return "Error: CHATWORK_API_TOKEN is not set."
    try:
        rooms = _cw_get("/rooms")
        lines = ["## Chatwork ルーム一覧\n"]
        for room in rooms:
            unread = room.get("unread_num", 0)
            badge = f"【未読{unread}件】" if unread else ""
            lines.append(f"- room_id={room['room_id']} | {room.get('name', '')} {badge}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def chatwork_list_room_messages(room_id: int, force: bool = True) -> str:
    """List messages in a Chatwork room.

    Args:
        room_id: The numeric room ID.
        force: If True, fetch all messages (up to 100). Default True.
    """
    if not CHATWORK_TOKEN:
        return "Error: CHATWORK_API_TOKEN is not set."
    try:
        params = "?force=1" if force else ""
        msgs = _cw_get(f"/rooms/{room_id}/messages{params}")
        if not msgs:
            return "（メッセージなし）"
        lines = [f"## room_id={room_id} メッセージ\n"]
        for m in msgs[:50]:
            ts = m.get("send_time", 0)
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime("%m/%d %H:%M")
            sender = m.get("account", {}).get("name", "")[:20]
            body = m.get("body", "")[:200].replace("\n", " ")
            lines.append(f"- [{dt}] {sender}: {body}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ---------- Slack ----------

def _slack_api(endpoint: str, token: str, params: dict | None = None) -> dict:
    url = f"https://slack.com/api/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _slack_list_channels(workspace: str) -> str:
    token = SLACK_TOKENS.get(workspace, "")
    if not token:
        return f"Error: token for workspace '{workspace}' is not set."
    try:
        # Note: the sankei/concierge user tokens only have channels:read
        # (public), not groups:read (private) — requesting private_channel
        # here would make the whole call fail with missing_scope.
        result = _slack_api(
            "conversations.list", token,
            {"types": "public_channel", "limit": 200, "exclude_archived": "true"},
        )
        if not result.get("ok"):
            return f"Error: {result.get('error')}"
        lines = [f"## Slack ({workspace}) チャンネル一覧\n"]
        for ch in result.get("channels", []):
            lines.append(f"- id={ch['id']} | #{ch.get('name', '')} | member={ch.get('is_member')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _slack_get_channel_history(workspace: str, channel_id: str, limit: int = 50) -> str:
    token = SLACK_TOKENS.get(workspace, "")
    if not token:
        return f"Error: token for workspace '{workspace}' is not set."
    try:
        result = _slack_api(
            "conversations.history", token, {"channel": channel_id, "limit": limit}
        )
        if not result.get("ok"):
            return f"Error: {result.get('error')}"
        msgs = result.get("messages", [])
        if not msgs:
            return "（メッセージなし）"
        lines = [f"## Slack ({workspace}) #{channel_id} メッセージ\n"]
        for m in msgs:
            ts = float(m.get("ts", 0))
            dt_str = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime("%m/%d %H:%M")
            user = m.get("user", m.get("username", ""))[:15]
            text = m.get("text", "")[:300].replace("\n", " ")
            lines.append(f"- [{dt_str}] {user}: {text}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def slack_sankei_list_channels() -> str:
    """List Slack channels in the sankei (3BROS.WORKS) workspace."""
    return _slack_list_channels("sankei")


@mcp.tool()
def slack_sankei_get_channel_history(channel_id: str, limit: int = 50) -> str:
    """Get recent messages from a channel in the sankei workspace.

    Args:
        channel_id: The Slack channel ID (e.g. C034JJMV55K).
        limit: Number of messages to retrieve (default 50).
    """
    return _slack_get_channel_history("sankei", channel_id, limit)


@mcp.tool()
def slack_concierge_list_channels() -> str:
    """List Slack channels in the concierge (ARCHITECT CONCIERGE) workspace."""
    return _slack_list_channels("concierge")


@mcp.tool()
def slack_concierge_get_channel_history(channel_id: str, limit: int = 50) -> str:
    """Get recent messages from a channel in the concierge workspace.

    Args:
        channel_id: The Slack channel ID.
        limit: Number of messages to retrieve (default 50).
    """
    return _slack_get_channel_history("concierge", channel_id, limit)


# ---------- Auth middleware ----------

class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not AUTH_SECRET:
            return PlainTextResponse("Server misconfigured: MCP_AUTH_SECRET not set", status_code=500)
        auth = request.headers.get("authorization", "")
        # Some custom-connector UIs (e.g. claude.ai's "Add custom connector"
        # dialog) only offer an OAuth Client ID/Secret pair, not an arbitrary
        # header. Accept the secret as a ?auth= query param too, so it can be
        # embedded directly in the connector URL instead.
        query_auth = request.query_params.get("auth", "")
        if auth != f"Bearer {AUTH_SECRET}" and query_auth != AUTH_SECRET:
            return PlainTextResponse("Unauthorized", status_code=401)
        return await call_next(request)


if __name__ == "__main__":
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware)
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
