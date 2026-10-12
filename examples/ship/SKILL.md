---
name: ship
description: "THE DEFAULT BUILDER in this project: any ready-to-build ticket, feature, or slice (\"let's build X\", \"we can move forward\") goes here, not to standalone /work. Takes a chunk of project work from plan all the way to an open PR — chains /work (plan + /review-plan + build + /mutate, plus /test when the diff has none + /super-review) → ship gate → /qa-and-pr (local-env-up + seed-if-thin + /qa run local + /e2e + /pr). The \"build it right, prove it locally, then land it\" driver that /work deliberately stops short of. Thin composite by design — the two legs (/work, /qa-and-pr) own the substance; this skill is the gate between them. Local-machine scoped: encodes one project's build→local-QA→PR workflow. Project-scoped example (genericized)"
disable-model-invocation: true
argument-hint: "[optional scope hint, passed to both legs] [optional \"tdd\"/\"notdd\" token, passed to /work] [optional \"noticket\" token, skips step 0b]"
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate the thin project composite that makes "build this" mean one thing: it runs the shared `/work` orchestrator, gates on its review recap, then hands off to the project's own land-leg. Everything project-specific lives in that land-leg, so the composite stays small. Don't install it — adapt the pattern.

Run the full project ship pipeline on the current scope: **(warm local env in background) → plan → harden → build → review → (gate) → local-env-up → seed-if-thin → local-QA → (gate) → PR.** This skill is deliberately **thin**: the two legs do the work — `/work` produces reviewed code, `/qa-and-pr` verifies it locally and lands it — and `/ship` is the **gate between them** plus the single final report. Project glue, by design; the reusable building blocks (`/work` and what it chains) stay machine-level in your shared skills dir. Project → shared is the right dependency direction — never push this workflow down into a shared skill.

This project verifies **locally before** opening a PR (CI deploys after the user reviews + merges). A deploy-first project would land to its staging environment first and verify there instead — that asymmetry lives entirely in the land-leg (`/qa-and-pr` here), so `/ship` and `/work` stay structurally identical across either flow.

**Hard contract: this skill always ends with a Ship Report (step 5).** It either ships-to-PR, or it stops at a gate and says exactly why — it never trails off mid-pipeline. The most common failure mode is an inner leg returning its block (`/work`'s `/super-review` recap, `/qa-and-pr`'s report) and you writing a turn-ending wrap-up. Don't. The inner block is **mid-pipeline input** — your next move is the next step, not a yield. (This is why both legs are invoked with the hand-back token: `/work noreport` ends at its `/super-review` recap, `/qa-and-pr nested` hands its report back — neither emits the satisfying terminal block that would stall this pipeline. `/ship`'s own Ship Report is the single terminus.)

## Argument parsing

`$ARGUMENTS` = optional scope hint + optional `tdd`/`notdd` token.
- Pass the **scope hint** through to both `/work` (step 1) and `/qa-and-pr` (step 3) so they narrow to the same slice.
- Pass a **`tdd`** or **`notdd`** token through to `/work` if present — `/work` builds test-first by default for behavior changes; these force it on or off. Don't pass `nohard` unless the user explicitly wants a fast, un-hardened ship — the `/mutate` hardening (plus `/test` when the diff arrives without tests) rides along inside `/work` by default, so the diff reaches the gate already coverage-audited.
- A **`noticket`** token skips step 0b (the ticket resolve) — for a scope the user has said doesn't warrant one.
- Do **not** pass any QA/devtools token to `/work` — browser QA happens in the `/qa-and-pr` leg against a real local server, not mid-build (`/work` has no devtools phase; that lives in this land-leg).

## The workflow

### 0. Warm the local stack in the background (non-blocking, never a gate)

`/qa-and-pr` (step 3) opens by probing the shared backends and booting whatever is missing — and that boot depends on **nothing** `/work` produces. Start it now, concurrently with the build, so the server is warm by the time the gate passes instead of costing a cold boot afterward.

- Probe first: `curl -sf localhost:<backend-port>/health` for each shared backend service. **Already up → do nothing, go to step 1.**
- Missing → start the backends the scope needs, headless and **backgrounded** — the same carve-out `/qa-and-pr` step 2 already operates under. **Never** the full stack with frontend dev servers (those stay the user's to run).
- In a **worktree**, this only warms the shared backends. The worktree's own server still comes up in `/qa-and-pr` step 2, which picks its non-colliding port — don't do that here.

**Three hard rules, because this step must never be able to stall the pipeline:**
1. **Non-blocking.** Fire it and move to step 1 in the same turn. Do not wait for health, do not tail logs here, do not report on it.
2. **Never a gate.** If the boot fails, errors, or the probe is ambiguous — *say nothing and continue*. `/qa-and-pr` step 2 re-probes and owns the real bring-up, including the failure path. A warm-up failure is not a ship failure.
3. **Skip entirely if the scope is obviously non-UI** (pure backend/migrations/config/docs/test-only) — `/qa-and-pr` will skip browser QA anyway, so there's nothing to warm.

Cost of a wasted warm-up when the gate later stops the ship: one idempotent background boot. Cheap against a cold boot on every green ship.

### 0b. Resolve the ticket — /ticket

Invoke **`/ticket`** with the scope hint, before the build. Project work is
supposed to be on the board; the close-out end of the promotion ladder assumes it
(the final hop transitions "the scope's ticket" to Done), so a ship that never opened one
leaves that step with nothing to close and leaves the work invisible to anyone
reading the board.

`/ticket` dedupes first, so the overwhelmingly common outcome is **"already tracked
as PROJ-NNN"** — it returns the key and costs one search. It creates only when
nothing covers the scope, and then sets the active sprint and the In Progress lane
so the ticket is actually visible rather than merely existing.

- **Carry the key forward.** `/pr` (inside `/qa-and-pr`) links tickets as
  `[PROJ-123](https://tracker.example.com/browse/PROJ-123)` — pass the key
  through with the scope hint so the PR body links it without you re-deriving it.
- **Not a gate.** If the tracker is unreachable or the dedupe verdict is genuinely
  ambiguous, say so in one clause and build anyway — an unfiled ticket is a
  bookkeeping miss, not a reason to stop shipping. Surface it on the Ship Report's
  Next line so it doesn't evaporate.
- **Skip** on the `noticket` token, or when the scope is plainly not board-worthy
  (a typo fix, a comment, a lockfile bump). If `/ticket` isn't installed, skip this
  step and note "no ticket step" on the report.

### 1. Build — /work noreport [tdd]

**Resume entry: the build already ran.** If `/work` already finished on this scope in this session, with a Super-review Recap in context and no edits since, skip this step. Print `Build: resumed — /work finished at <recap status>; entering at the gate`, then go to step 2 with that recap. Any edit after the recap → run step 1 as normal, since the gate must read a review of the final diff.

Invoke `/work` with `noreport` (+ the scope hint, + `tdd` if passed). `/work` owns the front-half: for a non-trivial scope it **plans**, **hardens the plan** (`/review-plan`), decides the surfaced questions itself (a printed `Decision:` line each — only the halt tiers pause), drives the work feature-complete, **hardens the tests** (`/mutate`, plus `/test` when the diff has none), runs `/super-review` (in an isolated fork), and — because of `noreport` — **ends at its `/super-review` recap instead of a terminal `/report`.** Trivial scopes self-skip planning. Nothing for `/ship` to add here — let `/work` run its course and read its recap at the gate.

### 2. The ship gate (hard — this is the whole point)

Read `/work`'s **Super-review Recap** (returned by `/super-review`'s fork) **→ Status:**
- **✅ ready to push** → **your immediate next action is a `Skill(qa-and-pr)` call (step 3).** Do not write a recap, a summary, or any prose first — the instant `/work` hands back on a green verdict, invoke the land-leg. **This is the stall the gate is built to survive:** `/work`'s hand-back ends near a satisfying "✅ ready to push", and if you wrap up the turn there instead of calling `/qa-and-pr`, the pipeline stops half-landed (the user then has to nudge it forward themselves). If you catch yourself composing a turn-ending message after the hand-back, that IS the stall — call `/qa-and-pr` instead.
- **🔧 fixes owed**, or **any escalation tagged `[caller-resolvable]`** → **not a gate. You fix it and continue.** Make the call on each one (a `Decision:` line), act on it, re-run `/super-review` on the fixed diff, then go to step 3. Say what you applied in one line and keep moving — no Ship Report, no question, no yield. **The party with the most context is you, not the user**: the fork was denied this session's investigation, prod anchors, ticket semantics and everything already decided here, and it is contractually forbidden to decide. Its escalation is a hand-off of work, not of authority.
- **`[needs-user]` + origin `pre-existing`** (and not widened by this diff) → **⚠️, but still not a stop.** Land it, carry the finding onto the Ship Report's Next line, and **queue it as a triage candidate — don't file it here.** `/triage` runs before the report and decides whether it earns a row; filing straight from this step is how one shipped ticket leaves four unprioritized ones behind. The hole is live whether or not you ship; holding a green diff on it buys no safety and only delays the fix that would have gone out.
- **`[needs-user]` + origin `introduced`** (or a pre-existing one this diff materially widens) → **🛑. This is the one real gate.** Do not run the land-leg, and deliver the Ship Report in THIS turn.

  **The stop is a terminus, not a pause.** Emit the Ship Report (step 5) with the finding in full, `/super-review`'s recommended option, and one explicit question — all before the turn ends. **Never end the turn on a colon, or on "let me first check X."** If one more fact would sharpen the recommendation, resolve it *before* you start writing; if it can't be resolved now, state the recommendation conditionally and ask anyway. A turn that ends mid-investigation with no report and no question is a stop nobody sees until hours later.

  **One carve-out, and it decides more ships than the rule above:** a `[needs-user]` item that is a **domain-ratification ask rather than a defect** — "is this the right modeling basis?", "does the stakeholder agree this field means X?" — **rides the PR; it does not block the build.** `/ship` ends at PR-opened, which *is* the user's review moment, and a PR is not a deploy. Apply everything caller-resolvable, land the PR, and put the question in the PR description, on the Ship Report's Next line, and in the email/Slack ask. The gate that must never be crossed unattended is the deploy ladder (the staging and prod promotion hops), and that one already hard-stops. Only a `[needs-user]` finding that means **the code is wrong** stops the build.

  An **untagged** escalation is a `/super-review` contract miss — apply the test yourself ("could I resolve this with what I already know?") rather than defaulting to a stop. Untagged ≠ `[needs-user]`.

Also confirm the build is genuinely green (tests passed inside `/work`, including any the harden phase added). If `/work` couldn't complete a phase, or the harden phase surfaced a **latent bug or an unclosed real gap**, treat it as **not-✅** and stop at the gate.

### 3. Verify locally + land — /qa-and-pr nested

Invoke `/qa-and-pr` with `nested` (+ the scope hint). It owns the land-half: brings up this service's local server (worktree-aware — starts the per-worktree dev-server launcher itself in a worktree, else uses the canonical shared-stack port), **seeds the local DB from staging if it's too thin** to exercise the change, runs `/qa run local` against it, runs the E2E specs that cover the diff via `/e2e` (which may also graduate one new spec onto the PR), gates on a clean pass, then opens the PR via `/pr`. Because of `nested`, it **hands its QA-and-PR Report back as mid-pipeline input** instead of ending the turn. Two inherited rules:
- **The land-leg's gates are `/ship`'s gates.** If `/qa-and-pr` stops (shared stack down, env unreachable, a real QA regression), `/ship` stops there too — surface it in the Ship Report, don't try to land around it. `/ship` adds no second gate here and removes none.
- **A real QA regression is a stop, not a patch-and-repush** — fixing it goes through a fresh `/ship` (or `/work`) cycle so the `/super-review` gate runs again on the fix.

### 4. Show it — /before-after

Invoke `/before-after` with the scope hint. It assembles the frames `/qa-and-pr` carried out of the browser pass into one proof sheet and hands back a single page path — the visual answer to "what did this session actually change," which is what makes a parallel session cheap to come back to.

**It never gates and never stalls.** It returns one line; fold that line into the report below and keep going. A backend-only diff with no visual surface returns one honest clause instead of a sheet — that's a correct outcome, not a failure. If it can't build the sheet (or `/before-after` isn't installed), the Ship Report says so in a clause and the PR still stands.

Run it **after** `/qa-and-pr` (the frames don't exist until the pass has run) and **before** the report, so the page lands attached to the terminus rather than trailing after it.

**The sheet auto-opens here** — this is one of `/before-after`'s two auto-open moments. `/ship` ends at the report, which is the user's review moment with them at the terminal, so the tab is the point rather than an interruption. Frames are local-fidelity (`/qa-and-pr` runs `/qa run local`); the prod-like counterpart opens later, at the staging rung.

### 4b. The QA sweep-up — /triage, second pass only

**The main triage pass already happened, inside `/work` at its step 5b, before
this ship froze anything.** That position is deliberate and it is not this skill's
to move: `/triage`'s fold disposition requires an open host diff, and by the time
step 3 has run local QA and opened a PR, a fold costs a new commit, a re-QA and a
re-review. Calling triage *here* for everything is what turns it into a ticket
printer — most of what it files is found-in-flight noise that folding would have
absorbed.

So this step is narrow: **only candidates that did not exist when `/work` triaged**
— things the browser QA pass in step 3 turned up, plus `/e2e`'s *For /triage* list
(pre-existing reds, flakes, "needs testid" lines). Usually that list is empty; say
"none" and move on.

When it isn't empty, invoke `/triage` with the whole list in one call, and tell it
what `/work`'s pass already spent: the one-row budget is per *ship*, not per call.
If `/work` already filed its row, this pass files nothing — its survivors go to
`LOG` or onto the Ship Report's Next line for the user.

**Nothing else in this pipeline files a follow-up ticket.** Step 0b's `/ticket`
resolves the *scope's* ticket and nothing more. A ship that leaves four new rows
behind is the failure this step exists to prevent.

### 5. Ship Report (terminus)

```
## Ship Report — <scope>
**Ticket (/ticket):** <KEY · created | already tracked · lane> — or "skipped: <why>"
**Built (/work):** <scope · key files · test/harden outcome · /super-review verdict> — carries the build detail /work's suppressed /report would have shown
**Verified (/qa-and-pr):** <env QA ran in · what was seeded · QA result — clean/findings · the `E2E:` line, e.g. "E2E: frontend · 6 specs · 6 green · no reds · graduated none · 3m10s">
**Shown (/before-after):** <proof sheet: /abs/path (opened | path only)> — or "no visual surface — proof is tests + /super-review"
**PR:** <url · base branch> — or "not opened: stopped at <gate> because <why>"
**Triage (/triage):** <in /work: N candidates → D deduped · F folded · X filed · L logged · R dropped · Q asks> + <QA sweep-up: none | N more> — or "no findings beyond scope"
**Riders (FINDINGS.md):** <N folded from the repo's FINDINGS.md backlog by `/work`, entries deleted: headings> — or "none"
**Next:** reviewed the PR? → take it up the promotion ladder (or `/go`) — merge to dev + verify (`/merge-and-verify`), promote to staging + verify, prod-readiness gate, promote to prod, post-deploy prod smoke check. Plus any queued follow-ups (e.g. the next slice).
```

## Guardrails

- **Step 0 is a warm-up, never a gate.** It fires the headless backends in the background and is forgotten; `/qa-and-pr` step 2 owns real bring-up and every failure path. If step 0 ever blocks, waits, or stops the pipeline, that is the bug — delete it before debugging anything else.
- **The gate routes on WHO can resolve it, never on severity.** A HIGH finding with a bounded, in-scope, provable fix is yours to apply — it is not a human-in-the-loop case. Only a `[needs-user]` finding (domain semantics, release coordination, prod-data risk, scope expansion) that this diff introduced or widened stops the land-leg. When it does stop, the stop is absolute *and* loud: Ship Report plus an explicit question, same turn, never silent. Anything else is decided in-flow.
- **Don't launder a decision you can make into a question.** A gate that stops green ships on questions that all resolve as "yes, do the obvious thing" is pure cost. Halting is not the safe default — it is a cost, paid in the user's attention, and it needs to buy a decision only they can make.
- **The ticket step never gates.** Step 0b resolves a key and moves on; a tracker hiccup is a clause in the report, not a stopped ship. The gate in this pipeline is step 2 and only step 2.
- **Findings are decided inside `/work`, not here.** Step 5b of `/work` owns the triage pass, because that is the last point where folding a finding is cheap. Step 4b is a sweep-up for what QA found afterwards, and it inherits the same one-row-per-ship budget. If you find yourself wanting to file a follow-up anywhere else in this pipeline, that is the fan-out failure, not an exception to it.
- **Stay thin.** `/ship` adds the gate and the report — nothing else. Don't duplicate the legs' logic (server bring-up, seeding, QA, commit/push/PR all live in `/qa-and-pr`; planning/building/review live in `/work`). If you're tempted to do leg-work in `/ship`, it belongs in a leg.
- **Land via PR, not a direct push.** The project integrates through PRs to the integration branch — local QA + a PR is the fidelity checkpoint; CI deploys after the user reviews + merges.
- **`/ship` ends at PR-opened — that's the review moment, by design.** It deliberately does **not** merge; merging is the user's call after they review. **The post-review leg is the promotion ladder** (merge to dev + verify → promote to staging + verify → prod-readiness gate → promote to prod → post-deploy smoke check), kicked off by their go-ahead; a plain `/go` on the Ship Report's Next line picks it up. Don't chain it from here. `/merge-and-verify` is the ladder's first rung; name it alone on the Next line only when the dev hop is genuinely all that's wanted (a change deliberately parked on dev).
- **Local QA, not localhost-mid-build.** Verification runs against a real running local server in the land-leg — that's the whole point of factoring QA out of `/work`.
- **Don't fake completion.** If the land-leg can't bring up the env or `/qa` can't run, the Ship Report says so and stops before the PR — don't claim "verified."
- **One terminus: the Ship Report.** A leg's hand-back block is mid-pipeline — never end the turn on it.
- **Don't expand scope.** Out-of-scope problems you trip over → the report's Next line, not this cycle.
