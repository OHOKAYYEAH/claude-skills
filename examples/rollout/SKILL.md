---
name: rollout
description: >-
  Take a reviewed, open PR the whole way up the deploy ladder —
  merge to dev + verify → promote to staging + verify → prod-readiness gate
  (HARD STOP for your go-ahead) → promote to prod → /smoke-prod. The standing
  composite for the four-stage promotion chain that otherwise gets re-improvised
  every ship: chains /merge-and-verify (dev hop), /promote (staging hop), a
  conditional /prod-ready, /promote (prod hop), /smoke-prod. Fire ONLY on an
  explicit rollout request — `/rollout`, `/rollout PROJ-123`, "take this all the
  way to prod", "run the full promotion chain" — NEVER proactively, and never
  merely because a /ship report said a PR is open: it deploys to staging and (on
  your word) prod. NOT /ship (that BUILDS and stops at PR-opened — this starts
  where it stops). NOT /promote (ONE hop; this chains three). NOT
  /merge-and-verify (ONE merge + deploy watch; this is the whole ladder).
  Test/docs/tooling-only diffs stop after the dev hop — the next release
  carries them (step 0b). Project-scoped example (genericized).
disable-model-invocation: true
argument-hint: '[ticket / PR id / scope hint] [tokens: "from staging" resume mid-ladder · "noqa" skip the per-hop browser QA · "full" climb every rung even for a test-only diff]'
---

> **Read-only example.** This is a *project-scoped* composite, shown to illustrate one idea: **a deploy ladder is a thin sequencer over single-hop atoms, with authorization that escalates by environment** — the invocation pre-authorizes the non-prod rungs, and prod always gets a fresh, explicit go-ahead. The real version encodes one team's repos, branch ladder and deploy triggers; everything identifying here has been genericized. Don't install it — adapt the pattern.

The ladder past the review boundary: **dev → staging → (your go-ahead) → prod → smoke.**

**Run only on the user's explicit rollout ask.** Invoking it authorizes the dev and staging deploys, so an open PR in a `/ship` report is not a reason to start it.

`/ship` ends at PR-opened because that's *your* review moment. `/rollout` is what you fire once you've reviewed and said go — it walks the same four stages you'd otherwise drive by hand, with the same gates, and stops dead at the prod hop for an explicit go-ahead.

**Thin composite by design.** The atoms own the substance — `/merge-and-verify` owns merge + CI-watch + QA, `/promote` owns the env-branch merge PR and its footguns, `/smoke-prod` owns the read-only prod pass. `/rollout` owns the **stage sequencing, the escalating authorization model, and the one final report.** If you're tempted to do atom-work here (polling CI, drafting QA scenarios, resolving a conflict), it belongs in an atom.

**Hard contract: this skill always ends with the Rollout Report — a `/report` call (step 6).** Every atom in this chain ends on a satisfying terminal block — that's four separate invitations to stall mid-ladder. An atom's report is **mid-pipeline input**; your next move is the next stage, not a wrap-up. The only two legitimate stops before the report are the prod gate (step 3) and a red stage.

## The authorization model (read first — it's why this is one skill and not four)

Invoking `/rollout` **is** your go-ahead for the dev and staging hops. You named the destination when you fired it, so don't re-ask at each rung:

- **dev** → proceed. Non-prod, pre-authorized writes.
- **staging** → proceed **only while every prior stage is green.** This deliberately pre-satisfies `/merge-and-verify`'s "staging re-confirm" rule — not a violation of it, a *composite-level* satisfaction of it, because `/rollout <scope>` — or a `/go` on a Ship Report whose Next line names `/rollout` — is an explicit staging authorization. Work *inside* an authorized rung (its QA pass, a re-run, a bounded fix and re-verify) never re-asks. The authorization lapses only on a 🛑 or a failure you can't fix in-rung: **then stop and ask.**
- **prod** → **hard stop, always, no exceptions.** Even though `/rollout` names prod as the destination, the prod hop needs a fresh, explicit go-ahead against the readiness report (step 3). Merging to a prod branch is a prod deploy.

## Argument parsing

`$ARGUMENTS` = optional ticket / PR id / scope hint + optional tokens:
- **`from dev` / `from staging` / `from prod`** → resume at that stage instead of auto-detecting. Override for when detection is ambiguous.
- **`full`** → climb every rung even when step 0b would stop at dev.
- **`noqa`** → pass through to each hop's `/merge-and-verify` (skips the browser QA). For a diff with no UI surface — though the atoms already infer that themselves, so you rarely need it.
- Anything else → scope hint, passed to every atom so they all narrow to the same slice.

## 0. Orient — find the work's rung on the ladder

`git fetch` in the service repo first (`origin/*` is a stale snapshot; never judge merged/ahead/behind without it), then locate the change:

- **Open PR into the integration branch** (e.g. `dev`, or `main` for a trunk-based repo) → start at step 1.
- **Already on the integration branch, not on `staging`** → start at step 2.
- **Already on `staging`, not on the prod branch** → start at step 3.
- Ambiguous → say what you found and ask; don't guess a rung that skips a verification.

**Multi-repo changes are stage-major, not repo-major.** A change spanning repos (e.g. a backend service + the frontend that calls it) walks *every repo through one rung* before any repo climbs to the next — backend first within the rung. Both sides must be live on staging before staging QA means anything; a frontend QA'd against a backend still on last week's code proves nothing.

## 0b. Decide how far the change has to go

**A change only earns promotion to the environments where it executes.** Every rung costs a promotion PR, a pipeline watch and, at the top, your attention at the prod gate. Code that never runs on staging or prod buys nothing from those rungs. Classify the change's own diff (its PR diff — not everything else riding the branch):

- **Stops at dev.** Nothing in the diff runs past the integration branch: E2E/unit specs and their support code and config, page objects, test-case docs, repo docs, `CLAUDE.md`, committed skills, dev-only scripts. The payoff lands the moment it merges, because every branch cut afterward inherits it. Run step 1, skip steps 2–5, and let the next release promotion carry it up.
- **Full ladder.** Anything the deployed service executes or reads: app code, config/env files, migrations, auth-provider actions, infra, and dependency bumps (the lockfile changes the built image).
- **Full ladder, even though it looks non-runtime:** CI/pipeline config that the staging or prod workflows read (a fix that reaches only dev leaves the prod pipeline broken), and any test or tooling fix a release branch in flight needs now.

A mixed diff takes the full ladder. Print the call as a `Decision:` line before step 1. `full` overrides a stop-at-dev call.

When it stops at dev, step 1's ✅ is the finish line: run 5b's close-out (ticket → Done, with a comment saying it merged to the integration branch and rides the next release; worktree teardown), and report staging/prod as ⬜ *rides the next release*, not *awaiting your go*. No `/promote`, no version tag, no `/smoke-prod`.

## Parallel sessions — who else is on this repo's ladder

Env branches are shared, and a promotion ships everything on its source branch, whoever merged it. So run this check before the staging promotion (step 2), at the prod gate (step 3), and again when the prod go arrives (step 4): the field moves while a gate waits. Skip it before the dev merge; a session promoting from `dev` asks for that hold itself.

**Look, cheapest first:**
- **Sessions:** list the other live sessions on this machine and peek at each one's last couple of turns without interrupting it (see the `/peek` example) — its cwd and branch say which repo it's on.
- **Riders** (other sessions' changes your promotion would carry): match the ticket keys in `git log --format='%h %s' origin/<to>..origin/<from>` (merge subjects name the branch) against those sessions' names. A commit with no live owner still goes in the gate's *Riding along* line, as before.
- Nobody else on this repo's ladder → print `Parallel: clear (N live sessions)` and move on. No messages.

| Another session… | Do this |
|---|---|
| has a change on your source branch (a **rider**) | Carry it; its owner QAs it on the next rung and replies READY. Still verifying → wait for its verdict. Red → hold until its fix lands |
| has a PR into your source or destination branch | Ask it to hold that merge while your hop runs |
| is mid-hop on this repo, at or above your rung | Hold while its hop runs; it leads |
| works in a repo that consumes yours, or that yours consumes | Ask ACK-WAIT or ACK-INDEPENDENT (does its change need code your hop hasn't shipped?); the provider ships first |
| is doing infra on the same env (terraform, a restore, a maintenance window) | Ask its window and sequence around it |

**Lead and holds.** The session taking the highest rung on a repo leads it, since it owns the step that's hardest to undo; at the same rung, the one already promoting. While a hop runs, nothing merges into the lead's source branch until its promotion PR merges, nor into its destination until its DONE. Dev merges stay open during a prod hop.

**Combine or queue.**
- **Same rung, same time → ride together:** one promotion, one version number (the version-check helper returns NOOP for a second staging hop before prod), one prod gate listing every rider, one `/smoke-prod` covering every rider's surface.
- **The lead is at the prod gate or past it → queue.** The user's go covers a payload, and a late joiner would change it after they looked. The gate block names who is queued. If the user says "join", the joiner asks the lead to release the hold; the lead waits for its READY on staging and re-presents the gate.

**As a rider,** don't call `/promote` for a rung the lead is promoting. Once your change lands on staging, QA it there as usual and send the lead `READY <ticket>: <verdict + evidence> · risk surfaces: <…> · smoke: <surface>`, or NOT-READY and why. You hold no prod gate of your own: the user's go in the lead's session covers what its readiness block lists. On its prod DONE, go to 5b.

**Mechanics:** message peers with a session-to-session relay that has a lead/coordination mode (see the `/relay` example), run inline rather than chained, so its plan line doesn't end this turn. Message only sessions with a stake, naming the repo, the hop, what to hold and what releases it, and that each session's prod go comes from the user in its own session. As lead, close every hold on every outcome: PAUSED at the prod gate, ABORT on a red rung, DONE after the smoke with the merge SHA, tag and live revision so peers can check them.

**Holding is a blocked prerequisite, not a question for the user.** Emit `/report`'s mid-flight hold report (who you're behind, and what unblocks it, e.g. "answer PROJ-123's prod gate") and end the turn. On the lead's DONE: `git fetch`, check its SHAs and revision yourself, re-run this check, and continue on your own authorization. DONE releases a hold; it is never a go.

## 1. Dev hop — /merge-and-verify

Invoke `/merge-and-verify` with the scope hint + `nested` (+ `noqa` if passed) — `nested` makes it hand its report back to this chain instead of ending the turn on it. It merges the reviewed PR into the integration branch, watches CI deploy it green — pinned by merge SHA, so it can't read a stale pre-merge pipeline as a false green — and runs `/qa dev` against the deployed env, skipping the QA when the diff has no browser surface.

**Gate:** ✅ → step 2. ⚠️ (deployed with a caveat, e.g. a red sibling test job on a CI-image issue) → surface it, and continue only if the caveat is provably unrelated to the diff. 🛑 → **stop.** A regression here is already live on dev; the fix goes through a fresh `/ship` cycle so review + gates run again, not a quiet re-push into this chain.

## 2. Staging hop — /promote

**First, the parallel check** (§ Parallel sessions): a hold pauses this rung, and if another session is already promoting your change, you ride it instead of calling `/promote`.

Invoke `/promote <integration> staging` (e.g. `dev staging`) through the Skill tool — also when the ladder resumes after a detour (a question, a side investigation). The project backs this with a hook that blocks any promotion PR created without a `/promote` call since the user's last message.

**`/promote` already chains `/merge-and-verify` internally** — it runs the `merge-tree` conflict pre-check, opens the promotion PR, then hands to `/merge-and-verify` for the merge + deploy-watch + `/qa staging`. So **do not invoke `/merge-and-verify staging` yourself afterward**; there'd be no open PR left and you'd be re-running a pass that already happened. One `/promote` call *is* the whole staging rung.

Three things to carry into it explicitly so they survive the handoff:
- **`nested`**, which `/promote` passes to its chained `/merge-and-verify` — the rung's report comes back to this chain, not as a turn-ending terminus.
- **Never close the source branch.** The promotion PR's source is the long-lived `dev` branch; the git host's merge default would delete it. `/promote` forces the no-close-source option — name it in the handoff anyway.
- A promotion carries the **whole** source branch. If anything else has landed on `dev` since the last promotion, this rung ships that too — the parallel check names each rider's owner; flag anything unexpected before merging rather than discovering it in the prod readiness report.

**Gate:** same shape as step 1, but a 🛑 here is sharper — it's live on the prod-like env and the next rung is prod. Stop loudly.

## 3. Prod-readiness gate (HARD STOP)

Staging is green and QA'd. **Do not continue.** Run the parallel check (riders and queued sessions belong in the block below), assess readiness, report, and wait for an explicit go-ahead.

**Choose the depth — don't reflexively run `/prod-ready`.** It's built to reconstruct *cold* state from durable artifacts, which is mostly redundant right after a chain that watched every deploy happen live. Escalate to a real `/prod-ready` run when the diff, or a rider's READY, touches something this chain genuinely cannot see:
- a **DB migration** (does it reach prod, and how — auto-on-approve vs no-auto-migrate? is it reversible?),
- a **new env var / secret reference** (present in the *prod* env's secret store, or the deploy fails when it reads it),
- a **cross-repo contract** a sibling repo consumes (an API shape, a shared column, any other shared contract) → lockstep deploy,
- **Terraform** (CI never applies it — a human does),
- a **per-env feature flag** whose prod value differs from staging's,
- or the work is **cold** — staging deployed in an earlier session / days ago.

None of those → skip it and write the lean block below from what the chain just proved. Either way the output is **one glanceable verdict + the conditions**, not a ledger:

```
### Prod Readiness — <scope>
**Proven:** dev <✅ CI green · QA: …> → staging <✅ CI green · QA: …>
**Riding along:** <commits on staging beyond the last prod release, each rider with its owner session and staging verdict — or "just this change">
**Parallel:** <holding <sessions> until DONE · queued behind this gate: <sessions> — or "clear">
**Prod hop:** <repo · staging → prod branch · deploy trigger · manual approval step: yes/no>
**Risk surfaces:** <migration / secret / cross-repo / terraform / flags — or "none; code-only, revision rollback">
**Verdict:** <🟢 clear to ship / 🟡 clear with N conditions / 🔴 blocked: …>
```

**Probe the prod session before writing the close** — a prod login usually outlives a deploy (the debug browser keeps its profile; SPAs often hold refresh tokens in localStorage), so an unconditional nudge makes the user redo a login they still have. `new_page` on the prod URL from the table below (never an isolated context — it has no cookies), wait for the app to settle, `take_snapshot`, `close_page`. That's the whole probe: no input, no clicks, no `get_network_request`. It only checks the login; the smoke itself comes later.

Close with the go-affordance plus one of these, because `/smoke-prod` can't authenticate and stalling on it at the end is a wasted round trip:

- **Snapshot shows the app** → `/go` to promote staging → prod. You're already logged into <APP> prod; `/smoke-prod` will reuse that session.
- **Login screen / auth redirect, or the probe couldn't run** (no browser on the debug port) → `/go` to promote staging → prod. **Log into <APP> prod — <URL> — in the debug browser now**; `/smoke-prod` attaches to your session at the end, it never logs in itself.

**Always name the app AND its prod URL** — someone context-switching between several apps can't tell at a glance which one "log into prod" means. Pick the surface `/smoke-prod` will drive: the app that renders the change; for a backend repo, the app its users see it in. Keep a small repo → app → prod-URL table in the skill (e.g. a backend service → app A at `https://app-a.example.com`, the app that renders its data), and when a URL isn't in the table, confirm it before naming it.

Two apps touched (e.g. a backend change visible in both app A and app B) → name both, primary first. If reaching prod needs network access the user may not have open, say so in the nudge.

**If the gate goes unanswered** — you defer, or the session ends — leave a breadcrumb that outlives the transcript: a one-line comment on the ticket ("verified on staging — awaiting prod hop", naming any sessions queued behind it) with the ticket left non-terminal. A pause nothing tracks silently becomes an abandoned release — green on staging and forgotten.

## 4. Prod hop — /promote, on the go-ahead only

**Re-run the parallel check first.** While the gate waited, a rider may have landed on staging or a peer may have started a hop. Anything new on staging means the user's go no longer covers the payload: re-present the gate instead of promoting.

**The go-ahead is a new message, so call `/promote` again through the Skill tool** — don't replay the staging hop's commands with the branch names swapped. Its prod-only rules (the version tag, the sweep of stale approvals) only apply when its text is loaded for *this* hop, and the promotion hook blocks the PR otherwise.

Invoke `/promote staging <prod-branch>` with **`noqa`** and `nested` passed through to its chained `/merge-and-verify`: the post-deploy browser pass on prod is `/smoke-prod` (step 5), which is read-only and attaches to *your* authenticated session — there is deliberately no mutational QA against prod, so don't let the inner QA inference reach for one.

Prod mechanics worth checking before you declare the deploy done:
- **If a repo deploys prod on a push to its prod branch**, that workflow often waits at a **manual approval step**. Your go-ahead in step 3 covers approving it — but if a migration rides along, approving that step *is* approving the migration, with no checkpoint after it.
- **If a repo deploys prod on tags** (its prod workflow filters on a version-tag pattern and ignores branches), merging `staging` into the prod branch alone deploys **nothing**. The tag push is a separate, required step — confirm the mechanism in the repo's CI config and raise the tag as an explicit action rather than reporting a merge as a prod deploy.

- **Every repo gets a version tag on the shipped commit** — `/promote`'s prod-tag step owns
  the mechanics (tag first where the tag *is* the deploy trigger, tag after the deploy
  is proven where a branch push is, and no tag yet where the CI would misfire on a
  tag push until it's guarded). The number itself is claimed once,
  at the staging hop, and `/promote`'s version-check helper gates it before the prod PR
  and again before the tag. Don't let the chain end with prod live and nothing durable
  recording which commit that was.

Then **prove the artifact is live** rather than trusting the pipeline status line — `/merge-and-verify` step 5 owns this (route probe / bundle-hash flip), and it matters most here.

## 5. /smoke-prod

Invoke `/smoke-prod <scope>`, with every rider's smoke surface added to the scope (one smoke covers the release) — **even for a no-UI diff**: a new revision rolled, and that is what gets smoked. So keep the step-3 session probe too. It attaches to the browser session you logged into, drives read-only navigation of the shipped surface, checks console + network, and returns a smoke verdict. If it reports an unauthenticated session, ask for the login — naming the app and prod URL, same as step 3 — and resume; never drive the prod login.

A ⚠️/🛑 here is a **live prod problem**: surface it immediately and loudly at the top of the report, and don't poke at prod trying to characterize it further.

## 5b. Close out — automatic on a green smoke, don't ask

**A ✅ smoke is the completion signal (or step 1's ✅, for a change step 0b stopped at dev). Close the ticket and tear down the work yourself** — this is pre-authorized, not a judgment call, and asking about it is friction at exactly the moment the user is context-switching away. Shipped-to-prod-and-smoked *is* done; a ticket left In Progress after that is just a lie the board tells.

- **Before closing, triage what the ticket still holds.** A ticket with an unchecked checklist, `leftover:` comments, or notes "recorded here rather than filed" is the only home those items have, and closing it orphans them. Run `/triage` once on all of them (it dedupes, merges and files within its budget), cite the result in the closing comment, then close. Nothing left → skip.
- Transition the scope's ticket to **Done** via the tracker's API or MCP — look up the Done transition's id for that ticket rather than hardcoding one.
- Before transitioning, make sure the **durable comment from step 3 exists and is current** — what shipped, the measured results, the release tag, and any follow-ups. The comment is what survives; the status is just the flag.
- **Do NOT auto-close on ⚠️ or 🛑**, and don't close when the chain stopped short of prod. Those stay non-terminal.
- **A post-release acceptance count (errors over a set watch window) does not hold the ticket open.** Close it on the green smoke and put the count on the calendar; if the count fails, reopen the ticket. Reopening beats an In Progress ticket used as a timer.
- **Tear down the shipped work's worktrees** — every worktree whose branch this rollout carried to prod, across repos. Stop the worktree's own dev server first (it's yours to stop, and a live server makes the cleanup keep the tree), then run the project's worktree-cleanup tooling on it: trees it would otherwise flag for review are safe to remove here, since prod containment is the proof that review was waiting for. A tree with uncommitted/unpushed work stays put and goes in the report.
- **Delete the merged local branches** — the feature branch and any `promote/*` resolve branch — once `git merge-base --is-ancestor <branch> origin/<prod-branch>` passes. `-D` is fine after that check; plain `-d` compares against the checkout's current branch and false-alarms.
- Worktrees or branches *unrelated* to this rollout are not yours to sweep — name them in the report's Next line.
- **Send DONE** to every session you held or carried: merge SHA, tag, live revision, smoke verdict and evidence path. Riders close their own tickets and trees.
- **As a rider,** the lead's ✅ smoke is your completion signal once you've checked its DONE yourself (`git merge-base --is-ancestor <your merge sha> origin/<prod-branch>`, revision live). Then close out your own ticket and tree as above.
- Also handle the **post-release merge-back** if a repo needs one (e.g. if its release tooling commits a version bump on the release branch, merge `staging` → the integration branch, or the bump never reaches trunk and the next release reuses a version). Open it, merge it without closing the source, confirm trunk's version file matches the tag.

**Follow-ups are triaged, not bulk-filed.** File a ticket only for the *substantial* ones — a real defect, a control gap, something with a user-visible or data-integrity consequence. Route them through `/triage`, which applies exactly that bar: substantial → a ticket, real-but-minor → the repo's `FINDINGS.md`, the rest dropped and named. Don't park them as a comment on the ticket you're closing — a comment on a Done ticket is on no board and in no query. Never bulk-file five tickets nobody will prioritize.

## 6. Rollout Report via /report (terminus)

**Invoke `/report` through the Skill tool as the last call of the turn** — every run, including one that stopped at the prod gate or a red rung. It lands at a context-switch moment, so it takes `/report`'s glanceable shape (bold verdict, icon table, numbered Next) instead of a block the user has to hunt through. If `/report` isn't installed, emit the same rows directly as the final block. Feed it these rows:

```markdown
### Where <scope> stands
**<✅ live on prod & smoked / ⚠️ live with caveat: … / 🛑 stopped at <rung>: …>**

|  |  |
|---|---|
| ✅ **dev** | PR #N merged · CI #X green · QA: clean/skipped/findings |
| ✅ **staging** | promotion PR #N merged · CI #Y green · QA: … |
| ✅ **prod** | promotion PR #N merged · approvals given · CI #Z green · revision R live · tag vX.Y.Z — or ⬜ "awaiting your go" |
| ✅ **Smoke** | routes checked · evidence path |
| ✅ **Closed out** | ticket → Done + comment · worktrees + merged branches removed · merge-back PR #N |
| ✅ **Follow-ups** | N filed (keys) / N left in the ticket comment / none |
| ✅ **Parallel** | led <repo> <hop>: held <sessions>, DONE sent / rode <session>'s release / queued Nm behind <session> |
```

- A ⚠️/🛑 row sorts to the top and drives the verdict — a prod problem is the first thing the user reads.
- Omit the **Parallel** row when every check came back clear.
- **Next** is only what's genuinely the user's (a leftover local command, a held worktree to push, unrelated stale trees). Nothing left → `**Next:** nothing — <scope> is done.`
- Stopped at the prod gate → the readiness block from step 3 *is* that turn's content; still close on `/report` with prod ⬜ and Next = "`/go` to promote to prod" (plus the login nudge only if the step-3 probe hit a login screen).

## Guardrails

- **Climb only as far as the change runs (step 0b).** A test/docs/tooling-only diff finishes at dev; promoting it spends rungs on code staging and prod never execute.
- **The prod gate is absolute.** Always stop at step 3, every time, however explicit the original request was. dev and staging ride on the `/rollout` invocation; prod never does.
- **Green-only continuation.** Any ⚠️ you can't prove unrelated, or any 🛑, ends the chain there. "It's probably fine" is how a staging regression reaches customers.
- **One `/promote` per rung — never double-run `/merge-and-verify` after it.** The most likely mechanical mistake in this chain. The second most likely: running a rung inline instead of calling `/promote` fresh for it.
- **Never close the source branch on a promotion merge.** Deleting `dev` or `staging` is the footgun `/promote` exists to prevent; don't undermine it from the composite.
- **Stage-major across repos.** All repos on a rung before any repo climbs.
- **Never ship another session's change behind its back.** Every rider's owner hears it's shipping and QAs its own change on the rung; every hold you set ends in DONE, ABORT or PAUSED.
- **Never `/qa` prod.** Prod gets `/smoke-prod` — read-only, attached to the user's session — and nothing else. There is no QA-prod skill by design.
- **A regression is a stop, not a patch-and-repush.** Fixes re-enter through `/ship` so the review gates run again, then `/rollout` from the bottom rung.
- **Don't fake a rung.** CI unwatchable, QA unrunnable, artifact unverifiable → say so in the report; don't claim "verified."
- **No halt after a green smoke.** Ticket close, worktree teardown and branch deletion are the ladder's last rung, not a question. The prod gate (step 3) is the only human stop past staging.
- **One terminus: the `/report` call.** Four atoms, four satisfying blocks, one report — never a second summary after it.
- **Don't expand scope.** Out-of-scope problems you trip over → the report's Next line.
