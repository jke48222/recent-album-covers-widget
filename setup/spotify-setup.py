#!/usr/bin/env python3
"""One-time Spotify authorization for the Recent Album Covers widget.

Prerequisite: ~/.config/widgetsuite/spotify.json containing your app's
  {"client_id": "...", "client_secret": "..."}
from https://developer.spotify.com/dashboard. In that app's settings, add the
redirect URI exactly:  http://127.0.0.1:8723/callback

This runs the OAuth authorization-code flow (opens your browser, captures the
redirect on a temporary local server) and writes the resulting refresh_token
back into spotify.json. Scope requested: user-read-recently-played.
"""
import base64
import json
import os
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CONF = os.path.expanduser("~/.config/widgetsuite/spotify.json")
REDIRECT = "http://127.0.0.1:8723/callback"
SCOPE = "user-read-recently-played"
box = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        box["code"] = (urllib.parse.parse_qs(parsed.query).get("code") or [""])[0]
        self.send_response(200)
        self.send_header("content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Spotify connected. You can close this tab.</h2>")

    def log_message(self, *a):
        pass


def main():
    try:
        c = json.load(open(CONF))
    except Exception:
        print("Create %s with {\"client_id\":..., \"client_secret\":...} first." % CONF)
        return
    cid, secret = c.get("client_id"), c.get("client_secret")
    if not (cid and secret):
        print("spotify.json needs client_id and client_secret.")
        return

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": cid, "response_type": "code",
        "redirect_uri": REDIRECT, "scope": SCOPE})
    srv = HTTPServer(("127.0.0.1", 8723), Handler)
    print("Opening browser to authorize Spotify...")
    webbrowser.open(auth_url)
    srv.handle_request()  # serve the single callback request

    code = box.get("code", "")
    if not code:
        print("No authorization code received.")
        return
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT}).encode()
    auth = base64.b64encode((cid + ":" + secret).encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token", data=body,
        headers={"Authorization": "Basic " + auth,
                 "content-type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as r:
        tok = json.load(r)
    rt = tok.get("refresh_token", "")
    if not rt:
        print("No refresh_token returned:", tok)
        return
    c["refresh_token"] = rt
    json.dump(c, open(CONF, "w"), indent=2)
    print("Saved refresh_token to", CONF)


main()
