#!/usr/bin/env python3
"""Chatwork MCP server — provides list_rooms and list_room_messages tools."""
import os
import json
import urllib.request
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("chatwork")

API_TOKEN = os.environ.get("CHATWORK_API_TOKEN", "")


def _cw_get(path: str) -> object:
    req = urllib.request.Request(
        f"https://api.chatwork.com/v2{path}",
        headers={"X-ChatWorkToken": API_TOKEN},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


@mcp.tool()
def list_rooms() -> str:
    """List all Chatwork rooms the authenticated user belongs to."""
    if not API_TOKEN:
        return "Error: CHATWORK_API_TOKEN is not set."
    try:
        rooms = _cw_get("/rooms")
        lines = ["## Chatwork ルーム一覧\n"]
        for room in rooms:
            unread = room.get("unread_num", 0)
            badge = f"【未読{unread}件】" if unread else ""
            lines.append(
                f"- room_id={room['room_id']} | {room.get('name', '')} {badge}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_room_messages(room_id: int, force: bool = True) -> str:
    """List messages in a Chatwork room.

    Args:
        room_id: The numeric room ID.
        force: If True, fetch all messages (up to 100). Default True.
    """
    if not API_TOKEN:
        return "Error: CHATWORK_API_TOKEN is not set."
    try:
        params = "?force=1" if force else ""
        msgs = _cw_get(f"/rooms/{room_id}/messages{params}")
        if not msgs:
            return "（メッセージなし）"
        lines = [f"## room_id={room_id} メッセージ\n"]
        for m in msgs[:50]:
            from datetime import datetime, timezone, timedelta
            ts = m.get("send_time", 0)
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime("%m/%d %H:%M")
            sender = m.get("account", {}).get("name", "")[:20]
            body = m.get("body", "")[:200].replace("\n", " ")
            lines.append(f"- [{dt}] {sender}: {body}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
