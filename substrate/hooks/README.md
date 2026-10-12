# Hooks

Skills that need a `settings.json` hook to work as intended. Copy the script somewhere on your machine, make it executable, and register it.

## `done-rename.sh` — powers `/done` and `/wait`

Both commands act instantly: a `UserPromptSubmit` hook intercepts the prompt, retitles the session, and blocks the turn — no LLM round-trip. The `/done` and `/wait` skill bodies are only the fallback for when this hook isn't installed.

| Prompt | New title | Meaning |
|---|---|---|
| `/done`, `/done <anything>` | `[DONE] X` | Finished, archived |
| `/wait`, `/wait <anything>` | `[WAIT] X` | In progress, blocked on a non-code answer from outside (a decision, approval, or info from someone else) |

Any existing `[DONE]` / `[WAIT]` prefix is stripped before the new tag is applied, so states transition cleanly (`[WAIT] X` + `/done` → `[DONE] X`). Other bracketed prefixes you add yourself (e.g. `[URGENT]`) are left alone. Every other prompt passes through untouched; the hook never blocks or errors on a normal prompt.

**Install:**

```bash
chmod +x done-rename.sh
# move it wherever you keep hooks, e.g. ~/.claude/hooks/done-rename.sh
```

Then add to your `settings.json`:

```jsonc
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/done-rename.sh" }
        ]
      }
    ]
  }
}
```

`UserPromptSubmit` hooks run on every prompt; the script itself decides whether the prompt is `/done` or `/wait`.

Requires `jq` on the PATH. The script honors `$CLAUDE_CONFIG_DIR` (falls back to `~/.claude`), so it works with a non-default config dir without edits.

**Live title badge:** the CLI doesn't repaint its session-name badge when a hook blocks the turn, so after `/done` or `/wait` the new title is saved but the badge updates on the next `/resume`. Run `/rename` yourself if you want it immediately.

**Optional tmux integration (off by default):** if you run Claude Code inside tmux and name each window after its session, set `SESSION_TAG_TMUX=1` in the environment Claude Code starts from. The hook then renames the current tmux window to the session title (on `/done`, `/wait`, and as a re-sync on every other prompt), and repaints the live badge by typing a native `/rename <title>` into the pane right after the block. Without tmux, or without the variable, all of that is skipped.
