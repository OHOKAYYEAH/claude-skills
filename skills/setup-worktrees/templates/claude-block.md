<!-- TEMPLATE for /setup-worktrees. Append to the project CLAUDE.md, resolve
     every <ADAPT: …>. This block is the automation itself: it is the explicit
     project instruction the harness EnterWorktree tool requires before it will
     fire, and the standing authorization ExitWorktree needs at teardown.
     Delete this comment. -->

## Worktrees — parallel sessions don't share a checkout

**Standing instruction (this line is the explicit CLAUDE.md authorization the
harness worktree tools require): any session about to WRITE to this repo works
in its own worktree** — `/worktree up <name>` (EnterWorktree, off CURRENT
`origin/<ADAPT: default branch>`) at the start of the writing work, not after a
collision. The main checkout is for reading and for the land step. Teardown at
land time is pre-authorized: the session calls ExitWorktree via `/wt-cleanup`
without asking again.

In-place exception, deliberately narrow: <ADAPT: the repo's main-only
carve-outs (standards layers etc.)>, or a minutes-scale single-commit fix when
`git worktree list` shows no other tree and no parallel session — and even
then, commit + push immediately.

- `/worktree` owns the lifecycle (`up · land · gc · list`); `/wt-cleanup` is
  the teardown atom (a `/wrap-up` closeout resolves it by name). Worktrees live in
  `.claude/worktrees/` (gitignored) — harness-made and manual alike.
- **Landing = `git push origin HEAD:<ADAPT: default branch>` from the worktree**
  (rebase onto the fetched origin ref first) — never merge through the shared
  checkout's index. <ADAPT: PR-convention repos: landing = push branch + PR.>
- **Full teardown or stated exception**: worktree gone, local branch gone, any
  pushed branch gone, `git fetch --prune`. A landed unit leaves no refs; never
  end a session with a worktree parked silently.
- Local `<ADAPT: default branch>` rots by design (pushes advance origin only).
  Freshen via `git merge --ff-only origin/<ADAPT: default branch>` only when
  the main checkout is clean, on the branch, and nobody else is mid-work there.
- Rebase conflicts in <ADAPT: append-heavy shared files> are almost always
  append-vs-append: keep both sides, verify nothing dropped.
