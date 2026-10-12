---
name: done-check
description: >-
  Glanceable verdict on "are we done, safe to close out?" (done /
  done-grab-N-first / not yet) plus ONLY loss-bearing loose ends: unfiled
  follow-ups, untold requesters, unpushed work, stale worktrees, uncaptured
  memory, dangling prod processes, each tagged [P] (closeout can clear it) or
  [M] (needs you). Fire on "are we done / safe to close / clear to wrap up?".
  NOT /wrap-up (acts on them), /handoff, /recommend, or /report.
disable-model-invocation: false
argument-hint: "[optional focus or scope] [token: \"nested\" — a composite owns the terminus]"
---

The user is context-switching and wants ONE thing at a glance: **are we done with this session's main work, and is it safe to close out?** This skill IS that answer — run it, don't answer from the hip. Lead with a plain yes/no verdict, then surface only the things that would actually be *lost* if they close now.

## The one question that is the headline

> **Is the session's MAIN work done?** — the headline objective the user set out to do (the opening ask, the ticket, the plan), achieved and verified to the bar that work asked for (shipped / merged / pushed / tested as applicable).

The verdict answers *that*, first and unmistakably. Everything else is secondary detail.

## The distinction that makes this skill work

Three different things get tangled at the end of a session. Keep them apart:

| Thing | What it is | Effect on verdict |
|---|---|---|
| **Main-work doneness** | the headline objective complete or not | **IS the verdict** |
| **Loss-bearing loose ends** | things that *evaporate or get stranded* if the user closes now (see buckets) | surfaced as "grab these first" — still a *yes* |
| **Optional follow-ons** | "next effort options" / "could also" / forward suggestions, esp. from `/work` `/report` `/super-review` report tails | **IGNORED — never downgrade the verdict, never listed as a loose end** |

### Obligation vs. option — the test for the middle column

> Did the session **decide this must happen** (an obligation: a ticket it resolved to file, a commit to push, a memory to capture) — or is it a **menu of what could come next** (an option)?

Only obligations that would **evaporate** get surfaced. "We should file a ticket for the reporting gap" that was *decided* and never filed → obligation, surface it. "Next you could tackle the mobile polish / migrate to URL state / harden X" → option, ignore it. **When unsure, it's an option — say nothing.**

This test carries the skill because composite skills almost always end with a *Next effort options* menu — forward could-dos, fully recoverable, never an obligation the session committed to. Reading that menu as loose ends is exactly what makes every verdict come back "yeah, but there's follow-ons."

## Tag every surfaced item `[P]` or `[M]`

Each loose end you surface carries one tag. `/wrap-up` consumes these directly — an untagged list forces it to re-derive the same judgment — and the tags are also what tell the user at a glance whether they can actually walk away.

- **`[P]` closeout clears it** (P = the closeout pipeline) — any reversible action on this session's own work: *uncaptured memory* (`/compound`), *this session's worktree when clean + pushed* (a worktree teardown), *committing this session's finished changes and pushing them to a branch already on the remote (or to the default, where that repo commits direct to it)*, *switching a checkout parked on a merged branch*, *moving an out-of-place file into the repo's git-ignored private folder*, *a ticket transition the work already earned*, *stopping a process this session started*. `/wrap-up` does these without asking and lists them after.
- **`[M]` needs the user** — outward-facing, destructive, or a call only they can make: *a triage ASK*, *an untold requester (bucket 6)*, *a push to a default/integration/env branch of a PR-flow repo*, *a never-pushed branch (a ship flow)*, *an untracked file with no obvious home*, *a standing instruction to a peer session*, *anything this session didn't start*.

**When unsure whether it's reversible, it's `[M]`. Reversible but unsure it's wanted → `[P]`** — it's listed in the report and undoable, and a pause costs more than an undo.

## Scan these loss-bearing buckets (fast)

1. **Follow-ups and decided obligations** `[M]` — *the highest-value bucket.* Something the session *resolved* to track — "should file a ticket," a proposed ticket agreed but never created, a verbal TODO it committed to — plus the findings it turned up in flight. These vanish with the transcript.

   **Hand every candidate to `/triage`, even a single one, and do it before the git sweep.** It owns the bar for what earns a row (dedupe, fold, merge, file, log, ask, drop) and its one-row budget, so don't re-judge here. It acts on its own dispositions by design — the one exception to "surface, don't fix" — and running it first means a fix it folds shows up as uncommitted work in bucket 2. Surface only its **ASK** lines, as `[M]`. If `/triage` isn't installed, surface each candidate as an `[M]` item instead and let the user decide. A nit noticed in passing is not a candidate, and this skill never invents one.
2. **Git, per touched repo** `[P]` unless a line says otherwise — some workspaces nest several *independent* repos in one directory, so check every repo with state, not just the one you're sitting in (the sweep below discovers them):
   - Uncommitted tracked changes mid-flight → often a `not yet`.
   - Local commits on no remote branch (`git log HEAD --not --remotes`) → "N commits on `branch` not pushed." Reliable without a fetch — but don't claim "behind" / "drift": that needs a `git fetch` and isn't this skill's job. **Not `@{u}..`** — a merged branch with the default pulled into it reads "ahead 17" of its own upstream while every commit is already on the default.
   - Checkout parked on an already-merged branch (`git merge-base --is-ancestor HEAD origin/<default>`, branch ≠ default) → `[P]` "switch to `<default>`." That parking is what makes the false "ahead N" above.
   - Evidence or private files outside their home (a PNG/PDF at the repo root, a paste-me draft in `docs/`), **staged or untracked** → `[P]` "move to the git-ignored private folder" (e.g. `docs/local/`, if the repo uses one; else `[M]`, ask where). Staged ones first: the next `git commit` sweeps possible customer data in.
   - Stale / finished worktrees (`git worktree list`) whose work is done or whose branch already merged → `[P]` if this session's tree and it's clean + pushed; `[M]` otherwise.
   - Untracked files: **noise-filter hard.** Flag only files that look like work product (source / scripts / docs). Ignore data and exports (`.xlsx` / `.csv`); screenshots and PDFs are the out-of-home bullet above. Summarize a count; never enumerate junk.
     - **The precise loss test is `untracked` AND `absent from origin`** — not untracked alone. A file can be untracked locally yet already committed upstream (harmless — a `git pull` restores it tracked), while a file that is untracked *and* missing upstream exists in exactly one place on earth. Cheap check: `D=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main); git status --porcelain | grep '^??' | sed 's/^?? //' | while read -r f; do git cat-file -e "$D:$f" 2>/dev/null || echo "LOSS-BEARING: $f"; done`.
     - **Inverse of the same test: untracked-but-identical-to-upstream is a landmine to CLEAR, not preserve.** After landing new files via a copy-into-a-worktree flow, the main tree keeps byte-identical untracked copies that make the next `git pull` refuse ("untracked working tree files would be overwritten by merge"). Verify with `git hash-object <f>` vs `git rev-parse "$D:<f>"`, then `rm` — provably lossless.
3. **Uncaptured durable knowledge** `[P]` — did this session learn something project-level not yet in memory (a root-caused bug, a non-obvious access path, a decision)? If yes → "capture to memory before close," tagged `[P]` because `/compound` is what captures it. If memory's already updated, that's a *closure* signal — say so, don't flag it.
4. **Dangling runtime state** `[P]` if this session started it, `[M]` otherwise — background processes this session started that outlive it: a live prod DB proxy or tunnel (security-relevant — flag it), a dev server / watcher, open Chromium debug tabs. Flag the ones that cost something; mention a harmless tab once at most.
5. **Standing instructions given to peer sessions** `[M]` — did this session `SendMessage` another session a *standing* instruction ("stop doing X until further notice", "hold off on Y")? That outlives this session and nothing downstream lifts it, so a stale one keeps suppressing correct behavior after its reason is gone. `ListAgents` to see which recipients are still alive, then lift or restate. A one-off request ("check if tests pass over there") is not this — only an instruction meant to persist.
6. **A ticket this session finished whose record hasn't caught up** — status `[P]`, requester `[M]` — read the ticket, don't recall it. Two checks ride on that one read:
   - **Its status contradicts the work.** The session landed the last thing its ticket was waiting on, but the ticket still reads `In Progress`, or its newest comment still says "open pending PR #N". Nothing downstream transitions it, and the board is what the team reads, so a finished row in the wrong lane costs a whole session to rediscover — even after a prior closeout returned a clean `done`. Surface the key plus the one transition that clears it. On boards that filter by a field (a sprint, a release), a ticket moved to Done may also need that field set or it vanishes from the board — check, don't assume.
   - **Its requester hasn't been told it's live.** Only when the session took to prod a ticket someone outside the team asked for. Nothing downstream sends that reply, and it is the one part of the work the requester sees.
     - **Who:** the reporter, plus the original asker when the ticket or its thread names one.
     - **Where:** the channel it came in on. One targeted search of mail (subject or ticket keywords; the mailbox search spans Sent) or Slack; keep the thread id.
     - **Told** = a message from the user in that thread dated after the prod deploy. A ticket comment or a Done transition doesn't count. Check the mailbox, not the session's memory: the user sends from their own client, so a reply the session didn't send is invisible to it.
     - **No thread** → still `[M]`: a new thread to the reporter. **Mail or Slack tool missing or logged out** → still `[M]`: "couldn't check — confirm the reporter was told."
     - The item names **who and which thread** — that lookup is the question the user otherwise has to ask. On `/go`, draft the reply as points (To / Cc / Subject, what changed, where it shows, anything that will look like a bug) and never send it.

Quick sweep for the git buckets. It finds the repo you're in plus any independent repos nested below it, and prints only the ones with something to report — so a repo that is clean and fully pushed stays silent:

```bash
{ git rev-parse --show-toplevel 2>/dev/null
  find . -mindepth 2 -maxdepth 4 -type d -name node_modules -prune \
    -o -type d -name .git -print 2>/dev/null | sed 's|/\.git$||'
} | sort -u | while read -r d; do
  out=$( git -C "$d" status --porcelain
         git -C "$d" log --oneline HEAD --not --remotes 2>/dev/null  # commits on no remote branch
         git -C "$d" worktree list | tail -n +2 )                     # extra worktrees only
  [ -n "$out" ] && printf '── %s ──\n%s\n' "$d" "$out"
done
```

A repo the session touched that lives *outside* the current directory won't be found — add its path to the list by hand. A repo with state the session never touched is `[M]` at most ("not this session's — left alone"), never `[P]`.

## Pick one of three

**`✅ Yes — done.`** — main work complete *and* nothing loss-bearing. Safe to `/done`. One line of why (e.g. "PR opened, ticket updated, memory captured, trees clean"), then stop. A clean yes is the most valuable answer this skill gives — don't pad it.

**`✅ Yes — done, grab N first.`** — main work complete (still a *yes*), but N **loss-bearing** items would be lost or stranded otherwise. List them tagged, each one line: what it is, why it's lost, the single action that clears it.

**`🛑 Not yet.`** — the main work itself is incomplete or live: uncommitted mid-edit changes, a migration half-run, a PR that still must be opened, an in-flight task. Name the live thing plainly. If it's worth preserving rather than finishing right now, point to `/handoff`. (Be honest here — don't green-light just because closing is easy.)

## Output

Lead with the marked verdict line so the answer is unmistakable at a glance. Then, only for the latter two, a tight bullet list — **every item tagged**:

```
✅ Yes — done, grab 3 first: main work shipped; these are lost otherwise

- [M] TICKET-123 is live but the two requesters haven't been told — no reply from you on "Re: export bug" since the deploy. → /go drafts the points; you send
- [P] 3 commits on `fix/ticket-124-banner` not pushed — local-only. → git push
- [P] timezone trap found today not yet in memory. → /compound captures it

/wrap-up clears the [P] items itself; the [M] one needs you.
```

If there are optional follow-ons worth a breadcrumb, add **at most one** deferred line — never itemized, never as a caveat on doneness:

```
(The report's next-effort options are there when you want them — not part of "done.")
```

**Under `nested`** (a composite such as `/wrap-up` passed the token and owns the terminus): emit the verdict line and the tagged list only, with no pointer line and no follow-on breadcrumb, then hand it back as mid-pipeline input. The caller's next step runs in the same turn; a pointer line here reads as a terminus and ends the caller's pipeline at the gate.

Point at `/wrap-up` (if installed), not `/done`, whenever a `[P]` item is listed: `/done` archives without running `/compound`, so the `[P]` it was counting on never happens. If the user fires `/go` instead, do the `[P]` actions and draft the `[M]` ones, then re-emit the verdict.

## Rules

- **Loss-bearing only.** No polish, no refactors, no resumable-later items: if it's safe in git / the tracker / memory, it is not a loose end.
- **Standalone, surface — don't fix.** Asked "are we done?", answer it; only bucket 1's triage acts. Run by `/wrap-up`, the `[P]` items are its to clear. Sends, force-pushes and shared-infra changes are never done here; a requester reply is drafted as points, never sent.
- **Cap the noise.** Many small things → surface the few that actually matter, not all of them.
- No preamble, no signoff, no hedging.

`nested` is a mode token, not a focus. If the user added a focus below, narrow the check to that slice (e.g. `/done-check git` → only the git buckets): $ARGUMENTS
