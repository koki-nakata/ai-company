#!/usr/bin/env python3
"""Get Google OAuth access token from refresh token."""
import os, sys, json, urllib.request, urllib.parse

def get_token(refresh_token_env):
    data = urllib.parse.urlencode({
        'client_id': os.environ['GOOGLE_CLIENT_ID'],
        'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'refresh_token': os.environ[refresh_token_env],
        'grant_type': 'refresh_token'
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']

if __name__ == '__main__':
    print(get_token(sys.argv[1]))
