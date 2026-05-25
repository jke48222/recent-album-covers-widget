# recent-album-covers — Troubleshooting

### The widget doesn't appear
- Make sure Übersicht is running, then use its menu-bar icon → **Refresh all**.
- Confirm `recent-album-covers.widget` is in
  `~/Library/Application Support/Übersicht/widgets/`.
- Re-run `./install.sh`.

### Images or assets don't load
- Keep the `recent-album-covers.widget` **folder intact**. Übersicht serves bundled assets
  relative to the widgets root, so files must stay inside the folder.
- If you edited `index.jsx`, check the Übersicht console for errors
  (menu-bar icon → Debug / Show console).

### It's blank / shows a permission notice
- This widget controls Music/Spotify via AppleScript. Grant access in
  System Settings → Privacy & Security → Automation → Übersicht.
- Run `./check.sh` to confirm the permission and helper status.
- For the local library: make sure the Music app is running and has tracks.
