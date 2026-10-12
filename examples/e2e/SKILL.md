---
name: e2e
description: "Project browser-E2E atom: run the browser E2E specs (Cypress here) that cover the current diff, in whichever app has a suite, against a live target, diagnose every red before judging it (environment / flake / outdated-by-intent / pre-existing / caused-by-diff), and only when a critical journey has no spec, graduate the verified /qa golden path into ONE new spec plus its test-case doc. Chained by the project's land-leg right after its local /qa pass; also fire on \"run the e2e / cypress tests\", \"is the suite still green for this\", \"write a cypress test for X\", \"cover journey X\". Runs isolated and returns a report. NOT /test (in-process unit/integration coverage), NOT /qa or /devtools (live exploratory browser QA; this is the durable, re-runnable suite), NOT post-merge CI triage (a merge-and-verify skill reads CI reds, using this skill's diagnosis ladder). Project-scoped example (genericized)"
disable-model-invocation: true
context: fork
background: false
agent: general-purpose
argument-hint: "[optional: target URL · a journey to cover · \"whole suite\"] — optional"
---

> **Read-only example.** Browser E2E as a chained atom that diagnoses every red before anyone acts on it (environment / flake / outdated-by-intent / pre-existing / caused-by-diff, and only the last stops a ship) and grows the suite by at most one spec per ship, only for an uncovered critical journey. Don't install it — adapt the pattern.

You are keeping the project's browser E2E suite honest for one change, **in this isolated fork**.
The in-process layers (`/tdd`, `/mutate`) and the live browser pass (`/qa`) have already verified
*the change*. Your job is everything else: prove the flows the change didn't mean to touch still
work, using specs that run the same way every time and cost nothing to re-run — and, rarely,
make the suite one journey stronger.

Three moves, in this order of frequency: **run** the specs that cover the diff (every time),
**diagnose** each red before anyone acts on it (whenever something fails), **graduate** one new
spec (only when a critical journey has none). Most runs end after the first move.

**Why this runs isolated:** Cypress output and failure screenshots are large and disposable, and
the report has to come back to the caller as a result so the pipeline keeps control. Read failure
screenshots directly here; this context is thrown away.

**Hard contract: always end with the E2E Report (step 7)** — including when there was nothing to
run. The caller routes on its verdict line.

**What ships with the real skill (not here):** four helper scripts — a spec indexer that lists
what each spec touches (test-case IDs, page objects, visited routes, API operations, tasks,
`.only` flags) so a diff can be matched to specs; a target launcher that boots a throwaway server
for a checkout or ref on an offset port; a runner that points Cypress at an explicit target and
serializes runs machine-wide; and a JUnit parser that summarizes a run per spec — plus
one profile per app and the diagnosis and graduation references summarized in steps 4 and 5.

## Inputs

A caller (normally the project's land-leg, e.g. the `/qa-and-pr` example) passes a block like
this; resolve anything missing from git and the defaults below, in that order.

```
repo: <the app whose suite to run>
checkout: <absolute path of the service checkout or worktree>
target: <URL the change is served at — e.g. http://localhost:<port>>
api: <backend URL, for a frontend whose suite needs a specific backend>
base: <diff base ref — defaults to origin/<integration branch> after a fetch>
ticket: <KEY, for naming evidence and test cases>
intent: <one paragraph: what the change deliberately does>
golden: <the /qa golden-path scenario(s) that passed: steps + expect + Observed (route · operation · record)>
main-baseline: <canonical URL of the main checkout's server, if it's on the integration branch>
```

Standalone (`/e2e` typed in a session): the repo is the service repo containing the cwd or the
recent edits; the diff is uncommitted + ahead of `origin/<integration>`. The target is this
checkout's own server: in a worktree, the worktree's own offset URL, never the canonical port,
which serves the main checkout's code and would green-light a diff it never ran; in the main
checkout, the canonical local port. Not answering → bring up your own (step 1, *Own target*). A
journey in the arguments ("cover journey X") means graduate that journey; the project's E2E
coverage matrix doc names them. "Whole suite" means run every spec, chunked, against the
integration branch: an own target at `origin/<integration>` (step 1), and the specs from that
target's checkout.

## 0. Profile and scope

- **Read the app's profile** (one reference file per app). It holds everything app-specific: how
  to point Cypress at the target, login, data, exclusions, the smoke core, the baseline source,
  conventions for new specs. Don't work from memory of these repos — that goes stale.
- **No live suite** in this repo → report "no E2E harness for the repo" and stop.
- **Diff scope:** `git -C <checkout> diff --name-only <base>...HEAD` plus `git status --porcelain`.
  If nothing in it is reachable through this repo's own app (docs, test-only, CI config), report
  "no E2E surface" and stop. A backend change in a *different* repo than the suite (a backend
  service's diff) is out of scope for now — say so.

## 1. Preflight

Each check exists because its failure mode is silent or expensive:
- **Target answers** (`curl -s -o /dev/null -w '%{http_code}' <target>`). Down → **own target**,
  below. Never start the user's canonical frontends instead.
- **Own target** — the target launcher, given the repo and either a checkout to serve in place
  (a diff's checkout, on an offset port) or a ref (default `origin/<integration>`, built in a
  throwaway worktree, for whole-suite runs). A frontend whose suite needs a backend also gets a
  backend worktree on that backend's integration branch, so it isn't whatever branch the shared
  checkout sits on. It prints the target URL, API URL, checkout, env file and a state handle — pass
  them to the runner. Still booting → wait on the state handle; boot failed → environment
  verdict, quoting its log tail. **Always finish by tearing it down**, red or green. Its servers
  also die at a TTL (a couple of hours) or with the Claude process, so a missed teardown can't
  orphan them.
- **Env files present** per the profile. Worktrees often lack gitignored env files → point the
  runner at the main checkout's copy.
- **Dependencies installed** for the E2E project (a fresh worktree has none — install them).
- **Specs match the app they'll drive.** When the target isn't this checkout's own server (a
  deployed service, or another checkout's server as a baseline), check
  `git -C <checkout> diff --name-only HEAD..origin/<integration>` after a fetch. If it touches
  `cypress/` or app code, the local specs and the target's app may disagree — say so up front, and
  treat any red under that condition as unattributed at best.
- **Evidence dir:** a gitignored `…/<ticket or slug>/e2e/<HHMMSS>/` in the **main** checkout, even
  from a worktree, because removing a worktree deletes its ignored files.

## 2. Select the specs

Build the spec index once (narrow it with grep terms as needed). Then choose:

1. **The smoke core** from the profile — always. It catches "the app is broken for everyone"
   (a provider, layout or auth change) in under a minute.
2. **Specs that cover the diff.** For each changed UI file, find where it renders: grep for
   `<ComponentName` up to a route-level page, resolving `styled(X)` wrappers and re-exports —
   render sites, not imports, which overstate reach. Map those routes and areas to specs through
   their visited routes and page objects. For each changed API operation (e.g. a GraphQL query
   document or resolver, or a REST handler), grep the index for the operation name. A test-case ID the ticket names maps straight
   to its spec.
3. **Shared infrastructure changed** (session/auth, the API client, providers, root layout,
   routing, middleware) → the smoke core plus one spec per top-level area.

Drop specs the profile excludes locally, and any the index flags `.only` (report that — a stray
`.only` silently skips the rest of a file). Keep each runner call to what finishes in about
eight minutes; if coverage needs more, run it in chunks. Record everything selected and anything dropped, with why.

## 3. Run

The runner points Cypress at the target through the env vars each app actually reads (otherwise a
worktree run silently tests the main checkout's server), takes a machine-wide lock so two runs
can't share the DB or the test auth account at once, runs headless Chromium with **retries off**, and
prints a per-spec summary. Give each call a long tool timeout (around ten minutes; a two-minute
default kills a real run mid-flight with no summary), and a label per re-run, so each run writes to
its own subdir and a flake re-check never overwrites the red it's checking. Retries stay off because a test that passes on its second try is a
flake you want to see, not a green you want to trust. Exit codes: `0` green · `1` a test failed or
a spec produced no result · `2` the run itself broke (read the log tail it prints) · `3` another
run held the lock (wait, retry once) · `4` a prerequisite is missing (the message names it;
environment verdict) · `124` timed out, including a kill (partial results; split the list).

## 4. Diagnose every red

A red is evidence to classify, not a verdict. Most reds turn out to be the environment, a flake,
or a stale test, and a pipeline that halts on all of them rebuilds exactly the flake tax E2E is
supposed to be cheaper than. Look at the failure screenshot before theorizing, then classify each
failing test with the **first rung that fits** — the cheap rungs come first on purpose:

1. **Environment** — the test never got a fair run: a rate-limit `429`, a login that never
   completes, a 5xx inside a `before`/`beforeEach` hook (Cypress doesn't retry hooks; a redeploy
   or cold start produces exactly this), missing env vars, `ECONNREFUSED`, or a spec that opens a
   hard-coded record the local DB lacks. Fix what's fixable without starting anything the user
   owns; retry once if transient (after a 429, wait ~60s). **In CI, check for concurrent runs
   first** — parallel pipelines sharing one test environment produce failures that read as real.
2. **Flake** — re-run that spec alone, retries off, twice. Passes at least once → flake; report
   the tally ("1 of 3 red"). In CI, a test that passed only on retry reports success and leaves a
   `(failed)` screenshot, so green is not clean. A flake in the diff's own journey earns a
   sentence (the diff may have introduced the race), not a block.
3. **Outdated by intent** — the assertion targets exactly what the change meant to change (a
   renamed button, a new column, reordered flow, deliberate copy change) → update the spec (test
   files only), re-run it green three times retries-off, list it as **spec updated**. If you can't
   tell the change was intended, it wasn't established — go to rung 4. Never "fix" a spec to match
   behavior nobody asked for; that is how a regression gets laundered into the suite.
4. **Baseline** — run the spec against code without the diff, in the most similar environment
   available: in a worktree, the main checkout's server when it's on the current integration
   branch (same DBs and auth = clean comparison); otherwise the spec's recent CI history on its
   integration branch. Red there too → **pre-existing**. Green on a *same-environment* baseline,
   red with the diff → **caused by the diff**. Green only on a different-environment baseline, or
   no baseline → **unattributed**; never upgrade a confounded comparison to "caused" or downgrade
   it to "pre-existing".

| Verdict | Stops the ship? | Goes where |
|---|---|---|
| caused by the diff | **yes** — before the PR; the fix goes through a fresh `/work` cycle | the report, loudly |
| spec updated | no | the report + the PR (the edited spec rides it) |
| pre-existing | no | a `/triage` candidate |
| flake | no | a `/triage` candidate, with the tally |
| environment | no | "E2E couldn't verify: …" |
| unattributed | no | the report + a line for the PR description |

When you reach **caused by the diff**, stop diagnosing that test: don't fix the app — that's a
fresh `/work` cycle so review and the gates run on the fix. Report the failing assertion, the
baseline compared against, and the screenshot path. **Skip reasons are hypotheses:** an `it.skip`
comment is often wrong when re-tested, so never cite one as a diagnosis.

## 5. Graduate? (usually no)

Decide in one line, printed as `Graduate: yes — journey, why | no — why`. A spec the suite
carries forever has to be worth its runtime and maintenance, so the bar is narrow:

- **Yes** only if the diff touches a **high-priority journey that no spec covers** (first look for
  a written-down high-priority manual test case — automating one the team already wrote is the
  preferred graduation), or the ship fixes an **escaped bug that lived at a seam** (wiring, an
  API contract, auth, config, a render path) — and a verified `/qa` golden path is in hand. A
  bug in pure logic belongs to `/tdd`'s unit test instead.
- **No** for everything else: edge cases and validation messages (unit tests and `/qa` own
  those), styling or layout (no CSS, computed-style or pixel assertions), file *content* like PDFs
  (backend tests own that; a spec may assert the download fires), anything needing a real signup,
  real email, or other real third-party side effect — and always when step 4 found a
  caused-by-diff red (the change isn't done). **Budget: one spec per ship**; extending an existing
  spec file in the same area counts, and beats a new file.

On yes, translate the golden path's *behavior*, not its clicks: each "Expect" becomes an
assertion on something a user sees (text, visibility, URL, aria state) or on a network contract
(an aliased API response). Copy a sibling spec's shape and the profile's conventions:
selectors in the page object scoped to a container; no `cy.wait(<ms>)` (wait on an intercept alias
or a positive end state); the spec seeds its own data through the profile's mechanism and asserts
facts it created or internal consistency — never rows that exist in only one environment's DB;
one journey per file, one concern per `it`; never direct-DB writes. If an element can't be
selected without a new `data-testid` in app code, abandon and log "needs testid" for `/triage`.
Register it the way the project does, if it tracks test cases at all.

Then prove it: **stable** (3/3 green, retries off; still flaky after one fix → abandon, delete
what you wrote, log it — a flaky new spec is worse than none) and **non-vacuous** (temporarily
intercept the journey's core data call to return a 500, declared after the spec's own intercepts
and just before its visit, since Cypress runs the newest matching intercept first; if the spec
stubs that call itself, break the stub's response instead. Confirm the spec goes red, then remove the
intercept and confirm the exact text is gone). A graduation that can't meet the bar is abandoned
and logged — never shipped half-proven.

## 6. Self-check

- No mutation left in the tree: `git -C <checkout> status --porcelain` shows only files you meant
  to write (specs, page objects, test-case docs, the registry) — never app code, never a leftover
  vacuity intercept.
- No `.only` in anything you touched.
- The profile's typecheck shows no error in a file you touched (suites often carry pre-existing
  errors; filter to yours).

## 7. E2E Report (terminus)

```
### E2E Report
E2E: <repo> · <N> specs · <P> green · <reds by verdict, or "no reds"> · graduated <ID | none | abandoned> · <m>m<s>s
**Verdict:** ✅ clean | ⚠️ land with flags | 🛑 caused by the diff | ➖ no E2E surface / no harness
**Target:** <env and URL> · **Evidence:** <evidence dir>
**Selected:** <smoke core + N covering specs> — dropped: <spec: why> | none
**Reds:** <test — verdict — one-line cause — evidence (baseline compared, re-run tally, screenshot)> | none
**Spec updates:** <spec — outdated by: …> | none
**Graduated:** <spec + test-case doc — gates: 3/3 stable, vacuity red ✓> | none — <why> | abandoned — <why>
**Files written:** <absolute paths for the PR step to stage by path> | none
**For /triage:** <pre-existing, flaky and data-coupled reds, "needs testid" lines — each must end recorded> | none
**PR note:** <one line for the PR description when anything is unattributed or flagged> | none
```

The `E2E:` line is the evidence a run happened — print it verbatim, so a later usage audit
can count catches, flakes and graduations from it.

## Guardrails

- **Never edit app code.** Specs, page objects, fixtures, test-case docs, the registry — nothing
  else. A needed `data-testid` is a finding, not a license.
- **Never target prod.** Local and dev by default; staging only on an explicit ask.
- **Never run tests that create real third-party accounts** or send real email.
- **Never start the user's canonical frontends.** A target that's down gets an own target on an
  offset port (the target launcher), torn down when the run ends.
- **No commits, no pushes, no tickets.** Findings go back in the report; the PR step and `/triage`
  act on them.
- **Diagnose before judging.** Only a same-environment baseline can make a red "caused by the
  diff"; anything weaker is "unattributed".
