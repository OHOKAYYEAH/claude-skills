---
name: super-review
description: "Pre-ship review of the current diff, run in an isolated fork so its recap returns to the caller as a result instead of ending the turn — the review gate inside /work and /postmortem, and inside the project's ship skill if it has one. Native /code-review (1 pass; 2 only if pass 1 found real bugs), a recall-biased /code-review high sweep unless trivial, then /blast-radius on a shared/cross-repo contract surface and /sec-review on a security surface. Applies bounded fixes; escalates real calls as tagged findings; always ends with the Super-review Recap."
disable-model-invocation: false
context: fork
background: false
agent: general-purpose
argument-hint: "[scope hint — include the worktree path + base ref when the diff isn't in cwd]"
---

Run the pre-ship review on the current uncommitted or in-flight changes, **in this isolated fork**, and return the recap to the caller. Do NOT commit or push anything — this is about getting the change clean, not shipping it.

**You see only your arguments, not the caller's conversation.** The caller passes the scope; if the diff isn't in cwd, it passes the worktree path and base ref too (step 1).

**Hard contract: this skill always ends with the Super-review Recap block in step 8**, followed by every escalated finding in full. Triage output, inline-fix reports, and per-pass narration are NOT the recap.

## Why a fork

The recap's `✅ ready to push` is the most turn-ending block in the suite. Inline, the caller reads it as job-done and yields mid-pipeline. In a fork it comes back as a result and the caller keeps going. [workaround — drop the fork when an inline chained skill's terminal block no longer ends the caller's turn]

## Escalate, never pause

There is no one to ask in here. Where a step below finds a real bug, a broken consumer, or a vulnerability, **escalate**: carry it into the recap with the file:line, what's wrong, the options, and **the option you recommend, with why**. The caller is the one talking to the user. Never decide severity for them — but a bare (a)/(b)/(c) with no pick just relocates the load. **Recommend, don't decide.**

**"Escalate" is not "apply nothing."** Escalating a finding and fixing a bounded defect are independent moves: escalate it *and* fix it, and say so in the escalation. Handing back an untouched tree because everything "felt like a judgment call" is a failed run.

**Tag every escalated finding `introduced` or `pre-existing`:**
- **`introduced`** — this diff caused it → **🛑 blocked.**
- **`pre-existing`** — already live, the diff didn't create it → **⚠️**, not 🛑 — *unless the diff materially widens the exposure* (a new field on an already-open surface, a new caller), in which case 🛑 and say in one clause what widened. Blocking a clean diff on a hole that is already live buys no safety.

**Then tag it `[caller-resolvable]` or `[needs-user]` — this tag, not severity, decides whether the caller's pipeline stops:**
- **`[caller-resolvable]`** — the fix is bounded, in scope, and provable from evidence the calling session holds (its diff, its tests, a prod anchor, a sibling implementation). The caller decides, applies, re-reviews, and keeps going. **Most findings land here, HIGH ones included.** An untagged escalation reads as `[needs-user]` and stops a ship, so tag everything.
- **`[needs-user]`** — needs something the session can't obtain: a domain/business-semantics call, release coordination (two repos deploy in lockstep), prod-data risk, or a scope expansion. **These, and only these, legitimately stop a ship.**

Ask "could the caller resolve this with what it already knows?" *before* you write ⚠️. The forked author is forbidden to decide; the tag hands routing back to the party holding the most context.

**The tags set the Status:**
- Any `[needs-user]` → **⚠️ needs your input** (pre-existing) or **🛑 blocked** (introduced/widened).
- Every escalation `[caller-resolvable]` → **🔧 fixes owed** — nothing here needs a human; the caller acts and continues.
- Nothing escalated → ✅.

**Fallback** — if the native `/code-review` can't launch its background fork from in here, run the passes directly yourself (same efforts, same gates), triage as below, emit the recap, and say which path you took.

**If a chained skill isn't installed** (`/blast-radius`, `/sec-review`): do that pass's read inline yourself against the same gate (consumers of the changed surface; the security checklist in step 5b), mark it `inline` in the recap, and never record a skipped pass as clean.

## The workflow

### 1. /code-review pass 1

Invoke the native `/code-review` skill via the Skill tool, **always with an explicit effort level as the argument** (bare `/code-review` reuses whatever level the user typed last — not yours to inherit) and **never `--fix`** — this pass finds and reports; triage and fixes are yours, on step 4's terms. It launches as a background fork and its findings come back as a task notification: **wait for that result before moving on**, and never predict or paraphrase it. At medium effort it fans out into parallel finder angles (line-by-line scan, removed-behavior audit, cross-file tracer, plus reuse/simplification/efficiency/altitude/conventions), verifies candidates, and returns the findings.

**Target the right repo — `/code-review` inherits your cwd and will silently review the wrong diff.** Bare `/code-review <level>` diffs whatever repo the shell is sitting in. In a multi-repo project, or when the work lives in a **worktree** while cwd is the parent checkout, that is not your diff — and the pass returns a confident, well-reasoned review of somebody else's code, costing a full pass before the mismatch is spotted. **Whenever the diff isn't in cwd, pass the explicit worktree path + base ref in the argument, name the files in scope, and say which repo NOT to review** — then confirm the returned findings actually cite your files before triaging them. [workaround — drop when `/code-review` accepts a repo target natively.]

**Scale the effort to the diff, the way step 5 gates on surface.** A trivial diff (copy, styling, hrefs, config-local, type-only) gets `/code-review low` — proportionate, but never *skipped*: this pass is the last inward read before the diff ships, and it's what catches "the small change wasn't small." Default medium for everything else; reach for `high`/`xhigh` only on genuinely gnarly logic. Scaling effort is the right knob here — skipping the pass entirely is not.

Triage as in step 4: verify load-bearing findings against the actual code, apply bounded fixes inline yourself, escalate real bugs or design concerns. The noise floor is real at default effort — refute findings that don't hold up under scrutiny rather than fixing things just because an agent flagged them.

### 2. Decide whether to run another pass

- If pass 1 surfaced **real bugs** that you fixed (not lint, not cosmetic, not refuted-as-noise), run `/code-review` pass 2. One fix often unblocks visibility into another — a fix in pass 1 can expose a second bug that pass 2 catches.
- If pass 1 was clean, found only cosmetic/lint, or its findings were mostly wrong-on-merits, **skip to step 3** (the final sweep). Don't run a second pass on a clean diff just for symmetry.
- Pass 3+ is reserved for the rare case where pass 2 *also* surfaces a real bug. Lint mop-up isn't a reason to keep going — the project's own lint/format command is.

**Carry context between passes.** Pass 2 must be told (a) what pass 1 already fixed, (b) what was refuted as wrong-on-merits, and (c) what was consciously deferred. Without this, pass 2 re-raises the same items and you re-decide them — that re-litigation is where multi-pass time goes.

### 3. Final recall-biased sweep

Once `/code-review` has converged, run **one more `/code-review high` pass**. This is not pass 1 again — it's a deliberate bias flip. Per its effort table, `medium` reviews for **precision** ("every finding you surface should be one a maintainer would act on"), while `high` reviews for **recall** ("catch every real bug a careful reviewer would catch in one sitting… err on the side of surfacing"). Passes 1–2 optimized for signal; this one optimizes for not-missing-anything, which is the right last question to ask before a diff ships.

Gate it on risk, the way step 5 gates on surface:

- **Trivial diff** (copy, styling, hrefs, config-local, type-only): **skip it.** Pass 1 at `low` was already the proportionate read. Say so in the recap.
- **Everything else:** `/code-review high`.

**Carry context in, same as step 2** — what passes 1–2 fixed, what was refuted as wrong-on-merits, what was consciously deferred. A recall-biased pass with no memory of the earlier ones will re-raise every deferred item and you'll re-decide them all.

> `/review` has been a plain alias for `/code-review` since CLI 2.1.223 — same engine, never run both. `ultra` (the cloud multi-agent review) stays user-only: if the diff warrants it, say so in the recap and the user types `/code-review ultra` themselves.

### 4. Triage what the final sweep returns

**Expect a higher noise floor than pass 1.** Recall bias is the point, and the cost of it is more speculative findings. Refute what doesn't hold up against the actual code rather than fixing things because an agent flagged them — a `high` pass that produces six refuted findings and one real bug did its job.

- **No critical issues**: note this and continue to step 5.
- **Small/bounded fixes** (e.g. a wrong comment, a missing type field): fix them inline and report, then continue to step 5.
- **Real bugs or design concerns**: escalate (tagged, with options and your pick), apply the fix too if it's bounded, and continue to step 5.

In all three cases the workflow still ends with the recap in step 8 — never short-circuit out of the workflow at step 4.

### 4b. Comment pass (always runs — it's a grep, not a fork)

The review passes judge whether code is *correct*; none of them judge whether a comment *belongs*. This step enforces a code-comment standard on the way out — why-comments only, at most 3 lines per block, and no change narrative in the code — because a generation-side rule alone doesn't hold: left unchecked, generated diffs drift toward long comment blocks that retell the change. If your project's CLAUDE.md sets its own comment standard, enforce that one instead.

Scan **only comment lines this diff adds** — never pre-existing comments; rewriting those is churn in a shared repo. Flag a block when either is true:

- **It runs past 3 lines** (inside code — docstrings/JSDoc documenting a contract and config-file comments are exempt from the cap, not from the next bullet).
- **It tells the story of the change** — a date, an incident, `used to` / `no longer` / `previously` / `now we`, "the point of this change", a retold ticket. Lint directives and licence headers aren't comments for this purpose.

For each flagged block, apply the bounded fix yourself — this never pauses and never escalates:

- Keep what *stays true* (the trap, the invariant, the business rule) in ≤3 lines; a ticket key stays as a bare pointer.
- Delete what restates the code.
- Cut the story. It isn't lost — it belongs in the commit message / PR description, so name the trimmed blocks in the recap's **Comments** line and whoever writes the commit carries the reasoning there.

Comment-only edits can't change behavior, so they don't reopen the inward passes and don't invalidate step 5.

### 5. Outward-surface checks, then fire both outward passes IN PARALLEL

The `/code-review` passes read the diff *inward* — is the changed code correct? The two outward passes ask different questions about the **same final state of the diff**, and **neither consumes the other's output**. So classify both surfaces here, then launch whichever gates open **in a single message so they run concurrently**. Sequencing them costs a full fork round-trip and buys nothing.

Do **not** pull these forward to run alongside the `/code-review` passes. Step 4's triage can change the diff — an outward pass reading a pre-fix diff is exactly the stale-analysis failure these gates exist to catch. Converge inward first, then fan out.

**a. Blast-radius surface.** Does the diff touch a **shared or cross-repo contract surface**: an exported/public function's signature *or behavior*, a DB column or migration, a GraphQL schema field, a shared config/env var/feature flag, a queue/event message shape, or a shared component's props?

**b. Security surface.** Does the diff touch new/modified endpoints, auth/permission checks, session handling, input parsing, file or URL handling, template rendering, shell/SQL/NoSQL construction, secrets or crypto, or dependency bumps in the auth/parsing/network path?

**c. Launch.** In **one message**, invoke every pass whose gate opened:
- Shared surface → `/blast-radius`. Read-only; runs in an isolated fork and **returns its report as a result**. It enumerates the changed surfaces, fans out to every consumer (in-repo and across sibling-repo seams), and flags the silent same-signature behavior changes the compiler won't catch. Earns its place most on prod hotfixes against old shared code.
- Security surface → `/sec-review`. Read-only; runs the audit in an isolated fork and **returns its report as a result**, so the chain survives. It proves a non-empty diff first and audits every changed file itself — never call the native `/security-review` here: it diffs the session cwd against `origin/HEAD`, committed only, and reviews the wrong change.
- **Neither gate open** (purely-internal, test-only, copy/styling/config-local): skip straight to the recap and say so there. Don't fork either one for symmetry.

Both are forks: their reports come back as results, so you keep control either way. Triage them in steps 6 and 7 as they land.

### 6. Triage what /blast-radius returns

Skip if it didn't run. Three branches:

- **🟢 contained / no at-risk or broken consumers**: continue. The recap's **Blast radius** line *is* the report.
- **⚠️ at-risk consumers / small bounded fixes** (e.g. an obvious caller that needs the new optional arg, a missing null guard a narrowed query now requires): apply the fixes, then describe them in the **Blast radius** line.
- **🔴 broken consumers or a cross-repo contract break**: escalate. A broken cross-repo consumer often means two repos must deploy in lockstep — that's `[needs-user]` release coordination; a consumer fix inside this diff's repos is `[caller-resolvable]`.

### 7. Triage what /sec-review returns

Skip if it didn't run. Three branches:

- **No findings**: continue to the recap. The recap's **Security surface** line *is* the report — don't write a separate "security review was clean" message first.
- **Small/bounded fixes** (e.g. an obvious missing input check, a clearly-wrong CORS header): apply the fixes, then describe them in the **Security surface** line.
- **Real vulnerabilities or design-level concerns**: escalate, tagged, with options and your pick.
- **🛑 could not establish a diff**: `/sec-review` refused because its step-0 check found nothing to review — a tooling failure (usually worktree cwd vs. parent checkout), **not** a clean result. Re-run it with an explicit scope, or run the audit inline. Never record it as a pass.

If `/sec-review` is noisy on routine changes (e.g., dep bumps with mostly false positives), surface that in the recap's Open questions line — the trigger criteria may want dialing back.

### 8. Final recap (mandatory, never skip)

Emit this block exactly. It runs whether `/blast-radius` or `/sec-review` ran or not, whether anything was flagged or not, and whether you already narrated between passes. Without it, the skill has not completed.

```
### Super-review Recap
**Status:** <✅ ready to push / 🔧 fixes owed — caller-resolvable, no human decision needed / ⚠️ needs your input / 🛑 blocked on critical issue>
**Blocker origin:** <none / introduced by this diff / pre-existing — already live (+ what this diff widens, if anything)>

- **Pass 1 (/code-review):** <one line: fixes applied, or "no real bugs">
- **Pass 2 (/code-review):** <one line, or omit if pass 1 was clean / only lint>
- **Pass 3 (/code-review):** <one line, or omit — should be rare>
- **Final sweep (/code-review high):** <skipped — trivial diff / clean / bounded fixes applied inline / critical issues flagged>
- **Comments:** <clean / N blocks trimmed — `file:line` each, + the reasoning the commit/PR body should carry>
- **Blast radius:** <no — skipped `/blast-radius` (no shared surface) / yes — `/blast-radius` ran: 🟢 contained / N at-risk fixed inline / N broken consumers flagged>
- **Security surface:** <no — skipped `/sec-review` / yes — `/sec-review` ran: clean / N bounded fixes inline / critical issues flagged>

**Deferred:** <one line, or "none">
**Open questions:** <one line, or "none">
**Escalations:** <N `[caller-resolvable]` + N `[needs-user]`, or "none" — the caller routes on this line>
**Pass attribution:** <for each REAL finding that survived triage, the pass that first surfaced it — e.g. "intransitive comparator → pass 1; coverage regression → final sweep; none from blast-radius" — or "no real findings">
```

After the block, list **every escalated finding in full**: file:line, what's wrong, both tags, the options, and the recommended one with its why. Never abridge — the caller routes on the tags and has to act on the actual finding.

**Why the attribution line exists:** the recall sweep (step 3) is the single most expensive call in this workflow, and there is otherwise no way to tell whether it has ever caught something passes 1–2 missed — an audit of past sessions can rate the multi-pass strategy as a whole but cannot attribute a single finding to a specific pass. This line is the instrument. One line per run; after a few audit windows it answers whether the sweep's cost is buying recall or symmetry. Attribute honestly, including "the sweep found nothing new" — that datum is the point.

## Guardrails

- **Never commit or push during super-review.** This workflow is strictly about cleaning the change; shipping is a separate, explicit step.
- **Don't touch data files.** Never open or quote customer-data files (`*.csv`, `*.xlsx`, dumps, `*.sql` data scripts, exported reports) — review code and config, not data.
- **Don't over-refactor.** `/code-review` can suggest architectural changes (helper extraction, component unification, etc.) — more so at step 3's `high`, where recall bias surfaces speculative shape-improvements. If a finding reads as "this would be a nicer shape" rather than "this is broken," it's probably out of scope. Mention it in the recap as deferred, but don't unilaterally apply large refactors.
- **Carry context between passes.** Each `/code-review` pass should be told what earlier passes already addressed, what was refuted as wrong-on-merits, and what was consciously deferred — so it doesn't re-raise the same items.
- **Wait for each review's task result.** Native `/code-review` runs in the background and the harness re-invokes you when it finishes. Don't start the next step, and never invent findings, until its notification lands.
- **In this fork, ending your turn IS returning.** A final message like "now waiting on pass 1" hands the caller a half-review that looks finished. While any pass you launched is still pending, keep going: block on it, or run that pass inline via the Fallback. Before the recap, check that every launched pass has a result. [workaround — drop when a fork's turn-end reliably waits on its own background tasks]
- **One fork at a time late in a session.** The high sweep (step 3) and `/blast-radius` (step 5) each fan out; launched concurrently on a long session they can both hit the session limit and die with partial angle reports. Launch them sequentially, and relaunch a rate-limited pass rather than triaging what one surviving angle returned. [workaround — retire when a rate-limited fork resumes instead of dying]
- **Typecheck after each pass** if the project has a typechecker (e.g., `npx tsc --noEmit`). Cheap insurance against introducing regressions.
- **Blast radius and security are gated, not always-on.** Both `/blast-radius` and `/sec-review` (step 5) run only when the diff touches their respective surface, and when both gates open they launch **in parallel in one message** — they are independent reads of the same final diff. A trivial copy/styling/config-local change skips both; don't fork them just for symmetry.
- **Step 1 scales, it never skips.** Step 1's effort tracks the diff (`low` on trivial, medium default) — but that pass always runs; it's the one read that must never go blind. **Step 3's recall sweep is the opposite:** it's *gated* like `/blast-radius` and `/sec-review`, and a trivial diff skips it outright.
