---
name: handoff
description: >-
  Judge the context move (continue / compact+handoff / fresh+handoff) and act
  on it; compact and fresh write the handoff to a file. Fire when the user asks
  for /handoff or whether to hand off ("should we /handoff?"): this skill is
  the evaluation, never answer that from memory. Pass their words as args, not
  a route. Also "hand this off", "should we compact / go fresh?", "context is
  getting high". NOT /wrap-up or /done-check.
disable-model-invocation: false
---

Two jobs: **judge** the context move and act on it, then, unless the verdict is continue, **write** the handoff: the delta the next session can't reconstruct from the repo, `CLAUDE.md` and memory.

## Step 1 — Absorb the user's intent

The user usually types `/handoff` in the same prompt where they say what comes next, or the last response already named the next move. That intent is the spine of the handoff; the next session exists to carry it out.

- Carry it in their terms. Strip dictation filler, but don't reinterpret, merge, or reorder what they asked for.
- If any of it is unclear (which of two things goes first, a "the other thing" this thread can't resolve, a step that conflicts with what the thread established), **ask before judging or writing**: one AskUserQuestion round, your recommendation first. A handoff built on a misread intent is worse than none. This is the only pause the skill allows.
- No stated intent and no obvious next move → ask what's next rather than invent one.

## Step 2 — Judge the move

**Skip if the user named the route themselves** ("compact this", `/handoff fresh`). A route word in args the calling model wrote is its guess from before it read this step: judge from scratch.

**Measure, don't estimate.**
- **Context used**: the percentage on your statusline, or `/context`. The `total_tokens` figure in system reminders is the run's budget, not context room.
- **Live work**: each background shell, watcher or subagent this session started that hasn't reported back: what it waits on, its task id, its output file.

**Place the next slice against this thread.** Go by what it touches, not by whether it has its own ticket or PR number; most slices do.
- **Continuation**: the next rung of this thread's own work. Same branch, PR or bug; the rollout or close-out of what was built here; the build of a spec settled here.
- **Sibling**: same feature or epic on its own branch, sharing code, data or domain rules with this thread.
- **Unrelated**: nothing this thread settled applies.

**Route on that:**
- **Continue**: a continuation whose rest is a few turns, or that finishes with the window under about half. If the rest branches (green → close out, red → debug), size it by the long branch. Say so plainly, then **start the work** in the same turn. No file.
- **Compact + handoff**: a continuation too big for that, or a sibling that leans on what this thread settled. Flow: write the handoff → the user runs the `/compact` focus line → they paste the path into the compacted thread.
- **Fresh + handoff**: unrelated work; work that runs alongside this session or needs another repo, machine, model or effort level (a new window, not `/clear`); or a thread that held a wrong model for a stretch (retracted findings, a long dead end) that a summary would re-anchor the next session on.

**What compact keeps.** `/compact` swaps the transcript for a structured summary: every message the user sent, the errors and fixes, files and code touched, pending work. Recently edited files and loaded skills come back with it; raw logs, QA dumps and tool output don't. A compacted window typically lands at a small fraction of where it started, not far above a fresh start. Nothing on disk is lost: the session file keeps every earlier record above the compaction marker. Finished-work residue is no case for fresh, because compact drops it too. The summary keeps what a handoff's cut test throws away (the user's corrections, ruled-out approaches, why calls went the way they did); the handoff keeps what a summary blurs (paths, SHAs, guardrails, their intent word for word).

**Don't route by asking whether the handoff could carry everything.** Its author can't see what it would drop, so the answer is always yes. For related work, lean compact: a needless compact costs a summary's worth of tokens, a needless fresh costs whatever the handoff missed.

**Live work changes the route only when its result lives in this session.** Background shells keep running through `/clear` and through `/compact`; their finish notice lands in whichever session holds the terminal by then. Treat a subagent the same way; that part is unverified.
- Re-checkable from outside (a CI pipeline, a PR, an email, a deploy): any route. The handoff says how to re-check.
- Only in this session (a task output file, a subagent's report): compact, or fresh via `/clear`. The handoff lists the task id, what it waits on and its output path, and says not to start a duplicate. Not a new window: the notice stays with this session.
- Due within minutes and the rest is short: continue, and run this skill again when it lands.

This usually runs at a natural seam with a heavy window, so continue is rare, and compact and fresh should both come up often. A continuation or sibling routed fresh must name the fresh trigger that applied.

## Step 3 — Write the handoff (compact / fresh only)

Save to a durable, git-ignored folder in the **main checkout**, e.g. `<main checkout>/docs/local/<ticket-or-slug>/handoff-<ticket-or-slug>.md` (add `docs/local/` to your global git ignore), overwriting an earlier one. Main checkout = `git worktree list | head -1`: removing a linked worktree deletes its ignored files. Outside a repo, use the session scratchpad. `/tmp` doesn't survive a reboot, so avoid it for anything the next session must find.

The file is only the handoff: the user pastes its path, so nothing from this session's chat reaches the next one. Open with a line that addresses the reader:

```
> **Handoff for the <fresh | post-compaction> session reading this: you are its target, act on it.** Written <YYYY-MM-DD HH:MM>.
```

**Write to the target.** Compact → a *thin pointer*: the summary keeps the story, so carry what summaries drop (exact paths, SHAs, branch/worktree state, hard "do NOT" guardrails, the user's intent word for word). Fresh → the fuller memo; the reader starts cold except for `CLAUDE.md` and memory.

**Building blocks**, not a template; use `##` headers and pick what earns its keep.

- **The user's intent**: what they asked for next, in their words (Step 1). Present whenever they stated any.
- **Where we are**: what just landed, current status. Near-universal.
- **Branches / working dirs**: branches in play, commit/push state, worktree paths. When non-trivial.
- **In flight**: each still-running task (id, what it waits on, output path) and how to re-check it if its notice never arrives.
- **Start here**: numbered first steps. **When the next move maps to a driver skill, name it in step 1**; it tells the next session *how* to proceed, not just *what's* next. Most handoffs are a scoped slice ("here's the work, go execute"), which almost always maps to the project's build/ship driver, so treat *not* naming one as the exception that needs a reason. Resolve the skill from the registry actually available, and match by kind of move; naming the wrong driver is worse than naming none:
  - **build-and-land a feature/fix** → the project's ship-class composite if present (build → local QA → PR); else its build driver (`/work`) plus a note that landing is separate.
  - **diagnose an unknown-cause bug** → `/debug`; **confirm a parked branch is deploy-safe** → the project's readiness gate; **orient / pick what's next, or a blocked decision** → `/recommend`.
  - **anything that doesn't map cleanly** → plain numbered steps, no driver.
- **Scope / ground rules**: conventions and hard constraints, including first-move guardrails ("do NOT fix until the root cause is agreed").
- **Out of scope**: deferred items, bugs handled elsewhere.
- **Open questions** or **Starting hypotheses**: unresolved ambiguities; for debug handoffs, ranked theories to validate first.

**Rules of thumb:**
- **Cut test: would the next session act differently without this line?** If not, cut it. Anything it can re-derive in one step (the ticket description, `git log`, a file) gets a pointer, not a restatement.
- Concrete paths, branches, SHAs. **Mutable state gets a timestamp and a re-check instruction** ("as of 16:39, re-verify"): `git status`, test results, and "HEAD is at X" go stale fastest when another session is live in the same repo.
- **Tag load-bearing claims by provenance**: ✅ a tool result this session shows it · 🧠 recalled (memory, an earlier handoff, a peer session) · 🔗 inferred · ❓ assumed. **Tag the claim the next session will act on, not just the number under it**: a ✅ measurement under a 🔗 conclusion is still 🔗. (Full rules: `/confidence-check`.)
- Typically 25–80 lines; compact pointers shorter.

## Output

In this order, nothing before the verdict:

1. **The verdict line**, naming why the runner-up lost:
   - `→ continue: <reason>`, then go straight into the work.
   - `→ compact + handoff: <reason> (fresh lost: <why>)`
   - `→ fresh + handoff: <reason> (compact lost: <why>)`
2. **Basis**, one line, so the user can check the read: `ctx <N>% · <continuation | sibling | unrelated>: <the slice> · live: <tasks, or none>`.
3. **Intent, as captured**: 1–4 bullets, so the user can check the read without opening the file.
4. Optional sender notes (ticket updated, a non-obvious shaping choice): 1–2 sentences.
5. **The move and the absolute path, last**, each in its own code block:
   - Compact: "run this, then paste the path:", then `/compact Keep: <what the next slice needs from the thread>. Drop: <the finished work's raw output>.` on its own line (plain words, no `@`, no path), then the path.
   - Fresh, replacing this session: "`/clear`, then paste:", then the path.
   - Fresh, alongside this session: "New session, paste:", then the path.

   Make the handoff file's path the only `handoff*.md` path in this reply, so it's unambiguous to copy.

Don't echo the handoff body into chat; the file is the handoff.
