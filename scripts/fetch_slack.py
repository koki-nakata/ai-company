#!/usr/bin/env python3
"""Fetch Slack messages. Usage: fetch_slack.py sankei|concierge LAST_DATE"""
import os, sys, json, urllib.request, urllib.parse, time
from datetime import datetime, timezone, timedelta

def api(endpoint, token, params=None):
    url = f'https://slack.com/api/{endpoint}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    workspace = sys.argv[1] if len(sys.argv) > 1 else 'sankei'
    last_date = sys.argv[2] if len(sys.argv) > 2 else ''

    token_key = 'SLACK_SANKEI_TOKEN' if workspace == 'sankei' else 'SLACK_CONCIERGE_TOKEN'
    token = os.environ[token_key]

    # oldest timestamp
    if last_date:
        dt = datetime.strptime(last_date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=9)))
        oldest = str(dt.timestamp())
    else:
        oldest = str(time.time() - 86400)

    # Get channels
    ch_result = api('conversations.list', token, {'types': 'public_channel,private_channel', 'limit': 200, 'exclude_archived': 'true'})
    channels = ch_result.get('channels', [])

    print(f'## Slack ({workspace}) — {last_date}以降\n')
    found = False
    for ch in channels:
        ch_id = ch['id']
        ch_name = ch.get('name', '')
        hist = api('conversations.history', token, {'channel': ch_id, 'oldest': oldest, 'limit': 30})
        msgs = [m for m in hist.get('messages', []) if m.get('type') == 'message' and not m.get('bot_id')]
        if not msgs:
            continue
        found = True
        print(f'### #{ch_name}')
        for m in msgs[:10]:
            ts = float(m.get('ts', 0))
            dt_str = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')
            user = m.get('user', m.get('username', ''))[:15]
            text = m.get('text', '')[:120].replace('\n', ' ')
            print(f'- [{dt_str}] {user}: {text}')
        print()

    if not found:
        print('メッセージなし')

if __name__ == '__main__':
    main()
