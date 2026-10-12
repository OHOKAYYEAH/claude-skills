<!-- TEMPLATE for /setup-worktrees. Copy to .claude/skills/worktree/SKILL.md
     and resolve every <ADAPT: …> marker from the survey. Delete this comment. -->
---
name: worktree
description: Spin up / land / tear down an isolated per-session git worktree —
  the lifecycle + judgment layer for parallel Claude sessions in this repo.
  `up` enters a worktree off CURRENT origin/<ADAPT: default branch> via the
  harness EnterWorktree tool (manual `git worktree add` fallback); `land`
  finishes the unit — rebase onto origin/<ADAPT: default branch>, push
  HEAD:<ADAPT: default branch>, full teardown via /wt-cleanup; `gc` sweeps
  stale worktrees SAFELY (never dirty, unmerged, or live ones); `list`
  reports. CLAUDE.md § Worktrees is the trigger (when to isolate); this skill
  is the mechanics + safety. NOT the Agent tool's isolation:worktree (harness
  scratch trees); NOT /wt-cleanup alone (that's the teardown atom this skill's
  land step chains).
disable-model-invocation: false
argument-hint: [up <name> | land | gc | list]
---

Manage this repo's per-session worktrees. The **mechanism** is the harness
EnterWorktree/ExitWorktree pair (session cwd actually moves; exit-time safety
is built in); this skill is the **judgment + lifecycle** over it: doing the
spin-up correctly, landing without touching the shared checkout, and tearing
down fully so `.claude/worktrees/` never accumulates cruft.

## `up <name>` — spin up

1. `git fetch origin <ADAPT: default branch>` — the base must be CURRENT, not
   a stale local snapshot.
2. **EnterWorktree** with a short kebab-case name for the unit of work. It
   creates `.claude/worktrees/<name>` on a fresh branch off
   `origin/<ADAPT: default branch>` and switches this session into it. Confirm
   the base afterward (`git log --oneline -1` = origin tip) and read the branch
   name back (`git branch --show-current`) — it comes back prefixed,
   `worktree-<name>`.
3. Fallback when the harness tool is unavailable (some subagent contexts):
   `git worktree add .claude/worktrees/<name> -b <name>
   origin/<ADAPT: default branch>` — then address the tree by absolute path in
   every command, or enter it with EnterWorktree `path=`.
4. <ADAPT: symlink steps for gitignored env files the tree needs (absolute
   paths), or delete this step if the repo has none.>
5. Report one line: path, branch, base sha.

## `land` — finish the unit, leave no refs

1. Everything committed in the worktree; account for every path you stage —
   never a blind `git add -A`.
2. `git fetch origin <ADAPT: default branch> && git rebase
   origin/<ADAPT: default branch>`. Conflicts in <ADAPT: the repo's
   append-heavy shared files> are almost always append-vs-append: keep BOTH
   sides, then re-check nothing was dropped.
3. <ADAPT: repo-specific pre-land checks (test suite, standards checker), or
   delete.>
4. `git push origin HEAD:<ADAPT: default branch>`.
   <ADAPT: branch+PR repos instead push the branch and open the PR; teardown
   then waits for the merge. No-remote repos instead
   `git -C <root> merge --ff-only <branch>` — requires a clean main checkout.>
5. Teardown: invoke `/wt-cleanup` (verifies landed, then removes tree +
   branch refs). CLAUDE.md § Worktrees is the standing authorization for the
   exit — don't re-ask.
6. Freshen local <ADAPT: default branch> — **only possible after step 5's
   exit**: while a session is worktree-isolated the harness refuses cross-tree
   `git -C` into the shared checkout. Back in the main
   checkout, and only when it is clean, on the default branch, and no parallel
   session is mid-work there:
   `git merge --ff-only origin/<ADAPT: default branch>`. Otherwise leave it —
   a rotting local ref is by design; landing never goes through the shared
   checkout.

## `list` — status

`git worktree list`, plus liveness per tree — a tree is **live** when some
process has its cwd inside it:

```bash
for c in /proc/[0-9]*/cwd; do readlink "$c"; done 2>/dev/null \
  | grep -F ".claude/worktrees/" | sort | uniq -c
```

## `gc` — safe sweep

For each `.claude/worktrees/*` (fetch first), **keep + report** if any holds:
- **dirty** — `git -C <wt> status --porcelain` non-empty (unsaved work),
- **unmerged** — `git -C <wt> log origin/<ADAPT: default branch>..HEAD`
  non-empty (unlanded work),
- **live** — the cwd probe above hits it (a session is using it).

Remove the rest: `git worktree remove <path>`, then `git branch -d <branch>`
(if `-d` refuses, the branch isn't fully merged — **stop and surface, never
`-D` on a guess**), finish with `git fetch --prune`. Report the keep/remove
split; when in doubt, keep + report.

## Guardrails

- **Never clobber another session's work.** Dirty / unmerged / live trees are
  off-limits to `gc` and to any removal. This rule is what makes the whole
  thing safe to automate.
- **Always tear down what you spun up — worktree AND branch refs.** A landed
  unit leaves nothing behind; anything left standing is a deliberate, *stated*
  choice (parked WIP, a handoff), never silent accumulation.
- **`.claude/worktrees/` only.** One home for harness-made and manual trees,
  one place `gc` sweeps. Off CURRENT origin, never a stale base.
- <ADAPT: single-writer / main-only carve-outs — paths that must never be
  edited from a worktree, and the main-first land-then-rebase path for them.
  Delete if the repo has none.>
- **Stay the judgment layer.** EnterWorktree/ExitWorktree own the mechanics;
  this skill decides when/whether, sequences the land, and reports.
