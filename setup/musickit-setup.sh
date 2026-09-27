#!/bin/bash
# One-time MusicKit setup. Prereqs in ~/.config/widgetsuite/ :
#   musickit.p8    your MusicKit private key (.p8) from the Apple Developer portal
#   musickit.json  {"keyId": "ABC123DEF4", "teamId": "TEAMID1234"}
#
# Generates the developer token, writes an authorize page with it embedded, and
# opens it. Click "Authorize Apple Music", sign in, then paste the token shown
# into ~/.config/widgetsuite/musickit-user-token.txt
set -euo pipefail
CFG="$HOME/.config/widgetsuite"
PORT="${MUSICKIT_SETUP_PORT:-8722}"
# How long the local authorize page stays up. The server stops after this
# even if the terminal is closed.
SERVE_SECONDS="${MUSICKIT_SETUP_SECONDS:-600}"

if [ ! -f "$CFG/musickit.p8" ] || [ ! -f "$CFG/musickit.json" ]; then
  echo "Missing $CFG/musickit.p8 and/or $CFG/musickit.json (needs keyId, teamId)."
  exit 1
fi

DEV=$(/usr/bin/python3 "$CFG/musickit-fetch.py" --devtoken)
if [ -z "$DEV" ]; then echo "Could not generate developer token. Check musickit.json + musickit.p8."; exit 1; fi

# The page is served from a private temporary folder that holds nothing but
# the page, so nothing else in $CFG (the .p8 key, the tokens) can be fetched.
SERVE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/musickit-auth.XXXXXX")"
chmod 700 "$SERVE_DIR"
# Earlier versions left the page, with the developer token in it, in $CFG.
rm -f "$CFG/musickit-auth.html"
HTML="$SERVE_DIR/musickit-auth.html"
cat > "$HTML" <<EOF
<!doctype html><html><head><meta charset="utf-8"><title>WidgetSuite · Apple Music</title>
<script src="https://js-cdn.music.apple.com/musickit/v3/musickit.js" data-web-components async></script>
<style>
  body{font-family:-apple-system,system-ui;background:#0d0d12;color:#eee;margin:0;height:100vh;
       display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:24px}
  button{font:600 16px -apple-system;padding:12px 22px;border-radius:10px;border:0;
         background:#fa2d48;color:#fff;cursor:pointer}
  textarea{width:min(640px,90vw);height:120px;border-radius:10px;background:#1a1a22;color:#9be;
           border:1px solid #333;padding:10px;font-family:ui-monospace,monospace;font-size:12px}
  code{background:#1a1a22;padding:2px 6px;border-radius:5px}
  p{opacity:.8;text-align:center;max-width:560px;line-height:1.5}
</style></head><body>
  <h2>Connect Apple Music</h2>
  <button id="go">Authorize Apple Music</button>
  <p>After authorizing, copy the token below into<br><code>~/.config/widgetsuite/musickit-user-token.txt</code> then reload the widget.</p>
  <textarea id="out" readonly placeholder="Music User Token will appear here"></textarea>
<script>
  const DEV = "$DEV";
  document.addEventListener('musickitloaded', async () => {
    try { await MusicKit.configure({ developerToken: DEV, app: { name: 'WidgetSuite', build: '1.0' } }); }
    catch (e) { document.getElementById('out').value = 'Configure error: ' + e; }
  });
  document.getElementById('go').onclick = async () => {
    try { const t = await MusicKit.getInstance().authorize(); document.getElementById('out').value = t; }
    catch (e) { document.getElementById('out').value = 'Authorize error: ' + e; }
  };
</script></body></html>
EOF

chmod 600 "$HTML"

# MusicKit's authorize() opens a popup that hands the Music User Token back to
# its opener via postMessage. From a file:// page the opener origin is "null"
# and Apple rejects the handshake (AUTHORIZATION_ERROR: Unauthorized). Serving
# the page over http://localhost, a browser-trusted secure origin, fixes it.
# The server listens on the loopback interface only, so other devices on the
# network cannot reach it.
if /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop whatever is listening there, or set MUSICKIT_SETUP_PORT."
  rm -rf "$SERVE_DIR"
  exit 1
fi
/usr/bin/python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SERVE_DIR" >/dev/null 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  rm -rf "$SERVE_DIR"
}
trap cleanup EXIT INT TERM HUP
sleep 1

open "http://localhost:$PORT/musickit-auth.html"
echo "Opened http://localhost:$PORT/musickit-auth.html"
echo "Authorize, then paste the token into $CFG/musickit-user-token.txt"
if [ -t 0 ]; then
  echo "Press Return when you are done. The page closes on its own after $((SERVE_SECONDS / 60)) minutes."
  read -r -t "$SERVE_SECONDS" _ || true
else
  sleep "$SERVE_SECONDS"
fi
echo "Stopped the local page."
