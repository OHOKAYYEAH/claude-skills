---
name: fortify
description: Harden the test suite for a unit of EXISTING code (a module/feature/path — not a diff). Adds missing coverage, proves the suite actually catches bugs by injecting realistic failure modes, and conservatively prunes worthless tests — high signal, low noise. For shoring up already-shipped code at rest, by unit. NOT for in-flight changes (that's /work's harden phase, or /test + /mutate on the diff). One unit per run; suggests the next.
disable-model-invocation: false
argument-hint: "[a path / module / feature — the unit to harden, e.g. \"the P/L engine\" or backend/app/services/pnl.py]"
allowed-tools: Bash(git *) Bash(npx jest *) Bash(npx vitest *) Bash(npm test *) Bash(yarn test *) Bash(pnpm test *) Bash(pytest *) Bash(go test *) Bash(cargo test *) Bash(npm install --save-dev *) Bash(pnpm add -D *) Bash(yarn add --dev *) Bash(pip install *) Bash(uv add --dev *) Bash(poetry add --group dev *) Bash(mkdir -p *) Bash(ls *) Bash(cat *) Bash(grep *) Bash(rg *) Bash(awk *) Bash(wc *) Read Edit Write
---

You are hardening the test suite for a **unit of existing code** — code that already shipped, not a diff you just wrote. Three moves, in order: **add** the coverage that's missing, **prove** the coverage actually bites, and **prune** the tests that are dead weight. The goal is a suite that's high-signal and low-noise: every test earns its place by catching a real bug.

## What this is

`/fortify` is `/work`'s Harden phase **decoupled from a diff and aimed at standing code, plus pruning.** Same `/test + /mutate` engine, different scope — a *unit at rest* instead of an *in-flight change*. That makes it complementary to the diff-scoped skills, not a duplicate of them:

- **`/fortify`** — existing code at rest, by unit. ← here
- `/test` — coverage gaps in a *diff*.
- `/mutate` — suite efficacy on a *diff*.
- `/work`'s harden phase — `/test → /mutate` on the chunk you just built.

## Arguments

`$ARGUMENTS` names the **unit**: a path (`backend/app/services/pnl.py`), a module/directory, or a feature ("the scoring engine", "SnapTrade sync"). Resolve it to concrete source file(s) and their public surface.

**No argument** → don't guess. Survey the codebase for **high-risk, low-coverage** units (bug-magnet logic — math, parsing, validation, state machines — with thin or no tests), propose a short ranked list, and ask which one (the single allowed question). **One unit per run** — at the end, suggest the next, don't sprawl across the whole codebase in one pass.

## The workflow

### Phase 0 — Scope the unit and capture a baseline

1. **Resolve the unit** to its source file(s) and its **public surface** — the exported functions / API endpoints / behaviors that callers and users depend on. That surface, not the line count, is what you're hardening.
2. **Locate its existing tests.** If the project has **no test infrastructure** for this unit (no runner, UI-only with no in-process seam) → stop and flag. Same boundary as `/test`; don't invent infra.
3. **Confirm a green baseline.** Run the unit's tests — if red before you start, STOP and report. Don't fortify on a broken suite.
4. **Capture a restore point.** `git rev-parse HEAD` → `BASE_HEAD`; `git stash create` → `SAFETY`; save `git status --porcelain`. You will **add and delete test files** here, so this matters — your only legitimate diff at exit is test-file changes (plus the package manifest/lockfile if Phase 1 introduces a property-testing library).
5. **Go/no-go.** If the unit is genuinely trivial (no logic — config, constants, pure pass-throughs), say so and stop.

### Phase 1 — Cover (add what's missing)

Audit the unit's **entire public surface** for coverage gaps — not a diff, the whole unit. Apply `/test`'s gap taxonomy and quality bar directly (don't invoke `/test` here — it's diff-scoped and would find "no changes"):

- **Gaps:** every branch (if/else, switch, guard, early return), boundary (empty, single, max, zero, off-by-one), error path (raised exceptions, validation failures, timeouts), business invariant (score in range, weights sum to 1, conservation/monotonicity), and public-contract shape.
- **Quality bar:** one logical concern per test, named for the property, realistic fixtures (real tickers/chains, not `foo`/`42`), visible Arrange/Act/Assert, no control flow in tests, no testing the framework or mocks. Parametrize pure-function input spaces rather than copy-pasting near-duplicate bodies.

Add tests for **critical** (bug-magnet: parsers, math, state) and **worth-adding** gaps. Run them; confirm green. Skip trivial accessors and framework glue.

For **invariant-shaped** parts of the unit (math, parsers, validators, state machines — the same bug-magnet list), also write **property-based tests** for the unit's invariants (Hypothesis, fast-check); if the project has no property-testing library, **introduce one as a dev-dependency** (same sanctioned exception as `/test`). Generated inputs probe cases no author chose — the one cheap check uncorrelated with generated-code blind spots — and a good property tends to kill whole mutant classes in Phase 2. Same guard as `/test`: no real invariant → no property test.

### Phase 2 — Harden (prove it bites) — /mutate

Invoke **`/mutate`** scoped to this unit — pass the unit explicitly and tell it to treat the **whole unit** as in scope (there's no diff to intersect). It injects realistic failure modes, confirms the now-expanded suite kills them, and writes tests to kill any survivors. It runs in an isolated fork and **returns its report as a result** — treat that as mid-pipeline input, not a turn-ending yield.

Carry its findings forward:
- **Survivors it closed** → folded into the suite (good).
- **Latent bugs** (the unit's current code is already wrong) → a **finding for the user**, not something you fix here.
- **Equivalent mutants** → noted, no test needed.

Phase 2 also produces the evidence Phase 3 needs: which tests actually kill mutants, and which don't.

### Phase 3 — Prune (conservative — high signal, low noise)

Now cut the dead weight. **Conservatism is the rule: auto-delete only the provably-worthless; flag everything else for the user.**

**Auto-delete** (and confirm the suite stays green after each — a worthless test's removal can't change pass/fail):
- **Zero meaningful assertions** — no assertions at all, or tautologies (`assert True`, `expect(true).toBe(true)`).
- **Framework/mock-only** — the body sets up mocks and asserts the mocks were called, testing your setup rather than the unit's behavior.
- **Exact duplicates** — identical test bodies (one survives).

**Flag for confirmation — do NOT delete:**
- **Mutation-proven redundant** — using Phase 2's results, a test that kills no mutant another test doesn't already kill. It's coverage-redundant, but may carry intent/documentation value, so it's the user's call. (Full per-test mutant attribution is expensive — surface the clear redundancies you observed, and say plainly that this isn't an exhaustive redundancy sweep.)
- **Over-mocked / stale-data / asserts-on-the-irrelevant** — smells, not certainties.

Never delete a test whose removal you can't prove is safe. When in doubt, flag, don't cut.

### Phase 4 — Self-verify and report

**Self-verify (mandatory).** `git status` must show **only test-file changes** (additions, edits, deletions) vs. the Phase 0 baseline — **zero source changes** (every `/mutate` mutation reverted). One legitimate addition: the package manifest + lockfile, *only if* Phase 1 introduced a property-testing library. If any other source file differs, restore from `SAFETY` and report it. Run the unit's full suite green before reporting.

```
### Fortify Report — <unit>
**Verdict:** <✅ hardened / ⚠️ partial — see gaps>

**Coverage added:** <N tests — the public surface / branches / invariants now covered>
**Efficacy (/mutate):** <M mutations — K killed by existing tests, S survivors closed with new tests>
**Tests pruned (auto — provably worthless):** <path::name — why>, or "none"
**Tests FLAGGED for your call (not deleted):** <path::name — redundant/smell, why>, or "none"
**Latent bugs surfaced (current code wrong — for you):** <file:line — what>, or "none"
**Tree restored:** <✓ only test files changed / ✗ discrepancy>

**Next unit suggested:** <highest-risk neighbor + one-line why>, or "none"
```

## Guardrails

- **One unit per run.** Suggest the next; don't sprawl across the codebase in a single invocation.
- **Conservative pruning is non-negotiable.** Auto-delete only provably-worthless tests; flag redundant/smelly ones for the user. A wrongly-deleted test silently removes a regression guard — the asymmetry favors keeping.
- **Don't fix source.** Latent bugs `/mutate` surfaces are findings, not a license to patch — the user decides. (If a fix is wanted, that's a separate `/tdd` or `/work`.)
- **No new test infrastructure.** No seam → stop and flag. Same boundary as `/test`, including its one exception: a property-based testing library may come in as a dev-dependency.
- **Self-verify: only test files change.** Source must match baseline at exit; restore from `SAFETY` otherwise.
- **No commits or pushes.** Hardening, not shipping.
