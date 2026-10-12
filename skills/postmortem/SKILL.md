---
name: postmortem
description: >-
  Retroactively apply the build-time quality gates (/work's, or a project ship
  skill's) to work that bypassed them. Detects whether it already SHIPPED to prod (live-remediation backlog) or
  is BUILT-BUT-UNSHIPPED (pre-ship fix list); runs the deferred gates (test
  hardening + /super-review), asks band-aid vs root cause, and for live
  incidents whether the trigger can recur. Fire on "postmortem this", "this
  shipped without the gates", or after any prod hotfix. NOT /super-review
  (already-gated work) or /debug (cause unknown).
disable-model-invocation: false
allowed-tools: Bash(git status*) Bash(git log*) Bash(git diff*) Bash(git branch*) Bash(git show*) Bash(git rev-parse*) Read Grep Glob
argument-hint: "[optional scope — commit range / PR# / branch / \"the working tree\" / incident note]"
---

Retroactively run the quality standards that `/work` (or the project's ship skill, if it has one) would have enforced, on a chunk of work that **skipped them**. This is the inverse of the build-time gates: instead of "should we ship this?", it asks "the gates got skipped — run them now, and tell me what to do about it given where the code already is."

**Hard contract: this skill always ends with the Postmortem Recap block in step 7.** Per-gate output, inline-fix reports, and reconstruction narration are NOT the recap. If you stop before emitting step 7, you have not completed the skill.

## Two modes — detect, don't assume

The same work-skipped-the-gates problem shows up in two shapes. The skill handles both; the difference only changes (a) how hard the forensic step is and (b) the shape of the verdict.

- **SHIPPED** — the work is merged to `main` *and* live on prod (classic: a prod hotfix pushed fast under fire). The gate is moot — it already shipped. Verdict = a prioritized **live-remediation backlog**, and the forensic step is real work (the fix may be N commits deep, in a different session's history). Recurrence risk matters.
- **UNSHIPPED** — the work is built but not yet live: uncommitted working tree, a branch not merged, or on `main` but not deployed. Often a session that iterated real code without ever invoking `/work` or a ship skill. The gate is still live — verdict = a **pre-ship fix list**, and bounded fixes can be applied inline (as in `/super-review`) before it ships.

State the mode you inferred and *why*, in one line, early — so it can be corrected before the deep work runs.

## The workflow

### 1. Determine scope + mode

**Scope (what code is under review):**
- If `$ARGUMENTS` names a commit range, PR#, branch, file set, or "the working tree" — use that.
- Otherwise infer from git state, in order: uncommitted working-tree changes (`git status`), then commits on the current branch ahead of base (`git log <base>..HEAD`), then — if neither and the context points at already-merged work — the relevant commits on `main`.
- **If genuinely ambiguous** (e.g. both a dirty tree *and* branch commits, or you can't tell which commits are the chunk), ask **one** sharp question to pin it. Don't guess at scope — everything downstream is scoped to this.

**Mode (shipped vs. unshipped):**
- **Unshipped** if the changes are uncommitted, on a branch not merged to `main`, or on `main` but not yet deployed.
- **Shipped** if the relevant commits are on `origin/main` **and** live on prod. Confirm deploy state using the project's own mechanism (read the project `CLAUDE.md` for the deploy model — e.g. push-to-`main` → a platform auto-deploy, verifiable via that platform's CLI status/inspect command). On `origin/main` but the deploy hasn't landed yet = still unshipped.

Whatever you infer, **scope every downstream gate to the reconstructed work explicitly** (e.g. "review commits `abc..def`" / "the changes in these files") — the gates default to "the current diff," but a postmortem often runs on historical commits or in a fresh session, where "current diff" is wrong.

### 2. Reconstruct what happened / what was built

Before judging the work, establish what it *is* — a fresh session won't have it in context.

- **Read the actual change** (`git show` / `git diff` over the scoped commits; read the touched files).
- **If it was an incident hotfix (shipped mode):** capture the short narrative — trigger, symptom, what the fix did, and **whether the incident is actually resolved or still in progress**. (External-vendor triggers especially: the fix may have stopped *our* symptom while the upstream cause is still live.)
- **If it was just feature/iteration work (unshipped mode):** capture what it does and the approach taken — enough to judge whether the design is sound, since no `/review-plan` gate ran before it was built.

Keep this to a tight paragraph. It feeds the recap's "what happened / was built" line.

### 3. Run the deferred gates (the heart)

Run the two quality halves `/work` would have run, scoped to the reconstructed work. Order mirrors `/work` (harden tests first, then review the final state including the new tests).

**3a. Test-coverage harden.** Did the work add tests for its changed logic? If there's a real gap, invoke `/test` on the scoped change. If the changed logic is bug-magnet territory (math, parsers, validators, money/quantity arithmetic, state machines, anything with off-by-one / sign / boundary risk), also invoke `/mutate` to prove the suite actually catches regressions. Adding tests is safe in **both** modes — for shipped code it's a retroactive safety net that doesn't touch prod behavior; for unshipped it's the coverage the build skipped. If the test seam genuinely doesn't exist (e.g. browser-only behavior), note the gap and move on rather than forcing it.

**3b. `/super-review`.** Invoke `/super-review` on the scoped change — it runs in a fork and hands its recap back as a result instead of ending the turn. It fans out `/code-review` → a recall-biased `/code-review high` sweep (unless the diff is trivial) → `/blast-radius` (if the change touches a shared/cross-repo contract surface) → `/sec-review` (if it touches a security surface), and returns its own recap. **This is where blast-radius and security get covered** — don't re-run them separately. `/blast-radius` earns its place most here: a prod hotfix against old shared code is exactly the change where a quiet downstream consumer is easiest to miss.

Carry the reconstruction context into these so they understand they're reviewing *after-the-fact* work, not a normal pre-ship diff.

### 4. Adversarial lens — the corners a fast/skipped build cuts

Beyond the generic gates, ask the questions that only exist *because* the gates were skipped. These are the postmortem's reason for being:

- **Band-aid vs. root cause.** Was this the real fix, or the fastest stop-the-bleed with the durable fix deferred? A deferred durable fix is an **open recurrence vector** — name it and it becomes a remediation ticket.
- **Design/approach sanity (esp. unshipped).** No plan review ran. Is the approach sound, or did it drift into a shape that should be reworked *before* it ships? You can't un-build, but you can flag "rework before shipping" while it's still cheap.
- **What did skipping the gates cost?** Missing tests (covered in 3a), unconsidered blast radius (covered in 3b), no error-path handling, a TODO left in a hot path, a hardcoded value that should be config. Enumerate the specific debts, not a generic "it was rushed."

### 5. Recurrence / residual-risk assessment

The one thing no diff-review ever asks — and the highest-value output in shipped/incident mode.

- **Shipped + incident:** Is the trigger still live? What's the recurrence window, and what happens if it fires again before the durable fix lands? (E.g.: "vendor still erroring → tonight's post-close write fails too → tomorrow morning the symptom returns → manual backfill needed again.") Be concrete about *when* and *what breaks*.
- **Shipped, no incident:** What's the residual risk of the change as it sits live — any silent behavior change a consumer hasn't hit yet?
- **Unshipped:** This collapses into the ship/no-ship risk — "what's the risk of shipping this as-is," which the gates above largely answer. Note anything they didn't.

### 6. Verdict + remediation backlog

Synthesize into a mode-appropriate verdict and a concrete backlog.

- **Unshipped → pre-ship fix list.** Bounded fixes already applied inline (note them); anything larger framed as "fix before landing." Recommended next step is usually the project's ship skill if it has one, else its normal land step (or `/work`'s harden phase if substantial rework is needed).
- **Shipped → live-remediation backlog.** Prioritized list: the deferred durable fix, any coverage/blast-radius/security gaps, and recurrence mitigations. **Do not push fixes to prod as part of the postmortem** — diagnose and draft; let the human drive the actual re-ship (e.g. via the project's ship skill). Inline edits to *unshipped* working-tree code are fine; silently re-shipping prod is not.
- **Tickets:** discover the project's tracker from its `CLAUDE.md` (e.g. a Jira project via the Atlassian MCP). **Draft** the remediation items as proposed tickets in the recap and file them on the user's go — don't auto-file into a tracker (wrong-project / noise risk), but make filing one confirmation away.

### 7. Postmortem Recap (mandatory, never skip)

Emit this block exactly. It runs whether the change was clean or not, in either mode, regardless of what the gates found. Lead with the glanceable verdict; defer detail below it. Without this block, the skill has not completed.

```
### Postmortem Recap
**Mode:** <SHIPPED — live on prod / UNSHIPPED — built, gates skipped>
**Verdict:** <one glanceable line — e.g. "SHIP-OK after 1 inline fix" / "SHIP-BLOCKED: real bug, see below" / "LIVE-CLEAN, 1 recurrence watch" / "LIVE-NEEDS-REMEDIATION: 2 tickets">

- **Scope:** <what was reviewed — commits / branch / working tree>
- **What happened / was built:** <one-line reconstruction>
- **Test harden:** <coverage added (/test, /mutate) / already covered / gap deferred — why>
- **Super-review:** <clean / N fixes applied inline / N flagged — folds in code-review, review, blast-radius, security>
- **Root cause vs band-aid:** <addresses root cause / band-aid — durable fix deferred → ticket>
- **Recurrence / residual risk:** <n/a (unshipped, no incident) / trigger resolved / TRIGGER STILL LIVE — recurs <when> unless <action>>

**Remediation backlog:** <numbered list, or "none"> — <"drafted — say the word to file" / "filed <KEY>-NNN…">
**Recommended next:** <e.g. "land + verify via the project's ship skill" / "do the durable-fix ticket next" / "/compound the process lesson — why the gates got skipped">
```

## Guardrails

- **Detect the mode, state it, let it be corrected.** Announce "looks SHIPPED/UNSHIPPED because <reason>" early; don't sink deep work into the wrong framing.
- **Scope the gates to the reconstructed work, not "the current diff."** Postmortems run on historical commits and in fresh sessions — pass the explicit commit range / file set into `/test`, `/super-review`, etc.
- **Read-only on prod.** For shipped work, the postmortem diagnoses and drafts remediation — it does **not** re-ship a fix-on-top. Inline cleanup of *unshipped* working-tree code is fine (same as `/super-review`); pushing to prod is a separate, explicit human-driven step.
- **Don't auto-file tickets.** Draft the backlog; file on confirmation, into the tracker the project's `CLAUDE.md` names.
- **This assumes the fix/work is in hand.** If the *cause* of an incident is still unknown, that's `/debug` first — postmortem starts from a fix or build that already exists.
- **`/compound` is a recommended follow-up, not auto-chained.** The process lesson ("why did this skip the gates, how do we prevent it") is worth codifying, but `/compound` mines the *current* session and a postmortem may run fresh — so surface it as the next step, don't run it blind.
- **Generic, not project-locked.** Works in any repo with the review-skill suite. Deploy-state detection, the prod URL, and the ticket tracker all come from the project's `CLAUDE.md` at runtime — never hardcode one project's specifics.
- **Missing chained skills degrade, not block.** If `/test`, `/mutate`, `/super-review`, `/blast-radius` or `/sec-review` isn't installed, run that gate inline by hand at the same bar (or note it as skipped in the recap) — never report a gate as passed that didn't run.
