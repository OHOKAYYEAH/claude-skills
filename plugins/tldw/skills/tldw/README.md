# tldw — setup notes

For whoever installs this skill; nothing here is needed at run time.

- **Install:** this folder is a plugin marketplace. Add it from GitHub or a local copy, then install and enable the plugin:

  ```bash
  claude plugin marketplace add OHOKAYYEAH/claude-skills   # or: /path/to/claude-skills
  claude plugin install tldw@ohokayyeah
  claude plugin enable tldw@ohokayyeah
  ```

  Or copy this `tldw/` folder into `~/.claude/skills/` and register the hook yourself (below).
- **Requirements:** Claude Code on your own machine (CLI or the desktop app's Code tab) and `python3`. The first run installs `youtube-transcript-api` (pinned) into `~/.cache/tldw/venv` (or `$TLDW_VENV`). Optional: `yt-dlp` on PATH adds a fallback when YouTube blocks the primary fetch.
- **Output:** digests save under `~/tldw` (or `$TLDW_DIR`), one folder per video.
- **Defaults:** `scripts/config.py set shape argument` / `set ratio 15` writes `~/.config/tldw/config.json` (or `$TLDW_CONFIG`); `$TLDW_SHAPE` / `$TLDW_RATIO` override it. Asking Claude ("make argument my default") does the same.
- **Paste-a-link shortcut:** `scripts/paste_hook.py` is a `UserPromptSubmit` hook. A prompt that is only YouTube links, plus words like "summarize this" or a shape/ratio, runs `/tldw` without typing it; every other prompt passes through untouched. Installed as the `tldw` plugin, the hook comes with it. Installing the skill on its own, register it in `settings.json`:

  ```json
  { "hooks": { "UserPromptSubmit": [ { "hooks": [
    { "type": "command", "command": "python3 /path/to/tldw/scripts/paste_hook.py" }
  ] } ] } }
  ```
