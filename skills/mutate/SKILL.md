---
name: mutate
description: Prove the test suite actually catches bugs — inject realistic failure modes into the changed/critical logic one at a time, see which survive uncaught, then write tests to kill the survivors. Mutation testing with LLM-chosen, plausible mutations (off-by-one, sign flip, dropped guard), not brute-force operator churn. Fires after /test, or on bug-magnet logic (math, parsers, validators, state machines), to harden coverage. NOT for first-pass coverage (/test) or writing a fix test-first (/tdd). Runs isolated; returns a report.
disable-model-invocation: false
context: fork
background: false
agent: general-purpose
argument-hint: "[optional path/scope or git range, e.g. \"the scoring engine\"]"
allowed-tools: Bash(git *) Bash(npx jest *) Bash(npx vitest *) Bash(npm test *) Bash(yarn test *) Bash(pnpm test *) Bash(pytest *) Bash(go test *) Bash(cargo test *) Bash(mkdir -p *) Bash(ls *) Bash(cat *) Bash(grep *) Bash(awk *) Bash(wc *) Read Edit Write
---

You are hardening a test suite **in this isolated fork** by proving it actually catches bugs — and closing the gaps where it doesn't. The technique is **mutation testing**: deliberately inject a realistic bug, run the tests, and see whether any test fails ("kills" the mutation). A mutation that **survives** — every test still green despite the bug — is a hole in the suite. You then write the test that would have caught it.

## Why this runs isolated

This mutates the *real* working tree — one injected bug at a time. The fork keeps the final report **chain-safe** (it returns as a result, so `/work` keeps control instead of halting on the report block). The fork isolates **context, not the filesystem** — so the baseline capture, per-mutation revert, and exit self-verify below are **mandatory, not best-effort**. They're what make this safe to fire unprompted.

**And the filesystem you're writing to is shared with a caller who may still be editing it.** That is the whole reason reverts are surgical rather than whole-file: a snapshot restore can't tell your mutation from the caller's concurrent work, so it discards both. Design every restore to touch only what you wrote.

## The engine

This is a round-trip proof pointed at *hypothetical* bugs instead of one real change: break it → run → observe red/green → revert. Two properties fall out of that:
- A **survivor** = the suite is blind to a class of bug there.
- Every test you write to close a survivor is itself **round-trip-verified** — it must go red on the mutation and green on the correct code before you keep it. So `/mutate` never adds a test that doesn't actually bite.

## LLM-chosen mutations beat brute force

Don't mechanically flip every operator the way `mutmut`/`stryker` do — that buries the signal under equivalent-mutant noise. Pick mutations that map to **real failure modes a careful reviewer would worry about**, and keep the set small (the top handful per target, not every permutation). Smart, bounded mutations are what make this fast enough to live inside `/work`.

## Arguments

`$ARGUMENTS` is optional. Default scope = the current diff (uncommitted + commits ahead of upstream). An argument can **redirect** scope (a git range like `main..HEAD`, "the last 3 commits") or **narrow** focus (a path/concern like "the scoring engine", "the P/L inference"). Same conventions as `/test`. Ambiguous → ask once.

## The workflow

### Phase 0 — Scope, baseline, go/no-go

1. **Identify the scope** per Arguments (default: the diff).
2. **Skip trivial scopes.** If the scope is exclusively docs/copy/styling/config/type-only/pure-rename, there's nothing to mutate — report "no logic in scope" and stop. Mutation testing only earns its cost on logic (branching, math, parsing, validation, state).
3. **Locate the covering tests** (project conventions; check `CLAUDE.md`). If the code has **no in-process test seam** (UI-only, no runner, would require new infra) → stop and flag, same boundary as `/test`. Mutation testing is in-process; browser-only code is out of scope.
4. **Confirm a green baseline.** Run the relevant tests — if they're red before you start, STOP and report. Don't mutate on a broken suite.
5. **Capture a restore point.** `git rev-parse HEAD` → `BASE_HEAD`; `git stash create` → `SAFETY` (dangling commit of uncommitted work, tree untouched; empty = clean); save `git status --porcelain` as the baseline. **`git stash create` skips untracked (`??`) files** — for each untracked file in scope, copy it byte-for-byte to the scratchpad and treat that copy as its `SAFETY`. Your *only* legitimate diff from this baseline at exit is the new test code.
6. **Record what you will revert *to*.** For every site you're about to mutate, keep the **exact pre-mutation text** of the region you're changing. That string — not a git snapshot — is what you restore in Phase 2. `SAFETY` remains the emergency net, but it is a **whole-file rewind to Phase 0**, so reaching for it discards anything written to that file since. See the concurrency rule in Phase 2.

### Phase 1 — Pick targets and design mutations

Target the **bug-magnet logic** in scope; skip trivial accessors and framework glue:
- **branching** — `if/else`, `switch`, ternaries, guard clauses, early returns
- **boundaries** — `<` vs `<=`, `0` vs `1`, first/last, empty
- **math / units** — arithmetic, a `* 100` / `/ 1000` scale factor, rounding
- **parsing / validation** — format handling, accept/reject logic
- **state transitions** — status changes, enum handling

For each target, design a small set of **realistic** mutations — the bugs a reviewer actually fears:

| Mutation | Example |
|---|---|
| comparison flip | `>` ↔ `>=`, `==` ↔ `!=` |
| off-by-one / boundary | `i < n` → `i <= n`, drop a `+ 1` |
| sign / operand swap | `a - b` → `b - a`, `+` → `-`, drop a negation |
| units / scale | remove a `* 100` or `/ 1000` |
| guard / null | delete an early `return`/`throw`, drop a `?.`, swap `&&`/`||` |
| branch swap | exchange the bodies of two branches |
| default / fallthrough | change a default, drop a `case` |
| async | drop an `await` |

Bound it to the highest-value handful per target. Log what you chose, so the report can state coverage honestly.

### Phase 2 — Run the mutations (one live at a time)

For each mutation:
1. **Apply** it via Edit.
2. **Run the affected test files** (specific files — fast signal).
3. **Record** the outcome: **KILLED** (≥1 test failed — the suite catches it) or **SURVIVED** (all green despite the bug).
4. **Revert immediately, and revert *surgically*.** Reverse the mutation with `Edit` — put back the exact pre-mutation text you recorded in Phase 0.6. **A whole-file restore is not the normal path.**

   `git checkout "$SAFETY" -- <file>` rewinds the file to the Phase-0 snapshot, which silently discards any edit the **calling session** made to that file while you were running — no error, no conflict, nothing red. The failure shape: a one-line guard vanishes mid-run while **its comment survives**, so the file reads as though the guard were still there; the suite stays green and only a later reviewer catches it.

   Before any whole-file restore, **check for a foreign edit**: compare the file's current bytes against what *you* last wrote to it. If they differ, someone else touched the file — reverse-edit your mutation only, never `git checkout` over it, and **record the collision** for the report. If a whole-file restore is genuinely unavoidable (the reverse-edit won't apply, the file is corrupt), use `git checkout "$SAFETY" -- <file>` when `SAFETY` is non-empty, else `git checkout -- <file>` — and say so in the report. Plain `git checkout -- <file>` reverts to **HEAD**, which on the default uncommitted-diff scope destroys the very change under test.

   **Never stack mutations** — exactly one is live at any moment.

Classify each **SURVIVOR**:
- **Real gap** — the bug changes observable behavior for some realistic input, and no test noticed → close it in Phase 3.
- **Equivalent mutant** — the mutation genuinely can't change behavior for any reachable input (e.g. a `<=`/`<` boundary the value can never hit) → **not a gap, no test needed.** Recognizing these is what keeps mutation testing from spawning contrived busywork tests.
- **Latent bug** — injecting the "bug" reveals the *current* code is already wrong (the mutation is actually the correct behavior). → a finding for the caller; note it, **do not fix it here.**

### Phase 3 — Kill the survivors

For each real-gap survivor, write the test that catches it, round-trip-verifying the test itself:
1. **Re-apply** the mutation.
2. **Write / extend the test.** Run it → it MUST go **red** on the bug. If it stays green, the test doesn't actually probe the failure — fix the test, not the assertion count.
3. **Revert** the mutation. Run the test → it MUST go **green** on the correct code.
4. Leave the test in place; move to the next survivor.

Hold every test to `/test`'s quality bar: one concern per test, named for the property, realistic fixtures, visible Arrange/Act/Assert, no control flow. If closing a gap would require test infrastructure that doesn't exist, stop and flag it — **don't invent infrastructure.**

### Phase 4 — Self-verify and report

**Self-verify (mandatory — two checks, and the second is the one that bites).**

1. **No mutant leaked.** `git status --porcelain` must show **only your added/edited test files** vs. the Phase 0 baseline — **zero** source-file changes. If a source file still differs, reverse-edit it and report it.
2. **Every mutation site is back verbatim.** For each site, assert the exact pre-mutation string from Phase 0.6 is present by **literal substring match** (`needle in file_text`) — never `grep -c`. `?`, `[`, `.` and friends are regex metacharacters; a pattern containing them can return a false `1` on a site that was *not* restored.

**Why check 1 alone is not enough.** If a whole-file restore clobbered a concurrent edit, the source file now *matches* the Phase-0 baseline — so `git status` comes back clean and check 1 **passes while work has been destroyed**. A green check 1 proves no mutant leaked; it proves nothing about what was overwritten. Report every collision recorded in Phase 2 even when both checks pass, so the caller can re-verify their own edits survived.

Then run the full affected suite green before reporting.

```
### Mutation Report
**Verdict:** <✅ suite has teeth / ➕ gaps closed / ⚠️ gaps remain>

**Mutations:** <N tried — K killed, S survived (G real gaps, E equivalent)>

**Survivors closed (tests added, round-trip verified):**
- `path::test_name` — now catches: <the mutation it kills>

**Real gaps NOT closed (if any):** <why — needs infra / ambiguous invariant>

**Equivalent mutants (no test needed):** <mutation — why behavior-preserving>, or "none"

**Latent bugs surfaced (current code wrong):** <file:line — what — for the caller>, or "none"

**Files I wrote to (re-verify your own edits here):** <paths touched by mutations>

**Concurrent-edit collisions:** <file — a foreign edit appeared mid-run; what I preserved>, or "none observed"

**Out of scope / deferred:** <one line each, or "none">
```

## Guardrails

- **One mutation live at a time; revert before the next.** The exit self-verify proves no source mutation leaked — this is what makes the skill safe to fire unprompted.
- **Assume the tree is live.** You mutate the *caller's real working tree*, and the caller may still be editing it. Revert by reverse-edit, check for a foreign edit before any whole-file restore, and never let a clean `git status` stand as proof that nothing was lost — a clobbered edit looks exactly like a clean tree.
- **Never commit or push.** Hardening, not shipping.
- **Don't chase a mutation score.** A contrived test that kills an equivalent mutant is worse than no test — optimize for "would catch a *real* bug," exactly like `/test`.
- **Bounded, realistic mutations only.** No brute-force operator churn; no mutating trivial code.
- **No new test infrastructure.** No test seam → stop and flag. Same boundary as `/test`.
- **Don't fix the source.** A mutation that reveals a latent bug is a *finding*, not a license to patch — the caller decides.
