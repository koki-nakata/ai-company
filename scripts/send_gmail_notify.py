#!/usr/bin/env python3
"""Send Gmail notification. Usage: send_gmail_notify.py SUBJECT BODY_FILE DOC_URL"""
import os, sys, json, base64, urllib.request, urllib.parse
from email.mime.text import MIMEText
sys.path.insert(0, os.path.dirname(__file__))
from google_token import get_token

TO_ADDRESS = 'contactcomparison@gmail.com'

def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else 'タスクリスト'
    body_file = sys.argv[2] if len(sys.argv) > 2 else None
    doc_url = sys.argv[3] if len(sys.argv) > 3 else ''

    body = ''
    if body_file and os.path.exists(body_file):
        with open(body_file, 'r', encoding='utf-8') as f:
            body = f.read()
    if doc_url:
        body = f'📄 Google Doc: {doc_url}\n\n' + body

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['To'] = TO_ADDRESS
    msg['Subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    token = get_token('GMAIL_REFRESH_TOKEN')
    data = json.dumps({'raw': raw}).encode()
    req = urllib.request.Request(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    print(f'送信完了: messageId={result.get("id")}')

if __name__ == '__main__':
    main()
