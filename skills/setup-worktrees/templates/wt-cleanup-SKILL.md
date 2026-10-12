<!-- TEMPLATE for /setup-worktrees. Copy to .claude/skills/wt-cleanup/SKILL.md
     and resolve every <ADAPT: …> marker. The skill NAME is load-bearing:
     /wrap-up resolves a project's teardown atom by the literal name
     `wt-cleanup`. Delete this comment. -->
---
name: wt-cleanup
description: Teardown atom for the current session's worktree — the
  safety-gated remove half of /worktree's lifecycle, named wt-cleanup so
  /wrap-up resolves it as this project's teardown step and runs it LAST in
  closeout. No arg = this session's tree - verifies everything is committed
  AND landed on origin/<ADAPT: default branch>, then removes the tree and
  sweeps its branch refs; HOLD (removes nothing, says exactly why) when
  anything is unlanded. In the main checkout it no-ops gracefully and points
  at /worktree gc. NOT /worktree (lifecycle + judgment — this is only the
  teardown); never --force, never -D.
disable-model-invocation: false
argument-hint: "(no arg = this session's worktree)"
---

Remove the current session's worktree — **only** once it is provably landed.
This is the rug-pull step: it deletes the directory the session is sitting
in, so it always runs last (that is why `/wrap-up` sequences it after
`/compound`).

## 1. Where am I?

`git rev-parse --show-toplevel`. Not under `.claude/worktrees/` → **no-op
gracefully**: report "main checkout, nothing to tear down" and point at
`/worktree gc` for the broader sweep. Done.

## 2. The landed gate (both must pass, or HOLD)

- **Committed:** `git status --porcelain` is empty.
- **Landed:** `git fetch origin <ADAPT: default branch>` then
  `git log origin/<ADAPT: default branch>..HEAD` is empty — every commit is
  reachable from the origin ref.

Either fails → **HOLD**: remove nothing, report exactly what is uncommitted
or unlanded, and hand back. The fix is `/worktree land` (or a deliberate
"park it" call by the user), never a forced removal.

## 3. Remove

- Session entered via EnterWorktree → **ExitWorktree** `action: "remove"`.
  CLAUDE.md § Worktrees is the standing authorization for this call. If the
  tool still refuses citing changes after step 2 passed (its own check can
  trail a just-pushed `HEAD:<ADAPT: default branch>`), step 2's green gate is
  the verification that makes `discard_changes: true` safe — say so when
  using it.
- Tree exists but this session isn't inside it via EnterWorktree →
  `git worktree remove <path>` from outside it.

## 4. Sweep the refs

1. Branch survived the removal? `git branch -d <branch>` — the safe flag; if
   `-d` refuses, it isn't fully merged: **stop and surface, never `-D`.**
2. A remote branch was pushed (rare — landing is HEAD:<ADAPT: default
   branch>)? `git push origin --delete <branch>` — never `backup/*`.
3. `git fetch --prune`.
4. Freshen the local default branch only if the main checkout is clean and on
   it: `git merge --ff-only origin/<ADAPT: default branch>` (the session's cwd
   is back in the main checkout after step 3's exit — and it must be: while
   isolated, the harness refuses cross-tree `git -C` into the shared
   checkout); otherwise say it was skipped.

## 5. Report

One line: `removed <path> · branch refs clean · local <ADAPT: default
branch> <ff'd | left N behind>` — or the HOLD with its reasons.
