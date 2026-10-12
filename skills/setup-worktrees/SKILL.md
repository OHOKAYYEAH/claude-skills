---
name: setup-worktrees
description: "Install a per-session git-worktree convention into the current project: parallel Claude sessions each work in their own worktree under .claude/worktrees/ (via the harness's EnterWorktree/ExitWorktree), land by rebase + push to the default branch, and tear down fully. Writes a CLAUDE.md block (so sessions isolate without being asked), two project skills from templates/ (/worktree for lifecycle, /wt-cleanup for teardown, named so /wrap-up finds it) and a .gitignore entry. For repos whose parallel hazard is git itself, i.e. most small repos without running services. Fire ONLY on an explicit request (\"set up worktrees here\"), never proactively: it writes a convention. REFUSES repos whose CLAUDE.md already declares worktree machinery. NOT the daily /worktree (this installs it), NOT /setup-ticketing, NOT the Agent tool's isolation:worktree."
disable-model-invocation: false
argument-hint: "(run inside the target repo)"
---

**Run only on an explicit ask** ("set up worktrees here", `/setup-worktrees`) — never proactively. It writes a convention, so a spurious run has teeth.

Install the worktree convention into the repo in scope, then get out of the way.
The convention is the deliverable; this skill should never be needed twice in
the same repo.

**Why this shape** (context for judgment calls, not dogma): per-session
isolation's real product is that the **main checkout stops being shared mutable
state** — no more two sessions racing one index, no more `git add -A` sweeping
a parallel session's (or your own) edits into a commit that asserts the opposite.
The harness **EnterWorktree** tool is the mechanism because (a) it actually
moves the session's cwd — a bare `git worktree add` leaves every later relative
path still pointing at the shared tree, the classic half-isolation; (b) it
branches off CURRENT `origin/<default>` by default (`worktree.baseRef: fresh`);
and (c) its own contract honors a CLAUDE.md standing instruction — which is
what makes isolation *automatic* instead of ask-every-time. Heavier
machinery (per-worktree ports and env wiring) is what
this grows into when a repo has running services; that
wiring is per-project and deliberately NOT installable generically.

## 0. Guard

- Explicit request only (see description).
- Read the repo's CLAUDE.md first. If it already declares worktree machinery —
  worktree/port scripts, a previous install of this convention — **surface
  that and stop.** One repo, one convention; migrating is a different
  conversation.
- Not a git repo → stop; there is nothing to isolate.
- `.claude/worktrees/` already gitignored but no CLAUDE.md block (or vice
  versa) is a half-install: say so and finish it, don't re-init.

## 1. Survey — the adaptation inputs (collect, don't guess)

- **Default branch + remote.** `git symbolic-ref --short HEAD` on a fresh
  clone lies less than assuming `main`; check `git remote -v`. **No remote** →
  the land step's `push HEAD:<default>` has nowhere to go: install anyway, but
  adapt land to `git -C <root> merge --ff-only <branch>` (needs a clean main
  checkout) and flag it in the report.
- **Collision-prone shared files** — indexes, ledgers, registries, anything
  every session appends to. Name them in the CLAUDE.md block so rebase
  conflicts there are *expected* and handled keep-both-sides.
- **Single-writer / main-only paths** — standards layers, generated files with
  a version-uniqueness invariant. Carve them out as never-edited-in-a-worktree.
- **Commit convention.** Straight-to-default repos land by `push HEAD:<default>`;
  branch+PR repos land by pushing the branch + opening the PR, teardown after
  merge — adapt the land section accordingly.
- **Service surface** — dev servers, ports, env files, node_modules. Gitignored
  env files a worktree needs become symlink steps in `up` (absolute paths).
  Port wiring is OUT of scope: flag it in the report as per-project work to
  grow into (per-worktree ports and env wiring).

## 2. Install

1. `.gitignore`: add `.claude/worktrees/` — harness-managed and manual trees
   share this one home, so `gc` has one place to sweep.
2. `templates/worktree-SKILL.md` → `.claude/skills/worktree/SKILL.md`,
   adapting every `<ADAPT: …>` marker from the survey.
3. `templates/wt-cleanup-SKILL.md` → `.claude/skills/wt-cleanup/SKILL.md`.
   The name is load-bearing: `/wrap-up` (if installed) resolves its project
   teardown atom by the literal name `wt-cleanup`, so closeout gets worktree
   teardown for free.
4. `templates/claude-block.md` → append to the project CLAUDE.md, adapted.
   **The block IS the automation**: it is the explicit project instruction
   EnterWorktree's contract requires, and the standing authorization
   ExitWorktree needs at land time. Without it the tools sit unused and
   nothing changed.

## 3. Land it

Follow the project's commit convention (a small solo repo often commits+pushes
directly — but stage only your own paths; a parallel session or the user may
have the tree dirty).

## 4. Report

One line: what was installed, the land variant chosen (push vs ff-merge vs
PR), the carve-outs named, and the first real use — "the next writing task in
this repo starts with `/worktree up <name>`."
