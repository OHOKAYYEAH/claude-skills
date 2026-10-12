---
name: test
description: "Audit the recent diff for in-process test coverage gaps (branching, boundaries, error paths, business invariants) and add robust tests where missing. Scope: pytest/vitest/jest/go test/etc — no browser E2E. Skips trivial diffs (docs, copy, config-only)."
disable-model-invocation: false
---

# Test Coverage Audit

You are auditing the in-flight changes in the working tree for missing **in-process** test coverage and adding robust tests where there are gaps. This is a focused, additive pass — not a refactor, not a coverage-number chase.

## Scope: what's in, what's out

**In scope.** Unit tests and fast integration tests that run via the project's standard test runner (pytest, vitest, jest, go test, cargo test, etc.) and exit in seconds. Tests that hit a local fixture DB, an in-memory cache, or a stubbed HTTP server are fine — those still count as fast in-process tests.

**Out of scope.**
- Browser-driven E2E (Cypress, Playwright, Selenium) — even when the project already has e2e infra. Selectors, auth bypass, fixtures, wait strategies, and flake patterns are project-specific tribal knowledge; a global skill "improving" them without it is a regression risk. If you see e2e infra (`cypress/`, `playwright.config.*`, `*.cy.ts`), do NOT touch it — surface as a deferred finding for the project's own e2e skill.
- Tests requiring real external services (live Stripe, broker APIs, third-party SaaS).
- Performance, load, or visual regression tests.
- Manual smoke tests or "test it in the browser."

If the project's test setup is unclear or missing entirely, say so and stop — do not invent test infrastructure.

## Argument handling

`$ARGUMENTS` lets the user redirect or narrow scope. Default scope (no argument) is uncommitted changes + any commits ahead of the upstream branch.

**Scope redirection** — argument names a git range. Override the default with the named range:
- "the last N commits" → `HEAD~N..HEAD`
- "since main" / "since master" → `main..HEAD` or `master..HEAD`
- "this PR" / "this branch" → ahead-of-upstream (this *is* the default, just confirm)
- "commit <sha>" / "<sha>..<sha>" → that explicit range

**Focus narrowing** — argument names files, paths, or concerns. Keep the default diff scope, but restrict the audit:
- File/path scope ("the Screener code", "frontend/", "auth.py", "scoring engine") → restrict to gaps in matching files; ignore other touched files
- Dimension scope ("focus on branching", "edge cases", "business invariants") → weight the gap categorization toward those dimensions

**Both at once** ("the last 3 commits, focus on the scoring engine") → apply scope redirection first, then narrow within it.

**Ambiguous** ("the recent stuff", "what we just did") → ask the user what they meant before proceeding. Don't guess.

The user's argument: `$ARGUMENTS`

## Step 1: Identify the diff and decide whether to run

Identify the diff per the **Argument handling** section above (default: uncommitted changes + commits ahead of upstream; override if the user passed a scope-redirection argument).

**Skip the audit and report "no in-scope changes" if the diff is exclusively:**
- Documentation (`.md`, `.txt`, `.rst`)
- Copy/text content (i18n strings, marketing copy, no logic changes)
- Styling-only (CSS, Tailwind class shuffling, color tokens)
- Config files without code changes (`.env.example`, JSON config, `tsconfig.json`)
- Dependency version bumps without behavioral code changes
- Type-only changes (TypeScript type aliases, Python type hints) with no runtime impact
- Pure renames (symbol rename, file move) the typechecker fully covers

If even a single hunk is logic — branching, math, parsing, validation, state changes, query construction, formatting — proceed.

## Step 2: Locate existing tests and confirm baseline green

Find the test files corresponding to the changed source files. Common patterns:
- Python: `tests/` mirroring `src/` layout, or `test_*.py` co-located
- TS/JS: `*.test.ts`, `*.spec.ts`, or a `__tests__/` directory
- Go: `*_test.go` co-located

The project's `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, or `README` may state the convention — check them before guessing.

Run the existing test suite (or just the touched test files if the suite is slow) to confirm a green baseline. **If existing tests fail before you write anything, STOP and report — don't add tests on top of a broken baseline.**

## Step 3: Audit for coverage gaps

For each meaningful code path in the diff, ask: **would an existing test fail if I broke this line?** If no, that line is uncovered. Categorize gaps across these dimensions:

- **Branching logic.** Every `if/else`, `switch`, ternary, early return, guard clause should have at least one test per branch. A function with three branches and one test is undertested.
- **Boundary conditions.** Empty input, single element, max size, zero, negative, off-by-one — the fenceposts.
- **Error paths.** Exceptions raised, validation failures, error responses, timeout handling, retries. Code that handles errors but is never tested *with* errors is a guess.
- **Business logic invariants.** Math identities, conservation laws, monotonicity, idempotence, range constraints. (Examples: a score is bounded to its declared range; weights within a composite sum to 1; an annualized return is monotonic in premium relative to strike.)
- **Public API contracts.** Return shape, status codes, error envelope, content type. If a function's signature is part of an API surface, its contract deserves a test.
- **Regressions.** If the diff fixes a bug, there should be a test that fails on the pre-fix code and passes on the post-fix code. No regression test = the bug can come back silently.

Categorize each gap as:
- **Critical** — untested logic that's a bug magnet (parsers, validators, math, state transitions, anything where being subtly wrong is silent)
- **Worth adding** — a straightforward case that's just missing; cheap to write
- **Skip** — trivial getters/setters, code already covered transitively, framework boilerplate, code paths the typechecker eliminates

## Step 4: Write the tests

Add tests for **critical** and **worth-adding** gaps. Run the tests after each meaningful batch — confirm new tests pass, confirm existing tests still pass.

**Quality bar — every test must clear these:**

- **One logical concern per test.** A test named `test_score_handles_empty_chain_and_negative_weights_and_caps_at_100` is three tests in a trench coat. Split it.
- **Name describes the property, not the mechanic.** `test_score_returns_zero_for_empty_chain` ✓ — `test_score_function` ✗.
- **Arrange / Act / Assert visible.** Setup, the call, the assertion. If a reader can't see those three phases, restructure.
- **No control flow inside a test.** `if`, `for` over assertions, or `try` to "see what happens" all signal a test that's testing too much. Parametrize, or split.
- **Realistic fixture data.** Use ticker symbols, real-looking option chains, plausible inputs — not `"foo"`/`"bar"`/`42`. Realistic data catches real bugs.
- **Mutation-test mindset.** Before committing a test, ask: if I changed `>` to `>=` in the code under test, would this test fail? If no, the assertion is too loose.
- **Don't test mocks.** If a test's body is mostly setting up mocks and then asserting the mocks were called, the test is testing your mock setup, not the code. Drop the mocks or rewrite as a real integration test using the project's fixture pattern.
- **Don't test the framework.** Skip tests that exercise the test runner, the ORM's `save()`, or the HTTP framework's routing — assume the framework works.
- **Don't test trivial accessors.** A pure getter that returns a stored field doesn't need a test. A getter that derives, transforms, or validates does.

Where the project's logic admits it (pure functions over input space — scoring, formatting, parsing), prefer **parametrized tests** over many near-duplicate test bodies. For **invariant-shaped, bug-magnet logic** (math, parsers, validators, state machines), go further: write **property-based tests** for the invariants (Hypothesis, fast-check) — and if the project has no property-testing library, **introduce one as a dev-dependency**, matched to the project's package manager and test runner. This is a deliberate exception to the no-new-infra rule: example-based tests only probe inputs their author thought of, and when the same model wrote the code, test and code stay correlated on the same blind spots — generated inputs are the one cheap check that isn't. Don't force it: a property test that just re-asserts a single example is noise. No real invariant → skip PBT for that code.

## Step 5: Stay in scope

This skill is **additive and scoped to the diff.** Things that look like gaps but are out of scope:

- **Untested code outside the diff.** Note them in the deferred section if obvious; don't fix them. That's a separate decision the user should make.
- **Refactoring source code "to make it testable."** If a function is genuinely untestable as written, flag it as a finding and stop — don't restructure source under the cover of writing tests.
- **New test infrastructure.** Don't add a new test runner, mocking library, or fixture framework. If the project doesn't have what you need, surface it and stop. (One sanctioned exception: a property-based testing library for invariant-shaped logic — see Step 4.)
- **Deleting existing tests.** Even if a test looks redundant or wrong, `/test` is additive. Flag it as a finding; let `/code-review` or the user handle deletion.
- **Existing e2e tests.** Out of scope (see Scope above) — surface as a deferred finding; don't modify them.

## Step 6: Output report

Keep it tight (this skill runs inline — often as `/work`'s harden phase, feeding `/mutate` next — so don't end on a heavy terminal block that reads as "stop here"):

```
### Test Audit
**Verdict:** <✅ coverage adequate / ➕ tests added / ⚠️ critical gaps remain>

**Tests added** (run and passing):
- `path/to/test_file.py::test_name` — one-line description of what's covered
- ...

**Critical gaps remaining** (if any):
- <gap description, why it matters, why you didn't fix it>

**Deferred / out-of-scope findings:**
- <one line each, or "none">

**Open questions:**
- <one line each, or "none">
```

If verdict is `⚠️`, the gap should be something you genuinely couldn't fix in scope (e.g., requires source refactor, requires new test infrastructure, ambiguous business invariant) — not laziness. Be specific about why.

## Guardrails

- **Run the tests you write before reporting.** A test that "should pass" isn't a test.
- **Don't chase coverage numbers.** A 100%-line-coverage suite full of weak assertions is worse than a 70%-line-coverage suite of tight ones. Optimize for "would catch the bug," not for the report.
- **Skipped is not deferred.** If you marked a gap **Skip** in step 3, don't put it in the deferred section — it was a deliberate non-issue.
- **If the project has no test runner at all, stop.** Setting one up is a meaningful infrastructure decision; report and let the user choose.
