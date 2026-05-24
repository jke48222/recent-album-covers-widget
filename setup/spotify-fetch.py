#!/usr/bin/env python3
"""Spotify recently-played fetcher for the Recent Album Covers widget.

Outputs RS/FS-delimited "cover<FS>albumURL" slots (the same format the widget
parses), deduped to nine distinct album covers in recency order. Prints an empty
line when not configured, so the widget falls back to its other sources.

Config: ~/.config/widgetsuite/spotify.json
  {"client_id": "...", "client_secret": "...", "refresh_token": "..."}
Run spotify-setup.py once to obtain the refresh_token.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

CONF = os.path.expanduser("~/.config/widgetsuite/spotify.json")
RS = chr(30)
FS = chr(28)


def conf():
    try:
        return json.load(open(CONF))
    except Exception:
        return {}


def access_token(c):
    if not (c.get("client_id") and c.get("client_secret") and c.get("refresh_token")):
        return ""
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": c["refresh_token"],
    }).encode()
    auth = base64.b64encode((c["client_id"] + ":" + c["client_secret"]).encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token", data=body,
        headers={"Authorization": "Basic " + auth,
                 "content-type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r).get("access_token", "")
    except Exception:
        return ""


def fetch_recent():
    c = conf()
    tok = access_token(c)
    if not tok:
        return ""
    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/player/recently-played?limit=30",
        headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception:
        return ""
    slots, seen = [], set()
    for it in data.get("items", []):
        al = (it.get("track") or {}).get("album") or {}
        imgs = al.get("images") or []
        cover = imgs[0]["url"] if imgs else ""
        if not cover or cover in seen:
            continue
        seen.add(cover)
        link = (al.get("external_urls") or {}).get("spotify", "")
        slots.append(cover + FS + link)
        if len(slots) >= 9:
            break
    if not any(s.split(FS)[0] for s in slots):
        return ""
    return RS.join(slots)


print(fetch_recent())
