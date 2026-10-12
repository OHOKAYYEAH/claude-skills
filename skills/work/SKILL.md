---
name: work
description: "Autonomous chunk-of-work pipeline — find or freeze the spec (/spec) → context-aware plan + /review-plan → execute (test-first via /tdd for behavior changes, red run shown before any implementation) → /spec-check the build against the spec → harden tests (/mutate, plus /test when the diff has none) → /super-review → /triage → /report, in order, without yielding between phases. Ends only when /report fires. Produces reviewed code; browser QA is deliberately NOT part of /work (that's /qa, or a project ship composite). NOT the default builder where the project has a ship composite (e.g. the /ship example): there, \"build this ticket / move forward\" means that composite (which runs /work inside it); run /work standalone only on an explicit ask to build without landing. For ticket-sized \"iterate until provably done\", use native /goal instead."
disable-model-invocation: false
argument-hint: "[optional tokens: \"tdd\" force test-first · \"notdd\" skip it · \"nohard\" skip test→mutate hardening · \"noreport\" hand back to an orchestrator; plus optional scope hint]"
---

Run the autonomous chunk-of-work pipeline on the current scope. This is a single-pass structured workflow — orient on the spec, plan + harden the plan, execute, check the build against the spec, harden the tests (/mutate, plus /test when the diff has none), super-review, triage the findings, report — in order, no yielding between them, ending with /report. Three phases are context-aware and self-skip on trivial scopes: the spec freeze, the plan phase, and the test-hardening phase.

**Hard contract: this skill ends with /report emitting its status block (verdict, status table, Next checklist). If you stop before /report fires, you have NOT completed the skill.** Most common failure mode: a phase returns a finished-looking block and you write a turn-ending wrap-up. Don't. That block is mid-workflow — your very next move is to act on it, not to yield.

**Check the entry point first.** If the project has a ship-class composite (`/ship` in the skill registry) and nothing asked for build-without-landing, stop and invoke that instead; it runs this skill as its build leg. (Under `noreport` the composite is already the caller, so skip this check.) Standalone `/work` is the exception, not the default.

**If a chained skill isn't installed**, run its phase inline by hand to the same bar and say so in one line (e.g. `Harden: /mutate not installed — mutated inline`). The phases and their evidence lines are the contract; the skills are how they're usually run. Never skip a phase silently because its skill is missing.

**Exception — orchestrated runs (`noreport`):** when an outer skill drives `/work` and owns the final report itself (e.g. `/ship`), it passes `noreport`. Then `/work`'s terminus is `/super-review`'s recap (step 5), not `/report` — hand-back mechanics in step 6.

## Argument parsing

`$ARGUMENTS` — tokens are matched anywhere in the args; the remainder is a scope hint:
- `tdd` → force the Execute phase test-first (step 3 drives via `/tdd`), even where the default would skip it.
- `notdd` → build free-form, skipping `/tdd` even for a behavior change.
- `nohard` (or `fast`) → skip the test-hardening phase (step 4). It's default-on for non-trivial scopes; this opts out.
- `noreport` → skip the terminal `/report` (step 6) and end after `/super-review`'s recap, handing control back to the caller. For when an orchestrator (e.g. `/ship`) drives `/work` and owns the final report itself. Default off — standalone `/work` always ends with `/report`.
- Anything left over is a scope hint — narrow the work to that slice, and pass it through to `/tdd` when that phase runs.

## The workflow

### 1. Orient — find or freeze the spec
Identify the scope from conversation context (and the scope hint from args, if any). Then find its **spec**, the agreed intent the whole run is measured against. Any intent the user already ratified counts, wherever it lives. Look in this order: a `🔒 FROZEN SPEC` comment, then a `spec-*` memory; a handoff named in the args; the ticket's description and acceptance criteria (where a feature-intake skill's spec lands when `/ticket` files the ticket, if your project has one); a scope the user approved in this thread. Where two disagree, the newer ratification wins: a narrowing the user gave in this thread beats the ticket's older criteria.

- **Found** → it's the requirement. The plan is built from it (step 2), and the build is checked against it (step 3b). Don't re-freeze it: approving what the user already approved is not a reason to halt.
- **None, and the scope is non-trivial** (no ratified intent anywhere) → invoke **`/spec`**. It freezes the intent from this thread and ends on its approval question. **That approval is this step's one allowed pause.** It replaces the single sharp question, because /spec's coverage pass asks whatever is genuinely open. Resume at step 2 on the user's go-ahead.
- **None, and the scope is trivial** (a one-line fix, copy, config) → no spec. A frozen spec for an href edit is ceremony.

Print the outcome as evidence: `Spec: <frozen comment | memory path | handoff path | KEY description | this thread> | frozen now — <where> | none — trivial scope`.

If the scope itself is genuinely unclear and no spec is being frozen, ask ONE sharp question and pause once. Don't accumulate clarifying questions; one is the cap.

### 2. Plan + harden — context-aware (skip for trivial scopes)
This phase catches real problems *before* execution, while they're cheap. It is **context-aware: don't ceremony-plan a one-line copy change.** Apply it when the scope is non-trivial — multiple files, a migration, an architectural choice, sequencing across phases, anything you'd want a second pair of eyes on. For a trivial mechanical change, note "scope trivial — skipped planning" and go straight to Execute.

Three moves:

**a. Get a plan on the table.** With a spec, every in-scope item maps to a phase, and the Deferred list bounds what the plan may touch. If a plan already exists in context — the user drafted one in Plan Mode, or either of you sketched one earlier this session — use *that*; do **not** re-plan from scratch. Otherwise draft a short phased plan now (the phases, their order, the risky steps). Tight working plan, not a document.

**b. Harden it — `/review-plan`.** Invoke `/review-plan` to pressure-test the plan: hidden assumptions, sequencing/blast-radius/reversibility risks, missing prerequisites, plus a set of decision questions. **Pass the full plan as the call's argument** (phases, files, risky steps, ticket, and the spec's location as step 3b passes it, so it can flag a phase that drifts from the spec), with any focus area after it — the fork sees only its arguments, not this conversation. It runs in a fork and returns its report as a result, so it doesn't end your turn.

**c. Resolve what it surfaces, then fold it back into the plan.**
- **Plan defects** (a wrong assumption about the code, a missing verification step, an unguarded one-way door) → fix the plan directly.
- **Decisions** (`/review-plan`'s "Decisions for the caller", stacked trade-offs) → for each, make the call yourself (step 3's Decision line) and fold it into the plan. Do **not** dump the review's questions back at the user and yield.
- **Genuine user-only calls** — irreversible/high-stakes actions, business-judgment calls, or a decision you truly can't make without more info — are the one allowed pause here (same spirit as step 1's single sharp question and /super-review's pause-on-critical). Surface only those, get the answer, resume. Don't let a routine decision masquerade as user-only to dodge the autonomy contract.

Then proceed to Execute with the hardened plan.

### 2.5 Riders: the repo's FINDINGS.md (runs even when step 2 was skipped)
`FINDINGS.md` at the repo root is where `/triage` logs real findings nobody will schedule. Opening the same code makes one cheap, so grep it for the files and behaviors this scope touches. A hit that passes `/triage`'s fold test (its §2a: same file or behavior class, testable, no cross-repo contract, doesn't more than double the diff) becomes a **rider**: add it to the plan, fix it in this diff, and **delete its entry in the same diff**. Riders share one budget: together they must not more than double the scope's own diff, so the PR still reviews as one change. An entry with an open domain question stays put.

This step only reads entries and deletes the ones it fixes. It never adds or rewrites one, even for a problem spotted while fixing a rider: that is a step 5b candidate like any other.

Print `Riders: <N, each entry's heading> | none` (no file → `none`).

### 3. Execute
Drive the work to feature-complete.

**Default: test-first.** When the scope changes behavior through a testable seam (bugfix, logic, resolver/API, data transform, validation) — or `tdd` was passed — invoke `/tdd` with the scope hint and build through its loop. It runs inline, so its work stays in this context.

**The red gate is checked here, whether or not `/tdd` loaded.** Before the first edit to non-test code, print this line with the run behind it:

```
RED: <test file>::<test name> — <assertion> — <failing output line>
```

No RED line, no implementation edit. If the test won't go red, or goes red for a different reason than the hypothesis, the diagnosis is wrong: loop back, don't pause. Re-diagnose (`/debug` when the cause is unknown), re-run the red, and resume; only a cause `/debug` can't find becomes a halt, carried in the report. Then implement to green and continue into step 4.

Build free-form only for UI layout, copy, config, docs, pure refactors, or `notdd`, and say so in one line: `Build: free-form — <why>`.

**Decisions: make the call yourself, then act.** Wherever you'd be tempted to stop and ask — a vendor pick, an architecture trade-off, an ambiguous requirement, stacked open questions — write one line, then act on it in the same turn:

```
Decision: <the call> — because <the one-line why>
```

You're closer to the context than the user is. The next thing after a Decision line is the action, never "proceeding with X?". Trivial choices (naming, helper placement, import order) get no line — just pick. Steps 2c and 5 use this same contract; the only reasons to halt are an irreversible or high-stakes action, a business-judgment call, or a decision you genuinely can't make without more information.

### 3b. Check the build against the spec — /spec-check
Runs whenever step 1 found or froze a spec; skipped when it printed `Spec: none`. Invoke **`/spec-check`** with the spec location plus `diff: <worktree path> <base ref>`. Pass the source step 1 printed as something the fork can read itself: the ticket key, memory path or handoff path, or, for a scope approved in this thread, the user's approving words quoted verbatim (with the ticket key too when the approval narrows a ticket). A paraphrase written after the build would grade the build against itself. The fork sees only the spec and the code, so it isn't swayed by the reasoning that produced the build. It returns a `### Spec-check Recap`.

It runs here, before hardening and review, because a gap is **unfinished work**. Building it now means `/mutate` and `/super-review` see the complete diff, not a diff that grows after its review. Route the recap:

- **Gaps `[caller-resolvable]`** → build them (through `/tdd` when behavioral) and re-run `/spec-check` once. A gap that survives the second run is carried to the report, not looped on.
- **Gaps `[needs-user]`** → a decision the spec doesn't contain, blocking in-scope work. **Ask now**; a blocked prerequisite is a legitimate halt. Carrying it forward would harden and review an incomplete diff, then force a second full cycle to finish it. Build the answer, re-run `/spec-check`, continue.
- **Built-differently items** (divergences from the spec) → **you decide each one; never halt, never ask.** You hold the context the fork was denied, and the user doesn't: asking them to approve a call you already know the answer to is not a reason to halt. Keep it as built when it was a reasoned call the build needed; fix it back to the spec when it's scope creep or a shortcut. A step 2.5 rider is a declared fold, not scope creep: keep it. Print a `Decision:` line for each (step 3's contract). The one exception is a divergence that encodes **a business rule no owner has confirmed** and that no ticket, code or source settles. Carry that one as an open question in the report. It still doesn't stop the pipeline, because the prod gate is where the user looks anyway.
- **QA walk items** → carry to the report. The land-leg's browser pass walks them.
- **🛑 can't verify** (no readable spec, or a required source's MCP is down) → carry it as `Spec: unverified — <why>`, never halt. A check that couldn't run says nothing about the build, so an orchestrator reads it as a completed phase with an unverified result, not an unfinished one.

### 4. Harden the tests — /mutate, plus /test when the diff has none
Default-on for non-trivial scopes; **skipped if the `nohard`/`fast` token was passed**, and self-skips when the diff is trivial (docs/copy/styling/config/type-only).

- **`/test` — only when the diff arrived without tests.** Check with `git status --porcelain`, which lists untracked files too (`/work` never commits). If source files changed and no test path did (`*.test.*`, `*.spec.*`, `*.cy.*`, `__tests__/`, `tests/`, `test_*.py`, `*_test.go`), invoke `/test` to audit the coverage gaps and add the missing tests. Otherwise skip it and say so: `Harden: /test skipped — diff carries <N> test files`. A `/tdd` build always carries tests, so this skips there by construction.
- **`/mutate` — always.** It proves coverage *bites*: injects realistic failure modes and writes tests to kill any that survive, which closes the gaps `/test` would have found.

Fold the outcome forward: if `/mutate` surfaces a **latent bug** (current code already wrong) or a real gap it couldn't close, carry it into /super-review's view and /report's Next — don't silently drop it.

### 5. /super-review
Invoke `/super-review` with the scope (plus the worktree path and base ref when the diff isn't in cwd) — it runs in an isolated fork (code-review passes → recall sweep → conditional `/blast-radius` → conditional `/sec-review`) and returns the recap as a result.

**Route the recap by its tags — do not treat "the fork escalated something" as "stop."** Every escalation `/super-review` returns carries a `[caller-resolvable]` / `[needs-user]` tag (and an `introduced` / `pre-existing` origin). Three routes:

- **🔧 fixes owed, or any `[caller-resolvable]` finding** → **you own it.** Make the call (step 3's Decision line), act on it, re-run `/super-review` on the fixed diff, and continue — no yield. This is the same autonomy contract as steps 2c and 3, and it applies here for the same reason: **you are holding the context the fork was denied** (the investigation, the production evidence, the ticket's ratified semantics, what the user already decided this session). A fork that is contractually forbidden to decide is not evidence that a decision is the user's.
- **`[needs-user]`, origin `pre-existing` and not widened** → ⚠️: surface it with `/super-review`'s recommendation, **and keep going**. The hole is live whether or not you land; blocking a green diff on it buys no safety. **Queue the finding as a triage candidate — do not file it here.** `/triage` runs at step 5b, while this diff is still open and folding is still legal; filing straight from this branch is how one worked ticket turns into four unprioritized ones.
- **`[needs-user]`, origin `introduced` or materially widened** → 🛑: this is the real yield. Put the finding in front of the user and let them make the call.

**A return without the `### Super-review Recap` block is a truncated run, not a verdict.** If the fork came back mid-flight ("waiting on pass 1…") or its recap omits a pass it launched, re-invoke `/super-review` with the same scope. Never route on a partial review.

An **untagged** escalation is a `/super-review` contract miss — judge it yourself against the same test ("could I resolve this with what I already know?") rather than defaulting to a stop.

Two rules on the 🛑 yield when it does fire:
- **Check the recap's `Blocker origin` line** before honoring a 🛑 — a pre-existing finding the diff doesn't widen was never a blocker.
- **The yield is a terminus: report and ask in the SAME turn.** Emit `/report` (or, under `noreport`, the hand-back) carrying the finding in full, `/super-review`'s recommended option, and one explicit question — before the turn ends. Never end on a colon or on "let me first verify X"; resolve that fact *before* you start writing, or state the recommendation conditionally and ask anyway.

### 5b. Triage the candidates — /triage

Invoke **`/triage`** with every candidate this run accumulated in one call: `/super-review` escalations tagged pre-existing, things noticed while editing, gaps the harden phase exposed, "we should probably…" asides. **One call with the whole list** — a per-finding call is the bug the skill exists to prevent, because holding one finding you cannot see it is one of four from the same parent.

**This is the only place in the pipeline that decides a finding's fate, and it runs HERE — before the report, before any land-leg — for one reason: this is the last moment folding is still cheap.** The diff is open, CI hasn't run on a final SHA, nothing has been promoted or QA'd. Once a PR is open, `/triage`'s own fold test (its §2a: "the work it rides on is still open") can no longer pass, so every candidate routes to FILE and the skill degrades into a ticket printer.

It decides DEDUPE / FOLD / MERGE / FILE / LOG / ASK / DROP autonomously and acts, under a one-row budget. **It never gates** — fold its report block into step 6's report (or, under `noreport`, into the hand-back). No candidates → say "none" and move on.

**Nothing else in this skill files a ticket.** A `/super-review` escalation, however severe, is a candidate until `/triage` says otherwise.

### 6. /report — the terminus (skipped when `noreport`)
**Default (standalone):** Invoke `/report`. This is the forcing function. Until its status block fires, the workflow is incomplete. The /report block is the last thing this skill emits — no trailing wrap-up after it.

**The Next line names the land-leg, never the composite.** The build is done, so the next step is the project's land-and-verify leg (e.g. the `/qa-and-pr` example, or whatever the registry has). Pointing at `/ship` would rebuild what just finished. No land-leg → name the manual step (commit + PR).

**The report carries step 2.5's `Riders:` line** next to the triage block, and **the spec's outcome**: a `Spec:` line (✅ built to spec, N gaps carried / N built differently, or unverified — <why>). Under it, list each kept divergence as FYI, one plain line on what changed for a user. These are not Next entries, because nothing waits on the user.

**If `noreport` was passed:** do NOT invoke `/report` and do NOT write any terminal status block or wrap-up yourself. `/triage` (step 5b) was your last substantive action. Emit one brief hand-back line re-framing the run as mid-pipeline (_"Build leg done; super-review verdict above. Spec-check: <status · N gaps · N built differently · N QA-walk>. Triage: <N folded · N filed (keys) | none>. Riders: <N | none>. Hand-back, not a stopping point."_), with the Spec-check Recap's Gaps, Built-differently (each with its Decision) and QA walk lists restated under it so the orchestrator can route them, then **continue straight into the orchestrator's next step in the same turn.** `noreport` only fires when an orchestrator is driving, so there is always a next step. `[workaround]` — since step 5 moved to `/super-review` the recap arrives as a tool result rather than as prose you wrote, which is most of what made this seam stall; re-test the hand-off from a ship composite (e.g. the `/ship` example) into `/work` next model generation and delete this if it holds without the reminder.

## Guardrails

- **No commits, no pushes, no PR opens.** /work cleans + reports; shipping is a separate, explicit step.
- **Inner-skill contracts hold.** /super-review's critical-finding gate is preserved, escalated from its fork rather than paused inline.
- **The `Spec:`, `Riders:`, `RED:`, `Decision:`, `Build:` and `Harden:` lines are the evidence a leg ran.** Print them verbatim; a harness audit greps transcripts for them.
- **No browser QA leg.** /work produces *reviewed code* (in-process tests + /super-review); behavioral browser QA was deliberately extracted — it belongs to /qa (or a project ship composite that chains /work → a QA-and-land leg). Don't re-add a /devtools phase here: its server/seeding/browser needs are the land-leg's concern, and a mid-build localhost poke duplicates it. To build *and* browser-QA without landing, run /work then /qa run.
- **The harden phase is default-on with an escape hatch.** Run /mutate on non-trivial scopes unless `nohard`/`fast` was passed, with /test first only when the diff carries no tests. Carry any latent bug or unclosed gap it surfaces into /super-review and /report's Next.
- **The plan phase is context-aware.** Skip it for trivial mechanical scopes; reuse an existing plan rather than re-planning; never let /review-plan's "Questions for the human" become a turn-ending yield — make each call (step 3) and act.
- **`noreport` suppresses the terminal report.** Full rule and hand-back shape live in step 6 — hand-back line, then straight into the orchestrator's next step, never a turn-end. Standalone /work always reports.
- **The spec is the requirement, not a suggestion.** Plan from it, check against it, and decide each divergence visibly (step 3b's `Decision:` lines) rather than silently fixing or blessing it. A changed intent mid-build is a re-freeze via `/spec`, never a quiet edit to what the build is measured against.
- **One pause allowed in step 1**: `/spec`'s approval when a spec is being frozen, or else one sharp question if scope is unclear. The plan phase's genuine user-only calls are the other allowed pause. Otherwise no yields between phases.
- **Don't expand scope.** If you discover problems outside the chunk you were handed, they are triage candidates — step 5b decides their fate. Don't sprawl into fixing them and don't file them yourself. Step 2.5's riders are the one declared exception: already logged, fold-able, and inside a shared size budget.
- **Step 5b is where findings are decided, and its position is load-bearing.** `/triage` runs before the report and before any land-leg, because its fold disposition requires an open host diff. An orchestrator that wants triage later is asking for a ticket printer; if a caller has its own triage step, delete the caller's rather than moving this one.
- **A /super-review escalation is routed, not obeyed.** `[caller-resolvable]` → decide, fix, re-review, continue. Only a `[needs-user]` finding that this diff introduced or widened stops the pipeline. Full routing in step 5.
- **Don't fake completion.** If a phase legitimately can't run (e.g., /super-review escalated a `[needs-user]` finding the user hasn't resolved), record the state in /report and stop there — don't pretend the phase ran.
- Ticket-sized, iterate-until-provably-done scopes belong to native `/goal`, not `/work`.
