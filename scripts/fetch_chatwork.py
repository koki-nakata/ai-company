#!/usr/bin/env python3
"""Fetch Chatwork messages. Usage: fetch_chatwork.py LAST_DATE"""
import os, sys, json, urllib.request
from datetime import datetime, timezone, timedelta

API_TOKEN = os.environ.get('CHATWORK_API_TOKEN', '')

def cw_get(path):
    req = urllib.request.Request(
        f'https://api.chatwork.com/v2{path}',
        headers={'X-ChatWorkToken': API_TOKEN}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    last_date = sys.argv[1] if len(sys.argv) > 1 else ''
    if last_date:
        since_ts = int(datetime.strptime(last_date, '%Y-%m-%d')
                       .replace(tzinfo=timezone(timedelta(hours=9))).timestamp())
    else:
        since_ts = int((datetime.now(timezone(timedelta(hours=9))).timestamp()) - 86400)

    rooms = cw_get('/rooms')
    print(f'## Chatwork — {last_date}以降\n')

    for room in rooms:
        room_id = room['room_id']
        room_name = room.get('name', str(room_id))
        unread = room.get('unread_num', 0)

        try:
            msgs = cw_get(f'/rooms/{room_id}/messages?force=1')
        except Exception:
            continue

        recent = [m for m in msgs if m.get('send_time', 0) >= since_ts]
        if not recent:
            continue

        print(f'### {room_name}{"【未読"+str(unread)+"件】" if unread else ""}')
        for m in recent[:15]:
            ts = m.get('send_time', 0)
            dt_str = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')
            sender = m.get('account', {}).get('name', '')[:15]
            body = m.get('body', '')[:120].replace('\n', ' ')
            print(f'- [{dt_str}] {sender}: {body}')
        print()

if __name__ == '__main__':
    main()
