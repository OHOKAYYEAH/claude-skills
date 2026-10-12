---
name: tangent
description: "Chase a side thread without blocking this one: fork the CURRENT session into its own tmux window with this conversation's full context and launch flags, for a side question or side investigation while this session keeps going. Text after the command is the fork's first prompt; none boots it idle. Fire on \"/tangent\", \"branch this off\", \"fork this\", \"spin this tangent off\". Explicit request only. NOT for starting a fresh session on a separate unit of work (no shared context needed), and NOT for handing work to a fresh session with a written summary (that's a handoff)."
disable-model-invocation: false
argument-hint: '[-n name | "name"] [-p prompt | prompt…] [-m model] [-e effort] [-f]'
allowed-tools: Bash(tmux *) Bash(tr *) Bash(grep *) Bash(sed *) Bash(cat *) Bash(ls *) Bash(ps *) Bash(mktemp *)
---

**Explicit request only** — never proactively, never to offload work that belongs here.

The user wants a tangent chased in parallel without losing this thread. `--resume <id>
--fork-session` replays this transcript under a **new** session id, leaving this one running
and untouched. Land it in its own tmux window with the right flags and name, then **carry on
with whatever this session was doing** — a side effect, not a hand-off: no summary, no wind-down.

**Requires:** tmux (this session running inside it) and a `claude` CLI with `--fork-session`.

## Arguments

Flags go anywhere; unflagged text is the prompt.

| Flag | Meaning |
|---|---|
| `-n NAME…` or a leading `"NAME"` | the fork's window + session name |
| `-p PROMPT…` or plain text | the fork's first prompt — `/tangent why does the cache miss here?` |
| `-m MODEL`, `-e EFFORT` | override the inherited model / effort |
| `-f` | focus the new window (default: it opens in the background) |

- **No prompt** → the fork boots idle.
- **A prompt** → the fork fires it as its first turn. A prompt that starts with `/` runs that
  slash command in the fork.
- **Model/effort** default to this session's *launch* flags (a later `/model` or `/effort`
  change here isn't inherited — pass `-m`/`-e`).

## Procedure

**1. Collect the facts — all from env/proc, don't ask.**

```
SID="$CLAUDE_CODE_SESSION_ID"                        # this session
ARGV=$(tr '\0' '\n' < /proc/$CLAUDE_PID/cmdline)     # exact launch flags (Linux)
# macOS / no /proc:  ARGV=$(ps -o args= -p "$CLAUDE_PID")  — loses argument quoting
JSONL=$(ls -t "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/projects/*/"$SID.jsonl" | head -1)
TITLE=$(grep -aoE '"customTitle":"[^"]*"' "$JSONL" | tail -1 |
        sed 's/.*"customTitle":"//; s/"$//')
CWD=$(grep -aoE '"cwd":"[^"]*"' "$JSONL" | tail -1 | sed 's/.*"cwd":"//; s/"$//')
```

**2. Rebuild the launch line from the real argv — never from a guess.** Replay it literally:
`claude <flags…>`, dropping any old `--resume` / `--continue` / `--name` / `--fork-session` and
the parent's own positional first prompt, so nothing collides with what's added below. Apply
`-m`/`-e` overrides. If the user launches through their own shell function or alias (e.g.
`opus` = `claude --model opus --effort high`) and the argv matches it exactly, use that name
instead, because that's what they'd have typed.

**3. Name it.** The `-n` name if given. Else, with a prompt: 2–4 words naming the fork's work.
Else `<TITLE> (fork)`, with any leading lifecycle tag like `[DONE]`/`[WAIT]` stripped off TITLE —
the fork is live work whatever the parent's state. Empty TITLE (never named) → fall back to the
tmux window name read through **this pane** (`tmux display-message -p -t "$TMUX_PANE"
'#{window_name}'`); if that's `bash`/`sh` too, name it `(fork)` and tell them to `/rename` it.

**4. Scope line** — only with a prompt while this thread is mid-plan: the fork replays the whole
transcript, so after answering it may carry on with the parent's plan. Append a last line
`(Side thread: do only the above; the parent session owns the plan.)`. Append, never prepend: a
prompt that starts with `/` must stay first to fire.

**5. Spawn detached in this pane's tmux session, then type the line into it.**

```
SESS=$(tmux display-message -p -t "$TMUX_PANE" '#{session_name}')
W=$(tmux new-window -d -P -F '#{window_id}' -t "$SESS:" -n "<name>" -c "$CWD")
tmux send-keys -t "$W" -l '[CLAUDE_CONFIG_DIR="<this dir>"] <launch line> \
  --resume "<SID>" --fork-session --name "<name>" [-- "$(cat <promptfile>; rm -f <promptfile>)"]'
tmux send-keys -t "$W" Enter
```

Both bracketed parts are conditional: the `CLAUDE_CONFIG_DIR` prefix **only when it is set in
this session** (see Traps); the prompt tail only when there is a prompt. Write the prompt to a
`mktemp` file with a quoted heredoc first — a file, not argv, so quotes and apostrophes in it
never meet shell quoting. With `-f`, `tmux select-window -t "$W"` afterwards.

Wait for the new shell's prompt before `send-keys`, then `capture-pane` ~10s after launch and
confirm the fork shows the prompt with the right model — not a first-run theme picker.

**6. Report in one line** — window, name, launch line, idle or prompt preview. Then continue the
parent thread. **The prompt is the fork's work, not yours — never act on it here.** If the name
ended up `(fork)`, say it needs a `/rename` there.

## Traps

- **`tmux new-window "<cmd>"` runs the command under `/bin/sh`, which has none of the user's
  shell functions or aliases** — so a launcher function isn't found, or the fork silently
  degrades to a bare `claude` at default model/effort. Spawning a plain interactive shell and
  *typing* the line is what makes the function resolve; it also leaves a live shell behind when
  the fork exits.
- **Pin `CLAUDE_CONFIG_DIR` only if this session has it set.** A new window inherits the tmux
  *server* env, not this pane's, so on a machine with more than one config dir, prefixing the
  current one keeps the fork on its parent's account. **When it's unset, setting it to
  `~/.claude` is NOT equivalent:** unset reads global state from `~/.claude.json`, set reads
  `$CLAUDE_CONFIG_DIR/.claude.json` — a different file, and the fork boots into first-run
  onboarding.
- **Start the fork in the transcript's cwd, not the process cwd.** After entering a worktree
  mid-session the two differ, and `--resume` from the wrong directory can't find the session.
- **Target this pane's tmux session and window** (`-t "$TMUX_PANE"`). Without `-t`, tmux
  answers for whichever session/window is *active*, so the fork lands — or the fallback name
  comes from — wherever the user happens to be looking.
- **The fork's history ends on this `/tangent` call, shown as interrupted** — it replays the
  transcript as flushed to disk. Harmless; it's why the prompt reads as a fresh turn. Fork at a
  natural boundary, not mid-tool-call.
- **`--name` sticks on a resume** — the fork's badge shows the new name. If a CLI version
  regresses that, the tmux window name is still right; `/rename` fixes the badge.

## Degradation

No tmux (`$TMUX` unset): don't improvise a half-fork. Say tmux is missing and hand the user the
ready-to-paste command (`cd <abs path>` plus the launch line with `--resume <SID>
--fork-session --name '<name>'`), one flag per line — they run it in a terminal of their own.
