#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# done-rename.sh — UserPromptSubmit hook (powers /done and /wait)
# ─────────────────────────────────────────────────────────────────────
# Session lifecycle tags — a prefix on the session's custom title:
#   (none)     → active / in progress
#   [DONE] X   → finished, archived
#   [WAIT] X   → in progress, blocked on a NON-CODE answer from outside
#                (a decision, approval, or info awaited from someone else);
#                not for code/CI/deploy blockers
#
# TAG COMMANDS: intercept and BLOCK the turn (instant, no LLM turn):
#   /done, /done <anything> → [DONE]   (closeout; /compound stays separate)
#   /wait, /wait <anything> → [WAIT]   (park while waiting on outside input)
#   Any existing [DONE]/[WAIT] prefix is stripped first, so
#     "[WAIT] Fix login redirect" + /done  →  "[DONE] Fix login redirect"
#
# ANY OTHER PROMPT: pass-through, never blocks, never errors.
#
# OPTIONAL tmux mirroring (off by default). Set SESSION_TAG_TMUX=1 in the
# environment Claude Code runs in to also:
#   - rename the tmux window holding this session to the session title, and
#     re-mirror the latest title on every prompt;
#   - repaint the CLI's live name badge after /done or /wait by typing a
#     native `/rename <title>` into this pane (the CLI ignores a blocking
#     hook's sessionTitle, so this is the only way to update it live).
# Without it the new title still lands; the badge catches up on /resume.
# ─────────────────────────────────────────────────────────────────────

set -e

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // ""')
TRIMMED=$(echo "$PROMPT" | awk '{$1=$1; print}')
SID=$(echo "$INPUT" | jq -r '.session_id // ""')
LIVE_TITLE=$(echo "$INPUT" | jq -r '.session_title // ""')   # what the badge shows now, if the CLI sends it

TMUX_ON=0
if [ "${SESSION_TAG_TMUX:-0}" = 1 ] && [ -n "${TMUX_PANE:-}" ] && command -v tmux >/dev/null 2>&1; then
  TMUX_ON=1
fi

# --- helpers ---------------------------------------------------------

# Latest custom title in the session jsonl (native /rename and this hook
# both write the same {"type":"custom-title",...} line). "" if none.
latest_title() {
  tac "$1" 2>/dev/null | grep -m1 '"type":"custom-title"' \
    | jq -r '.customTitle // ""' 2>/dev/null || true
}

# Strip leading lifecycle prefixes (repeatably). Only touches these tags;
# a user title like "[URGENT] X" is left intact.
strip_prefixes() {
  local t="$1" changed=1 p
  while [ "$changed" = 1 ]; do
    changed=0
    for p in "[DONE] " "[WAIT] "; do
      case "$t" in
        "$p"*) t="${t#"$p"}"; changed=1 ;;
      esac
    done
  done
  printf '%s' "$t"
}

# Rename the tmux window holding this session's pane. No-op unless opted in.
mirror_tmux() {
  local desired="$1" current
  [ "$TMUX_ON" = 1 ] && [ -n "$desired" ] || return 0
  current=$(tmux display-message -p -t "$TMUX_PANE" '#W' 2>/dev/null || true)
  if [ "$current" != "$desired" ]; then
    tmux rename-window -t "$TMUX_PANE" -- "$desired" 2>/dev/null || true
  fi
  return 0
}

# Type a native `/rename $1` into this pane once the block has rendered.
# Skipped in copy-mode, where the keys would land as copy-mode commands.
live_rename() {
  [ "$TMUX_ON" = 1 ] && [ -n "$1" ] || return 0
  [ "$(tmux display -p -t "$TMUX_PANE" '#{pane_in_mode}' 2>/dev/null)" = 0 ] || return 0
  setsid -f bash -c 'sleep 0.4; tmux send-keys -t "$1" -l -- "/rename $2";
    sleep 0.3; tmux send-keys -t "$1" Enter' _ "$TMUX_PANE" "$1" \
    >/dev/null 2>&1 </dev/null || true
}

# Emit the block JSON that ends the turn instantly. $1 = reason shown.
block_turn() {
  jq -cn --arg r "$1" '{decision:"block", reason:$r}'
}

# --- classify the prompt ---------------------------------------------

TAG=""
case "$TRIMMED" in
  "/done"|"/done "*) TAG="[DONE]" ;;   # glob: "/done fast" or a trailing note still tags
  "/wait"|"/wait "*) TAG="[WAIT]" ;;   # glob: "/wait on a reviewer's decision" must not fall through to the LLM
esac

# Resolve the session jsonl (best-effort).
JSONL=""
if [ -n "$SID" ]; then
  JSONL=$(ls "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/"*/"$SID.jsonl" 2>/dev/null | head -1 || true)
  [ -f "$JSONL" ] || JSONL=""
fi

# --- tag command: rewrite title, optionally mirror, BLOCK -----------

if [ -n "$TAG" ]; then
  if [ -z "$JSONL" ]; then
    block_turn "session hook: jsonl not found for ${SID:-<none>}"
    exit 0
  fi

  CUR=$(latest_title "$JSONL")
  BASE=$(strip_prefixes "$CUR")
  NEW_TITLE="$TAG${BASE:+ }$BASE"   # "[DONE]" if unnamed, else "[DONE] <base>"

  if [ "$CUR" != "$NEW_TITLE" ]; then
    jq -cn --arg t "$NEW_TITLE" --arg s "$SID" \
      '{type:"custom-title", customTitle:$t, sessionId:$s}' >> "$JSONL"
  fi

  mirror_tmux "$NEW_TITLE"

  case "$TAG" in
    "[DONE]") MSG="Session closed out → ${NEW_TITLE}. (Run /compound separately to codify any lessons.)" ;;
    "[WAIT]") MSG="Session parked, waiting on external input → ${NEW_TITLE}." ;;
  esac
  [ "$LIVE_TITLE" = "$NEW_TITLE" ] || live_rename "$NEW_TITLE"
  block_turn "$MSG"
  exit 0
fi

# --- pass-through: optional tmux re-mirror, never block -------------

if [ "$TMUX_ON" = 1 ] && [ -n "$JSONL" ]; then
  T=$(latest_title "$JSONL")
  [ -z "$T" ] || mirror_tmux "$T" || true
fi
exit 0
