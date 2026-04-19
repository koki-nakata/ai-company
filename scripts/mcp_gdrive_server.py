#!/usr/bin/env python3
"""Google Drive / Docs MCP server — search, createGoogleDoc, updateGoogleDoc."""
import os
import sys
import json
import urllib.request
import urllib.parse
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(__file__))
from google_token import get_token

mcp = FastMCP("gdrive")

FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "1BOIRQdX2M4uqdxRYWtPAQc4tFdydTHKH")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post(url: str, token: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=_headers(token))
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _patch(url: str, token: str, data: dict = None) -> dict:
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body, headers=_headers(token), method="PATCH")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


@mcp.tool()
def search(query: str) -> str:
    """Search files in Google Drive.

    Args:
        query: Search query string (e.g. file title or keyword).
    """
    try:
        token = get_token("GDRIVE_REFRESH_TOKEN")
        q = urllib.parse.urlencode({"q": query, "fields": "files(id,name,webViewLink,mimeType)"})
        url = f"https://www.googleapis.com/drive/v3/files?{q}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        files = result.get("files", [])
        if not files:
            return "（該当ファイルなし）"
        lines = [f"## 検索結果: {query}\n"]
        for f in files:
            lines.append(f"- [{f['name']}]({f.get('webViewLink', '')}) — {f['id']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def createGoogleDoc(title: str, content: str, folder_id: str = "") -> str:
    """Create a new Google Doc in the eng/タスク folder.

    Args:
        title: Document title.
        content: Text content to insert into the document.
        folder_id: Google Drive folder ID. Defaults to eng/タスク folder.
    """
    try:
        token = get_token("GDRIVE_REFRESH_TOKEN")
        target_folder = folder_id or FOLDER_ID

        # Create the document
        doc = _post("https://docs.googleapis.com/v1/documents", token, {"title": title})
        doc_id = doc["documentId"]

        # Insert content
        if content:
            _post(
                f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                token,
                {"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            )

        # Move to target folder
        move_url = (
            f"https://www.googleapis.com/drive/v3/files/{doc_id}"
            f"?addParents={target_folder}&removeParents=root"
        )
        _patch(move_url, token)

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return f"作成完了: {doc_url}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def updateGoogleDoc(document_id: str, content: str) -> str:
    """Overwrite an existing Google Doc with new content.

    Args:
        document_id: The Google Doc document ID.
        content: New text content to replace the document body.
    """
    try:
        token = get_token("GDRIVE_REFRESH_TOKEN")

        # Get current doc to find end index
        req = urllib.request.Request(
            f"https://docs.googleapis.com/v1/documents/{document_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req) as r:
            doc = json.loads(r.read())
        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        requests = []
        # Delete existing content (keep index 1)
        if end_index > 1:
            requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index}}})
        # Insert new content
        requests.append({"insertText": {"location": {"index": 1}, "text": content}})

        _post(
            f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
            token,
            {"requests": requests},
        )

        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        return f"更新完了: {doc_url}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
