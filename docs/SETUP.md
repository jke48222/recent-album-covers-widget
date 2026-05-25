# recent-album-covers — Setup

> A 3x3 mosaic of your most-played album covers.

## Install (one click)

1. Install [Übersicht](https://tracesof.net/uebersicht/) and run it once.
2. Double-click `install.command` (or run `./install.sh` in Terminal).
   It copies `recent-album-covers.widget` into your Übersicht widgets folder, installs any
   helpers, and walks you through any configuration.

The installer is safe to re-run; it just refreshes the install in place.
To install by hand instead, unzip `recent-album-covers.widget.zip` into
`~/Library/Application Support/Übersicht/widgets/`.

## Configuration

Covers come from the first available source: **Spotify → Apple Music → your
local library**.

- **Spotify** (recently played): `install.sh` can run `spotify-setup.py`.
- **Apple Music** (MusicKit): `install.sh` can run `musickit-setup.sh`.
- **Local library**: uses AppleScript and needs **Automation permission**:
  > System Settings → Privacy & Security → Automation → Übersicht → enable Music.

Resolved covers are cached in `~/Library/Caches/ws-albumart`, so refreshes are
fast and only re-fetch when your top albums change. If the local path is blocked
by permission, the widget shows a tap-to-fix notice.

## Fonts

For the intended look, install **Instrument Serif**, **Geist**, and
**Geist Mono**. System fonts are used as a fallback otherwise.
