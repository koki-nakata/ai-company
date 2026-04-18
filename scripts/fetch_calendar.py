#!/usr/bin/env python3
"""Fetch Google Calendar events. Usage: fetch_calendar.py LAST_DATE TODAY"""
import os, sys, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from google_token import get_token

def api_get(url, token):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    last_date = sys.argv[1] if len(sys.argv) > 1 else ''
    today = sys.argv[2] if len(sys.argv) > 2 else last_date
    token = get_token('GCAL_REFRESH_TOKEN')

    jst = timezone(timedelta(hours=9))
    time_min = urllib.parse.quote(f'{last_date}T00:00:00+09:00')
    time_max = urllib.parse.quote(f'{today}T23:59:59+09:00')

    result = api_get(
        f'https://www.googleapis.com/calendar/v3/calendars/primary/events'
        f'?timeMin={time_min}&timeMax={time_max}&singleEvents=true&orderBy=startTime&maxResults=20',
        token
    )
    items = result.get('items', [])

    print(f'## Google Calendar ({last_date}〜{today})\n')
    if not items:
        print('予定なし')
        return

    for item in items:
        start = item.get('start', {})
        start_str = start.get('dateTime', start.get('date', ''))[:16].replace('T', ' ')
        title = item.get('summary', '(タイトルなし)')
        location = item.get('location', '')
        loc_str = f' @ {location}' if location else ''
        print(f'- {start_str} **{title}**{loc_str}')

if __name__ == '__main__':
    main()
