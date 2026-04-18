#!/usr/bin/env python3
"""Create Google Doc in eng/タスク folder. Usage: create_gdoc.py TITLE CONTENT_FILE"""
import os, sys, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from google_token import get_token

FOLDER_ID = '1BOIRQdX2M4uqdxRYWtPAQc4tFdydTHKH'

def api_post(url, token, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    title = sys.argv[1] if len(sys.argv) > 1 else 'タスクリスト'
    content_file = sys.argv[2] if len(sys.argv) > 2 else None

    token = get_token('GDRIVE_REFRESH_TOKEN')

    # Create doc
    doc = api_post('https://docs.googleapis.com/v1/documents', token, {'title': title})
    doc_id = doc['documentId']

    # Insert content
    if content_file and os.path.exists(content_file):
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        api_post(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate', token, {
            'requests': [{'insertText': {'location': {'index': 1}, 'text': content}}]
        })

    # Move to eng/タスク folder
    move_url = f'https://www.googleapis.com/drive/v3/files/{doc_id}?addParents={FOLDER_ID}&removeParents=root'
    req = urllib.request.Request(move_url, data=b'{}', headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }, method='PATCH')
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    url = f'https://docs.google.com/document/d/{doc_id}/edit'
    print(url)

if __name__ == '__main__':
    main()
