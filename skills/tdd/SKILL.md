---
name: tdd
description: >-
  Test-first build: write the failing test (or repro) first, confirm it fails
  for the hypothesized reason, then implement to green; a cause that can't
  produce a red test is wrong. Use by default before a bugfix or behavior change
  with a testable seam; falls back to a /devtools browser repro. NOT /test
  (coverage on existing code), /mutate, or /debug (cause still unknown).
disable-model-invocation: false
argument-hint: "[what you're about to build or fix]"
allowed-tools: Bash(git status*) Bash(git diff*) Bash(git log*) Bash(git grep*) Bash(npx jest *) Bash(npx vitest *) Bash(npm test *) Bash(yarn test *) Bash(pnpm test *) Bash(pytest *) Bash(go test *) Bash(cargo test *) Bash(grep *) Bash(rg *) Read Edit Write
---

You are building **test-first**: the test (or a reproducible failure) comes *before* the implementation. You write something that fails, prove it fails **for the reason you think it does**, then write the code that makes it pass.

## Why test-first, not test-after

The red-first step is a **forcing function that catches a wrong diagnosis before you waste a fix on it.** You cannot write a test that fails *for reason X* if X isn't the real cause — the attempt itself falsifies a bad theory. The classic trap it prevents: confidently "fixing" code that was never the problem (e.g. editing a normalizer that turns out to be inert — a no-op change shipped against a false premise). Test-after can't catch this; by then you've already committed to the implementation.

So the gate below ("red for the *right* reason") is the whole point of the skill — not ceremony.

## When this fires vs. its siblings

- **`/tdd`** — you're *about to* write a fix or feature and want the test to drive it. ← here
- `/test` — code already exists; audit it for missing coverage and add tests.
- `/mutate` — harden an existing suite by injecting hypothetical bugs.
- `/debug` — the cause is still unknown; systematic diagnosis that ends by handing its confirmed cause to /tdd's step 1.

Highest value on **bugfixes**, and on **risky/old/load-bearing code** where "I'm nervous to touch this" is the right instinct.

## The loop

### 1. Pin the behavior precisely

- **Bugfix:** state the exact symptom (what's observably wrong) *and* your hypothesized cause (which line/condition produces it). Vague — "the form breaks" — isn't pinnable; "reopening the settings form unchecks the toggle because the saved value arrives as the string `"true"` and the widget expects a boolean" is.
- **Feature:** state the contract — input → expected output, the boundary cases, the error behavior.

### 2. Pick the red medium

- **In-process logic** (backend, pure functions, parsers, math, reducers, API contracts) → a **unit test**. Hold it to `/test`'s quality bar (one concern, named for the property, realistic fixtures, visible Arrange/Act/Assert). You may invoke `/test` to author it.
- **UI / no in-process test seam** (component renders, form widgets, browser-only behavior) → a **live repro via `/devtools`**. Don't invent render-test infrastructure to force a unit test — that's a separate, deliberate decision (same boundary as `/test`).
- **Process-level / native failure** (a C-extension `assert()` that SIGABRTs, a segfault, a deadlock, an OOM) → a **repro script driving the REAL dependency**. The mocked suite is *structurally blind* here: an `abort()` is not an exception, so no assertion can observe it — and if a test double stands in for the very library that dies, green is guaranteed and meaningless. **Mock the slow or irrelevant parts; never mock the thing that crashes.** (Example: a native audio library's `assert()` can kill the app on every rapid restart while a fully mocked suite stays green; a repro against the real library reproduces it on demand — exit 134 before the fix, clean runs after.)

### 3. Establish RED — and gate hard on the reason

Run the test / drive the repro. It must **fail, for the reason you hypothesized in step 1.**

- ✅ Red for the right reason (the assertion catches the exact wrong value / the repro shows the exact symptom) → proceed to implement.
- 🛑 **It won't go red, or goes red for a *different* reason → STOP. Do not write the fix.** Your root cause (or spec understanding) is wrong — re-diagnose first. Implementing now means coding against a false premise, likely a no-op. This stop is the skill working as intended, not a failure.

### 4. Blast-radius pass (before touching existing code)

If you're changing code that already exists — especially old/shared code — find what *else* depends on it before you edit: `git grep` the symbol, list the callers, note shared utilities. State the blast radius explicitly ("N other consumers of this helper stay untouched; the change is scoped to these 2 call sites"). For brand-new code, skip this.

**Deleting a guard is a blast-radius event, not a simplification.** When the fix is to remove or loosen a condition — an early-return, a state check, a lock, a retry cap, a debounce — `git grep` finds nothing, because nothing *references* a guard. So ask the question grep can't: **what invariant was this incidentally enforcing, beyond the one it's named for?** Write that answer down before you delete it. (Example: an `if state != IDLE: return` can look like a stale UI check, yet also be the only thing serializing calls into a non-thread-safe native library, so removing it turns a lost-input bug into a process abort. Chesterton's fence, with no compiler to catch it.)

### 5. Implement to GREEN

Write the **minimal** change that makes the red test pass. Don't gold-plate; don't fix adjacent things you noticed (note them for the caller instead).

### 6. Confirm green — and no regressions

- The new test/repro passes.
- The **full affected suite stays green** — you didn't trade one bug for another. For an existing-code change, this is the payoff of the blast-radius pass.

## Close-out

Keep it short (this skill runs inline — often as `/work`'s execute phase — so don't end on a heavy terminal block that reads as "stop here"):

- **Pinned:** the behavior you drove toward.
- **Red→Green:** the test/repro failed for `<reason>`, passes after the change.
- **Blast radius:** what else touches this, confirmed unaffected (or "new code, n/a").
- **Coverage note:** if the red medium was a `/devtools` repro, say so plainly — **no permanent regression test exists**; flag adding one (or the infra for it) as a follow-up, since a browser repro isn't committed coverage.

## Guardrails

- **Never skip the red gate.** A fix written before a failing test is not TDD — it's a guess with extra steps. If you're tempted to "just write the fix, it's obvious," that's exactly the case the inert-normalizer trap punishes.
- **Red must precede green from the same diagnosis.** Don't write the fix, then back-fill a test that passes — that proves nothing (the back-filled-test failure mode, prospectively).
- **Minimal implementation.** TDD drives the smallest change that satisfies the test, not a refactor. Scope creep → note it, don't do it.
- **Don't fake a red.** If the only way to make the test fail is to assert something contrived, your test isn't probing the real behavior. Re-pin step 1.
- **Implement to the contract, not to the assertion literals.** When one context writes both the test's expected values and the fix, there's a pull to code toward the *literal* — hard-coding the fixture's expected output, or shaping the impl to satisfy the assertion rather than the real behavior. That's a green that proves nothing (the back-filled-test failure mode in miniature). Implement from the **behavior you pinned in step 1**, not the numbers in the test. High-stakes strong form (load-bearing logic, or when you don't trust yourself not to peek): have a *separate context* write the implementation from the behavior spec **alone — no assertion literals visible** — so it structurally can't overfit. Same fork-for-integrity that keeps `/mutate` honest.
- **No commits or pushes.** Building, not shipping — that's a separate, explicit step.
