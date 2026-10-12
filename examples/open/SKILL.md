---
name: open
description: >-
  Open a new Claude session in its own terminal window and hand it work from this one: a
  handoff memo when the work leans on this thread, a worktree when it would share a checkout,
  the driver skill up front. Fire on "/open X", "run X in parallel", "spin X off into a new
  session". NOT /tangent (forks this conversation for a side thread); NOT /handoff.
  Personal-tooling example (genericized)
disable-model-invocation: true
argument-hint: '[-n name | "name"] [-p prompt | prompt…] [-m model] [-e effort] [-f] [-d dir] [-b N]'
---

> **Read-only example.** Spinning work off into a parallel session is one command that builds the new session's starting context for it (memo, worktree, driver skill) instead of a ritual of open window, start CLI, write prompt, rename. Don't install it — adapt the pattern.

**Explicit request only**: the user typed `/open`, asked to run something in a new session or in
parallel, or sent `/go` on a plan whose lanes read `/open …`. Never a way to offload work that
belongs here.

It replaces: new terminal window → start the CLI with the right model → write a starter prompt →
`/rename`. The new session starts with **no** context from this one beyond what its prompt
carries. The engine is a small local launcher script (not shipped here) that opens a named window
in the terminal multiplexer, starts the CLI in it and types the first prompt. It parses the flags
itself, so quotes and apostrophes never pass through a shell.

## Grammar (canonical in the engine's docstring)

Flags go anywhere — front, back, or one per line. `-n`/`-p` take every word up to the next flag.

| Flag | Meaning | Default |
|---|---|---|
| `-n Name…` · `"Name"` at the very start | session + window name | you pick one, below |
| `-p Prompt…` · any unflagged text | first prompt, fired on boot | none → boots idle |
| `-m opus\|sonnet\|haiku` | which model launcher to start | your default |
| `-e low\|medium\|high\|xhigh\|max` | effort, overriding the launcher's own | the launcher's |
| `-f` | switch to the new window | stay here |
| `-d DIR` | working directory | this session's |
| `-b N` | its own DevTools browser on debug port 9222+N; refused while a browser or live session holds it | shares this session's |
| `--` | the rest is prompt, verbatim — no flag parsing | |

`-m`/`-e`/`-d`/`-b` count only when a valid model/effort/existing dir/slot number follows, so
"explain -m in grep" stays prompt. `-f`, `-n`, `-p` always count: a prompt that mentions them goes
after `--` or in "double quotes". Single quotes are just apostrophes.

## 1. Find the work

- **Arguments** → one launch for the work they name. Several clearly separate slices → one each.
- **None, right after a plan** whose lanes read `/open …` → each lane. None and no plan → boot
  one idle session.

## 2. Build the prompt

The user's words stay verbatim; you only **add** to them, and only what the new session needs.

- **Leans on this thread?** It does when the new session needs what this one settled
  (decisions, findings, a plan, the "why"), not merely when it shares a ticket. Then write a
  fresh handoff memo by `/handoff`'s rules, but name the file after the launch
  (`handoff-<name-slug>.md`), never this session's slug: two launches, or this session's own
  later `/handoff`, would overwrite it. Append its absolute path to the prompt. Work that stands
  alone gets no memo, and neither does a prompt that is already a handoff path.
- **Driver skill first** when the prompt names none and the work maps to one, resolved from the
  skills available: build-and-land → the project's ship-class driver (e.g. the `/ship` example,
  where the project has one, else `/work`); gather the record → a record-sweep research skill, if
  the project has one; unknown-cause bug → `/debug`.
- **Worktree first** when the session will edit files in a git checkout this session or another
  launch also edits: lead with the project's worktree tooling, else "make a git worktree off the
  integration branch first". Two sessions in one checkout clobber each other's branch switches
  and uncommitted edits. Read-only work skips it. A session that will drive a browser gets its own
  with `-b N` (DevTools on port 9222+N; without it, it shares this one's). Pick an N no live
  session holds, and stop that browser when the work closes.
  On a memo route, the driver and worktree lines go in the memo's first step instead.
- **This thread's own next step** isn't a launch: it would race this session on the same work.
  Say so once; launch anyway only if the user insists. **A choice the user named wins** ("no
  memo", "fresh"), with any disagreement noted in the hand-back line.
- **Name** (used only when the arguments carry none): 2–4 words naming the work, ticket key first
  (`PROJ-123 date picker`). No prompt: the launcher name.

## 3. Launch

One engine call per launch. When you added nothing, pass the raw arguments unaltered, through a
quoted heredoc so the shell never touches them. When you added to the prompt, put the user's flags
first, then `--`, then the full prompt, so its words are never read as flags. Another repo → add
`-d <repo root>`.

Non-zero exit (bad flag, no multiplexer session) → relay the message; don't hand-roll a launch.
The engine's comments hold the traps (launchers defined as shell functions, targeting the right
multiplexer session).

## 4. Hand back

One line per launch: the engine's line (window, name, model@effort, prompt sent/idle, boot
status), plus `memo` and its path when you wrote one. **The prompt is the new session's work,
never yours: don't act on it here**, not even a one-word answer. Then carry on with this
session's work, or return to the caller (`/go` on a plan) so it can run the plan's here-steps.
