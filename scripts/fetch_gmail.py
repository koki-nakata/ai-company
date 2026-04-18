#!/usr/bin/env python3
"""Fetch Gmail messages since last_date. Usage: fetch_gmail.py LAST_DATE"""
import os, sys, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from google_token import get_token

def api_get(url, token):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    last_date = sys.argv[1] if len(sys.argv) > 1 else ''
    after = last_date.replace('-', '/')
    token = get_token('GMAIL_REFRESH_TOKEN')

    query = urllib.parse.quote(f'after:{after} -category:promotions -category:social -category:forums -from:noreply')
    result = api_get(f'https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query}&maxResults=30', token)
    messages = result.get('messages', [])

    if not messages:
        print(f'## Gmail ({last_date}以降)\nメールなし')
        return

    print(f'## Gmail重要メール ({last_date}以降)\n')
    for msg in messages[:25]:
        detail = api_get(
            f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg["id"]}'
            '?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date',
            token
        )
        h = {x['name']: x['value'] for x in detail.get('payload', {}).get('headers', [])}
        labels = detail.get('labelIds', [])
        is_unread = 'UNREAD' in labels
        subject = h.get('Subject', '(件名なし)')[:60]
        sender = h.get('From', '(不明)')[:40]
        date = h.get('Date', '')[:16]
        snippet = detail.get('snippet', '')[:100]
        unread_mark = '【未読】' if is_unread else ''
        print(f'- {unread_mark}**{subject}**')
        print(f'  送信者: {sender} | {date}')
        print(f'  概要: {snippet}')
        print()

if __name__ == '__main__':
    main()
