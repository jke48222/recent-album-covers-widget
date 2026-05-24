#!/usr/bin/env python3
"""MusicKit / Apple Music API fetcher for the Music Archive widget.

Returns the user's heavy-rotation albums (most-played recently) as the same
RS/FS-delimited "cover<FS>albumURL" slots the widget already parses, so the
widget can use real Apple Music data with proper artwork and per-album links.

Setup (one time), all under ~/.config/widgetsuite/ :
  musickit.p8                 your MusicKit private key (.p8) from Apple
  musickit.json               {"keyId": "ABC123", "teamId": "DEF456"}
  musickit-user-token.txt     the Music User Token (run musickit-setup.sh)

The developer token (ES256 JWT) is generated with openssl and cached in
musickit-devtoken.json for ~150 days. Prints an empty line if not configured,
so the widget falls back to its iTunes/AppleScript path.

Usage:
  musickit-fetch.py            -> RS/FS album slots (or empty)
  musickit-fetch.py --devtoken -> just the developer token (for the auth page)
  musickit-fetch.py --nowplaying [MAC_TRACK] [MAC_ARTIST]
        -> JSON for the account's most-recently-played track (captures playback
           on any device, e.g. iPhone), used by the NowSpinning widget when the
           Mac itself is not actively playing. Stays empty when that track is
           the same one MAC_TRACK names (the Mac just paused it), so the widget
           keeps the Mac's paused/idle state instead of falsely spinning.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

CFG = os.path.expanduser("~/.config/widgetsuite")
P8 = os.path.join(CFG, "musickit.p8")
CONF = os.path.join(CFG, "musickit.json")
USERTOK = os.path.join(CFG, "musickit-user-token.txt")
DEVCACHE = os.path.join(CFG, "musickit-devtoken.json")
NPCACHE = os.path.join(CFG, "musickit-nowplaying-cache.json")
RS = chr(30)
FS = chr(28)


def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def der_to_raw(der):
    # ECDSA DER: 0x30 len 0x02 rlen r 0x02 slen s -> raw r||s (32+32)
    i = 2
    if der[1] & 0x80:
        i = 2 + (der[1] & 0x7F)
    assert der[i] == 0x02; i += 1
    rl = der[i]; i += 1
    r = der[i:i + rl]; i += rl
    assert der[i] == 0x02; i += 1
    sl = der[i]; i += 1
    s = der[i:i + sl]
    r = r.lstrip(b"\x00"); s = s.lstrip(b"\x00")
    r = b"\x00" * (32 - len(r)) + r
    s = b"\x00" * (32 - len(s)) + s
    return r + s


def gen_dev_token():
    try:
        conf = json.load(open(CONF))
        kid, team = conf["keyId"], conf["teamId"]
    except Exception:
        return ""
    if not os.path.exists(P8):
        return ""
    now = int(time.time())
    exp = now + 150 * 86400
    header = b64url(json.dumps({"alg": "ES256", "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({"iss": team, "iat": now, "exp": exp}, separators=(",", ":")).encode())
    signing_input = (header + "." + payload).encode()
    try:
        der = subprocess.run(["openssl", "dgst", "-sha256", "-sign", P8],
                             input=signing_input, capture_output=True, timeout=10).stdout
        token = signing_input.decode() + "." + b64url(der_to_raw(der))
    except Exception:
        return ""
    try:
        json.dump({"token": token, "exp": exp}, open(DEVCACHE, "w"))
    except Exception:
        pass
    return token


def dev_token():
    try:
        c = json.load(open(DEVCACHE))
        if c.get("token") and c.get("exp", 0) - time.time() > 7 * 86400:
            return c["token"]
    except Exception:
        pass
    return gen_dev_token()


def user_token():
    try:
        return open(USERTOK).read().strip()
    except Exception:
        return ""


def fetch_albums():
    dev = dev_token()
    usr = user_token()
    if not dev or not usr:
        return ""
    # Recently played tracks: the freshest, fullest stream. Many tracks share an
    # album cover, so dedupe by the raw (templated) artwork URL — one tile per
    # distinct cover — and keep the first 9 in recency order.
    url = "https://api.music.apple.com/v1/me/recent/played/tracks?limit=30"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + dev,
        "Music-User-Token": usr,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception:
        return ""
    slots = []
    seen = set()
    for it in data.get("data", []):
        a = it.get("attributes", {})
        raw = (a.get("artwork", {}) or {}).get("url", "") or ""
        if not raw or raw in seen:
            continue
        seen.add(raw)
        art = raw.replace("{w}", "400").replace("{h}", "400").replace("{f}", "jpg")
        link = a.get("url", "") or ""
        slots.append(art + FS + link)
        if len(slots) >= 9:
            break
    if not any(s.split(FS)[0] for s in slots):
        return ""
    return RS.join(slots)


def recent_top():
    # The single most-recently-played track's attributes, across all of the
    # account's devices. Cached briefly so the 2s NowSpinning refresh doesn't
    # hammer the API — play/pause responsiveness comes from the local Mac check,
    # this only needs to track which song is on.
    try:
        c = json.load(open(NPCACHE))
        if time.time() - c.get("ts", 0) < 10:
            return c.get("attr")
    except Exception:
        pass
    dev = dev_token()
    usr = user_token()
    if not dev or not usr:
        return None
    url = "https://api.music.apple.com/v1/me/recent/played/tracks?limit=1"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + dev,
        "Music-User-Token": usr,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception:
        return None
    items = data.get("data", [])
    attr = items[0].get("attributes", {}) if items else None
    try:
        json.dump({"ts": time.time(), "attr": attr}, open(NPCACHE, "w"))
    except Exception:
        pass
    return attr


def fetch_nowplaying(mac_track="", mac_artist=""):
    a = recent_top()
    if not a:
        return ""
    track = a.get("name", "") or ""
    if not track:
        return ""
    norm = lambda s: " ".join((s or "").lower().split())
    # Same song the Mac is already showing (just paused) -> let the Mac path own
    # it so its paused/idle state is preserved.
    if mac_track and norm(track) == norm(mac_track):
        return ""
    raw = (a.get("artwork", {}) or {}).get("url", "") or ""
    art = raw.replace("{w}", "600").replace("{h}", "600").replace("{f}", "jpg") if raw else None
    return json.dumps({
        "track": track,
        "artist": a.get("artistName", "") or "",
        "album": a.get("albumName", "") or "",
        "art": art,
        "playing": True,
        "url": a.get("url", "") or "",
    })


def fetch_cover(track="", artist="", album=""):
    # Correct Apple Music cover for a specific track via a catalog song search
    # (needs only the developer token). Used by NowSpinning to get the right
    # sleeve for the Mac's currently-playing track. Empty when not found.
    import urllib.parse
    dev = dev_token()
    if not dev or not track:
        return ""
    term = " ".join(x for x in [artist, track] if x)
    qs = urllib.parse.urlencode({"term": term, "types": "songs", "limit": "1"})
    url = "https://api.music.apple.com/v1/catalog/us/search?" + qs
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + dev})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception:
        return ""
    songs = (((data.get("results") or {}).get("songs") or {}).get("data") or [])
    if not songs:
        return ""
    raw = ((songs[0].get("attributes", {}) or {}).get("artwork", {}) or {}).get("url", "") or ""
    if not raw:
        return ""
    return raw.replace("{w}", "600").replace("{h}", "600").replace("{f}", "jpg")


def main():
    if "--devtoken" in sys.argv:
        print(dev_token())
        return
    if "--nowplaying" in sys.argv:
        rest = sys.argv[sys.argv.index("--nowplaying") + 1:]
        print(fetch_nowplaying(rest[0] if len(rest) > 0 else "",
                               rest[1] if len(rest) > 1 else ""))
        return
    if "--cover" in sys.argv:
        rest = sys.argv[sys.argv.index("--cover") + 1:]
        print(fetch_cover(rest[0] if len(rest) > 0 else "",
                          rest[1] if len(rest) > 1 else "",
                          rest[2] if len(rest) > 2 else ""))
        return
    print(fetch_albums())


main()
