#!/usr/bin/env bash
# Interactive setup for Recent Album Covers. Invoked by install.sh.
# Sources, first with data wins: Spotify → Apple Music (MusicKit) → local
# library. The local library path uses AppleScript and needs Automation
# permission for Übersicht.
set -euo pipefail
CFG="${CFG:-$HOME/.config/widgetsuite}"

echo "Recent Album Covers can pull from Spotify, Apple Music, or your local library."
echo
echo "The local-library option uses AppleScript and needs Automation permission:"
echo "  System Settings → Privacy & Security → Automation → Übersicht → enable Music."
printf "Open Automation settings now? [Y/n] "; read -r a
case "$a" in
  n|N) ;;
  *) open "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation" 2>/dev/null || true ;;
esac

echo
if [ -f "$CFG/spotify-setup.py" ]; then
  printf "Set up Spotify (recently played) now? [y/N] "; read -r s
  case "$s" in y|Y) /usr/bin/python3 "$CFG/spotify-setup.py" || true ;; esac
fi
if [ -f "$CFG/musickit-setup.sh" ]; then
  printf "Set up Apple Music (MusicKit) now? [y/N] "; read -r m
  case "$m" in y|Y) bash "$CFG/musickit-setup.sh" || true ;; esac
fi
