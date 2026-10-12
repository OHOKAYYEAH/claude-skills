---
name: qa
description: Draft a behavioral browser-QA scenario list for the current scope of changes — golden path, edges, error paths, regressions, cross-cutting concerns. Pairs with /devtools as the execution primitive; `/qa run` drafts then immediately walks the list, plain `/qa` drafts and stops so the list can be run later or used as a manual checklist.
disable-model-invocation: false
argument-hint: "[optional focus] [optional \"run\" to execute] [optional target: local|dev|stage|staging|prod or a URL — implies run]"
---

# QA Scenario Pass

Draft a robust set of behavioral QA scenarios against the current scope of work — the kind of list a thoughtful human would walk through to confirm the change actually does what it's supposed to, doesn't break adjacent flows, and degrades sensibly on bad input. Optionally execute the list in the browser via `/devtools`.

This skill owns the **drafting** side of QA — figuring out *what* to verify. The execution primitive (driving the browser, taking snapshots, watching console + network) is `/devtools`. `/qa run` chains the two; plain `/qa` produces a paste-able checklist you can run later, hand to someone else, or use as the basis for a future Cypress test.

## Argument handling

`$ARGUMENTS`:

- **`run`** or **`execute`** as a token → after drafting, immediately invoke `/devtools` to walk the scenarios.
- **A target token** (`local` / `dev` / `stage` or `staging` / `prod`) or a raw URL → the environment to run against, and it **implies `run`**: a target only means something if the list gets walked. Pass it through to `/devtools`. If absent, `/devtools` resolves the target itself (explicit > session context > local).
- **Anything else** → focus hint. Narrow drafting to that slice (e.g., "the new modal", "the redirect bug", "the checkout form").
- **Combined** ("run the new modal on dev") → narrow scope, run, against dev.

Default scope (no argument) is uncommitted changes + commits ahead of the upstream branch — same default as `/test` and `/code-review`.

The user's argument: `$ARGUMENTS`

## Step 1: Identify scope and decide whether to run

Identify the diff (default: uncommitted + ahead-of-upstream; narrow if args supplied a focus).

**Stop and redirect only when nothing the change does reaches a screen:** config, docs, test-only, dependency bumps, or backend code no page calls. The test is reachability, not file type — a backend change a page renders (a resolver, a field, a validation rule) is in scope: draft against the screens that call it. So is any styling or layout change.

Output: "No UI surface in this diff — `/qa` is for browser-QA scenarios. Consider `/test` for in-process coverage." …and stop.

Against a deployed env, scope is the merged change the args name, not the local tree.

## Step 2: Draft scenarios

Generate as many scenarios as the change warrants — no more, no fewer. A one-line copy tweak might need a single scenario; a new feature-sized flow might need fifteen. The bar: every scenario should pay rent. If you wouldn't bother running it, don't list it. If a meaningful path is uncovered, add it even if the list is getting long.

**Cover these dimensions** — skip a category outright if it genuinely doesn't apply, but don't skip *because it felt hard*:

- **Golden path.** The intended happy flow. What the user is most likely to do, working as designed.
- **Edge cases.** Empty input, max size, zero/negative, single-element, unusual entry routes (deep links, refresh mid-flow), back-button behavior.
- **Error paths.** Network failure, validation rejection, permission denied, 500 from a dependency. What does the user see when things go wrong?
- **Regression risks.** Adjacent flows that share code paths, state, or UI surface with the change. Could they break silently? Don't guess at adjacency — derive it: grep which routes/screens render (not merely import) the changed components/hooks/stores and draft from that consumer list. If a `/blast-radius` consumer map is already in session context, use it as the list.
- **Cross-cutting.** Auth states (logged out, wrong role), viewport (wide ~1900px for any table/grid layout; mobile if the app supports it), browser refresh mid-state, deep-link entry to a partial flow. A role-gated flow runs as the gated role *and* as one without it — an admin passes every gate, so it proves nothing about one; use the project's role-scoped test users.
- **Data variations.** Different user roles, different data shapes — anything where a code branch depends on input characteristics.

**Each scenario must include:**

- **One-line statement** — behavioral, not implementation. ("User submitting empty form sees inline validation" ✓ — "submit handler returns 400" ✗.)
- **Steps** — 3–7 concrete actions a human or `/devtools` can walk through. Concrete enough that you don't have to think mid-execution.
- **Expect** — the observable outcome. UI state, message, navigation, network call shape — something a watcher can confirm. For a write, the persisted record read back (reload or DB), not the UI's optimistic state.

**Quality bar:**

- **Behavioral, not mechanical.** A scenario should describe what a user observes, not what a function returns.
- **Realistic data.** Use plausible-looking inputs from the project's own domain — real-looking ids, dates, amounts, and formats (a plausible SKU, a realistic order number), not `"foo"`/`"bar"`. Realistic data catches real bugs.
- **Single concern per scenario.** "Submits empty form AND sees error AND form clears AND focus returns" is four scenarios in a trench coat. Split.
- **Mutation-test mindset.** If you changed `>` to `>=` in the code under test, would any scenario notice? If no, the scenarios are too loose.
- **Don't invent fake assertions.** If a flow requires a backend you can't reach, list it anyway as a scenario to run when reachable — don't substitute a hand-waved version that "checks the same thing."

## Step 3: Present the list

Output as a paste-able checklist. Categories are short tags: `Golden`, `Edge`, `Error`, `Regression`, `Cross-cutting`, `Data`.

```
### QA Scenarios — <one-line scope>

- [ ] **1. Golden: <one-line statement>**
  - Steps:
    1. <step>
    2. <step>
  - Expect: <observable outcome>

- [ ] **2. Edge: <one-line statement>**
  - Steps: …
  - Expect: …
```

After the list, two short sections:

- **Assumptions** — what you took as given about scope, data, or environment. One line each.
- **Deferred coverage** — flows you considered but excluded, with a one-line "why not now."

## Step 4: Execute (only if args enabled `run` / `execute` or named a target)

If args included `run`, `execute`, or a target, invoke `/devtools` with the scope hint, **the target env** (if one was given), and the scenario list as context — e.g. `/devtools the checkout form on dev`. `/devtools` resolves the target (explicit > session context > local), handles availability gates (MCP loaded, target reachable, `:9222` running), and reports back.

If `/devtools` reports 🛑 unavailable, surface that and stop — don't fake the verification. The drafted list still has value as a manual checklist.

Any frame or rendered output the pass produces lands where `/devtools` puts it — a git-ignored local evidence dir (e.g. `docs/local/<ticket>/` in the main checkout, never a linked worktree, which deletes ignored files on removal), never the repo root. QA frames can carry real customer data, so they never get committed.

If `/devtools` surfaces issues:

- Fix trivial slips inline (single-line text, obvious typo, clear logic error).
- Defer larger findings to a follow-up — don't sprawl mid-pass.

Output a final pass/fail summary per scenario:

```
### QA Pass — <scope> · <target>

- ✅ 1. Golden: <statement>
  - Observed: <route> · <API operation: REST URL or query name, read from the screen's code> · <record used>
- ✅ 2. Edge: <statement>
- ⚠️ 3. Error: <statement> — <introduced | pre-existing (reproduces without the change)> — <one-line issue, file:line if known>
- 🛑 4. Regression: <statement> — <couldn't run, reason>

**Issues fixed inline:** <list or "none">
**Outstanding:** <list or "none">
**Frames:** <absolute paths /devtools reported, or "none">
```

The `Observed` line and `Frames` carry what callers can't re-derive once the browser is gone — an E2E spec written later needs the API operation, a before/after sheet needs the frames.

If args included neither `run` nor a target, stop after Step 3. The list itself is the deliverable.

## Guardrails

- **Drafting is the unique value.** Even if the list is never executed, it should stand on its own — a reader should understand what to verify and why from the list alone.
- **Stay scoped.** Don't draft scenarios for flows outside the diff. If something adjacent looks fragile, note it under "Deferred coverage" — don't expand.
- **Reproduce before patching.** During Step 4, if a scenario fails, confirm the failure cleanly before reaching for a fix. Don't pattern-match a fix from a symptom.
- **Test users only.** Never auth real / production accounts. If a scenario requires real auth, surface it under Deferred coverage.
- **No commits, no pushes, no PR opens.** This is verification, not shipping.
