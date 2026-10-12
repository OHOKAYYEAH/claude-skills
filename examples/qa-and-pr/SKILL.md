---
name: qa-and-pr
description: "The \"verify-locally-then-land\" leg — bring up the right local server (worktree-aware), seed the local DB from staging if it's too thin to exercise the change, run /qa run local against it, run the E2E specs that cover the diff via /e2e, gate on a clean pass, then open a PR via /pr. The land-half that /work deliberately stops short of, factored out so it's independently invocable: build with /work, then /qa-and-pr when you're ready to verify + land. /ship chains /work → this. Presumes review-ready code (it does NOT review — that's /work's job). Local-machine scoped: encodes the project's local ports, worktree conventions, seed source, and PR flow. Project-scoped example (genericized)"
disable-model-invocation: true
argument-hint: "[optional scope hint, passed to /qa + /pr] [optional tokens: \"noseed\" skip DB seeding · \"nested\" hand back to /ship]"
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate a project land-leg that verifies *before* landing: bring up the local env, seed it if it's too thin to exercise the change, walk the browser QA list, and open the PR only on a clean pass. Don't install it — adapt the pattern.

Verify the current in-scope change **locally in the browser**, then **open a PR**. This is the project's land-leg: `local env up → seed-if-thin → /qa run local → /e2e → gate → /pr`. It QAs *before* landing because local fidelity, not prod, is the safe checkpoint, and the PR (not a direct push) is the integration boundary CI deploys from. (A deploy-first project would land first and QA on prod instead — same slot in `/ship`, opposite order.)

Factored out of `/ship` on purpose: each leg is single-responsibility and independently runnable. Built something with plain `/work` (or by hand) and just want to verify + land it? Run `/qa-and-pr` directly. **This leg presumes the code is review-ready** — it runs no `/code-review` / `/super-review` itself, exactly like `/pr` doesn't. Review is `/work`'s job; `/ship` is what gates on it before calling this leg.

**Hard contract: this skill always ends with the QA-and-PR Report (step 7).** It either verifies-and-lands, or it stops at a gate (env unavailable / QA regression / an E2E red the diff caused) and says exactly why — it never trails off mid-leg. The common failure mode is an inner skill (`/qa run`, `/pr`) returning its block and you writing a turn-ending wrap-up. Don't — the inner block is mid-leg; your next move is the next step. **Exception — `nested` (`/ship` is driving):** do the work but hand the report content back as mid-pipeline input instead of emitting it as a terminus; `/ship` folds it into the one Ship Report.

## Argument parsing

`$ARGUMENTS` = optional scope hint + optional tokens:
- **`noseed`** → skip the DB-seeding step (step 3); QA against whatever data is already local. For when you know local has enough, or the change doesn't need data.
- **`nested`** (alias `noreport`) → `/ship` drives this leg and owns the final report. Do everything, but hand the QA-and-PR Report back as mid-pipeline input rather than ending the turn. Default off — standalone always emits the report.
- Anything else → scope hint. Pass it through to `/qa run` and `/pr` so both narrow to the same slice.

## The workflow

### 1. Resolve scope + service

- Identify the diff (default: uncommitted + commits ahead of upstream; narrow to the scope hint if given). Same default as `/qa` / `/pr`.
- Identify **which service** this is from `cwd` / the repo (a frontend or one of the backend services). That fixes the local URL, the integration branch (`/pr` knows these), and which DB the QA needs.
- **If the diff is exclusively non-UI** (pure backend/services/migrations, config, docs, test-only): there's nothing for the browser to walk. Skip steps 2–5 entirely, note "no UI surface — local QA skipped; in-process tests + super-review are the proof," and go straight to `/pr` (step 6). A backend change a screen renders still skips here — a full-stack local bring-up costs real time — and gets its browser pass post-deploy (`/merge-and-verify` step 6). Don't fake a browser pass.
- If any frontend surface is in the diff, continue.

### 2. Bring up the local environment (worktree-aware)

The goal: a running instance of **this service's own code** at a known URL, against the shared backends + DB, for `/qa` to drive. Resolve the target by checkout type:

- **Make sure the backends it needs are running.** Probe each one this service talks to (e.g. `curl -sf localhost:<backend-port>/health`). If any are down, start the leanest headless set yourself, in the background — backends and DB containers are safe to start and don't orphan. **What stays the user's: the full stack with its frontend dev servers.** Rule of thumb: **headless backends = you; canonical frontends = the user.**
- **Check the backend is serving the code you expect.** A shared backend serves whatever branch its checkout sits on. If it's off or behind the integration branch **and your change depends on recently-merged backend code**, the QA would go green against the *wrong* code — report the drift and let the user decide rather than trusting the pass. A frontend-only change against a slightly-behind backend is usually fine — flag it, don't block on it.
- **In a worktree:** if this worktree's own server isn't already running from your build session, start it yourself, in the background, on a port that doesn't collide with the main checkout's (a worktree's own server is always yours to start). Confirm it booted and QA against the URL it actually serves on — *never* assume the canonical port, which serves the main checkout's code.
  - **Change spans a frontend and a backend on the same branch:** start the backend worktree first, then point this frontend at it rather than at the shared backend. A frontend-only change against the shared backends is fine; flag a backend-coupled change whose sibling isn't running.
- **In the main checkout**: this service is already served by the main dev stack at its canonical port. That's the QA target; nothing to start.
- Record the resolved target URL for step 4.

### 3. Seed the local DB if it's too thin to QA (skip if `noseed`)

Local DBs often start empty/stale (e.g. an empty dashboard, no active records, an empty customer list) — a real prototype can't be QA'd against no data. **Seeding is QA-driven:** from the step-4 scenarios you're about to run, derive the entities they need (a customer with a few related records, an order, an active subscription, …), then check whether local has them (probe the running app or the local DB). **An empty list/table UI ≠ absent data** — a permission, role, or feature-flag filter can hide rows that are present; before concluding local is too thin (and seeding — or worse, punting QA to staging), verify the DB directly and/or call the underlying resolver/query, not just the UI. Seed **only what's missing** — don't bulk-load.

- **Source = a prod-like env (usually staging), read-only** (pre-authorized by default; tune to your team's policy). Extract with read-only queries → load into the local DB. **Never mutate the source.**
  - Read connection secrets from your secret store without echoing them. The **local** load target is whatever the running service is configured to use — read it from its config; don't hardcode it.
- **Read-only prod is the fallback, not the default** — reach for a read-only prod-DB access path *only* if staging is structurally out of sync with prod for the rows you need (rare when staging is refreshed often). Staging first. A service with no staging seed wired → the same read-only prod path, noted in the report.
- **Migration-in-worktree guardrail (hard).** If worktrees **share** a local DB and the in-scope diff includes a **new schema migration**, do **not** apply it from a worktree and do **not** seed against the shared DB whose schema this branch changes — that mutates every other session's DB. Either run this whole leg from the **main checkout** (where applying the migration to the local DB is the intended path), or **stop and surface** the conflict. Never silently migrate a shared DB from a worktree.
- Seeding writes to the **local** DB only — pre-authorized. Keep PII extracts scoped to the scenario need (hygiene, not a gate).

### 4. /qa run local

**Carry the frames out of this step.** `/devtools` screenshots each state it reaches; capture the paths it reports, because `/ship` hands them to `/before-after` afterward and the browser is gone by then. If the change is a visual *delta* rather than a new surface and a baseline is cheaply available (the old state was already on screen while reproducing, or the tree is clean in the main checkout), grab a before frame too — a pair beats a single shot. Never re-drive the browser purely to collect frames.

Invoke `/qa run local` with the scope hint **and the resolved target URL from step 2** (pass the explicit URL, e.g. `/qa run http://localhost:<worktree-port> the customer search`, so `/devtools` hits *this* worktree instance, not the canonical port). `/qa` drafts the behavioral scenarios and walks them via `/devtools` against the local server. For login, use the project's test credentials; fall back to manual login only for an env they don't cover. Don't ask the user to log in manually when test creds are available.

### 4b. /e2e — the durable suite

`/qa` just verified the new behavior by hand. `/e2e` covers what it didn't look at: it runs the E2E (Cypress) specs that cover this diff against the same target, diagnoses every red, and — only when a critical journey has no spec — turns `/qa`'s golden path into one new spec. It runs in a fork and hands back its E2E Report as a result, so the next move is step 5, not a wrap-up.

- **Only after a clean `/qa` pass.** A `/qa` regression already stops this leg, and graduation needs a golden path that actually passed. Services with no live E2E suite (e.g. a backend with no browser surface) skip this step.
- **Invoke `/e2e`** with this block; the fork sees only its arguments:
  ```
  repo: <the app whose E2E suite covers this diff>
  checkout: <this service checkout or worktree, absolute path>
  target: <the step-2 URL>
  api: <for a frontend that talks to a sibling backend worktree: its URL, else the shared backend URL>
  base: origin/<integration branch>
  ticket: <KEY>
  intent: <one paragraph: what this change deliberately does>
  golden: <the Golden scenarios /qa passed — steps + expect + its Observed line>
  main-baseline: <in a worktree, when the main checkout's server is up on the integration branch: its canonical URL; else none>
  ```
- **Carry three lines forward:** its *Files written* (step 6 stages them), its *PR note* (step 6 puts it in the description), and its *For /triage* list (`/ship`'s sweep-up takes it; standalone, it goes on this report's Next line).

### 5. QA gate

Read what `/qa run` returned:
- **Clean pass** (all scenarios ✅, only trivial slips fixed inline) → proceed to `/pr` (step 6).
- **A real regression / failed scenario** → **STOP. Do not `/pr`.** Surface the finding. Don't silently patch-and-repush — a fix goes through a fresh `/work` (or `/ship`) cycle so review + the gate run again on it. Report it in step 7 and stop.
- **`/devtools` 🛑 unavailable** (env couldn't come up, MCP not loaded, target unreachable) → you **cannot** verify locally → surface the gap and **stop before `/pr`**. Don't fake the verification. (This is the honest degradation: better to land nothing than to land unverified and claim "QA'd.")
- **`/e2e` 🛑 caused by the diff** (red with the change, green on a same-environment baseline) → **STOP. Do not `/pr`.** Same rule as a QA regression: the fix goes through a fresh `/work` cycle.
- **`/e2e` ⚠️ or ➖** (flake, pre-existing, environment, unattributed, spec updated, no surface) → proceed; its flags ride the PR description and the report. The change itself was already verified by `/qa`, a PR isn't a deploy, and halting on reds the diff didn't cause is how an E2E suite becomes the tax it was supposed to replace.

### 6. /pr

Invoke `/pr <scope>`, passing along `/e2e`'s *Files written* (a new or updated spec, page object, test-case doc) and its *PR note* for the description. It commits (conventional message, stage **by path** — the checkout may be shared with a parallel session; never `git add -A`), pushes, and opens the PR against the service's **integration branch** (from the project's per-repo branch table) through the git host's PR API, emitting the URL. Don't PR from an integration branch — `/pr` stops if you're on one.

### 7. QA-and-PR Report (terminus)

```
## QA-and-PR Report — <scope>
**Env:** <where QA ran — "worktree, own server on <port>" / "main checkout, canonical port" / "shared stack down — stopped">
**Seeded:** <what was pulled from staging, or "local data sufficient" / "skipped (noseed)" / "n/a — non-UI">
**QA:** <clean — N scenarios / findings list / 🛑 couldn't verify: reason>
**E2E:** <the `E2E:` line from /e2e, plus any PR note — or "skipped: no UI surface / no suite in this service">
**Frames:** <screenshot paths /devtools captured during the pass, in capture order — or "none">
**PR:** <url · base branch> — or "not opened: stopped at <gate> because <why>"
**Next:** <queued follow-ups>
```

**Under `nested`:** produce the same content but hand it back to `/ship` as mid-pipeline input — don't end the turn on it.

## Guardrails

- **Presumes review-ready code.** This leg does not `/code-review` or `/super-review` — that's `/work`'s job (and `/ship` gates on it before calling here). Standalone, you own that the code was reviewed.
- **Headless backends are yours; canonical frontends are the user's.** Make sure the backends it needs are running, and start a worktree's own server on a non-colliding port — both backgrounded. Don't start the full stack with its frontend dev servers (those stay the user's). The shared backend serves whatever branch its checkout is on — if it's stale/off-branch and your change depends on backend code it lacks, surface it (report the drift), don't silently trust the QA.
- **Seed from staging read-only; write only to local.** Never mutate staging or prod. The read-only prod-DB path is a fallback for structural staging drift only.
- **Migration-in-worktree → never migrate the shared DB from a worktree.** Run from main checkout or stop.
- **Don't fake QA.** Env unreachable or `/devtools` unavailable → stop before `/pr`, report the gap. Landing unverified is worse than landing nothing.
- **A real QA regression is a stop, not a patch-and-repush.** Fix through a fresh `/work`/`/ship` cycle so the gate runs again.
- **Stage by path (via `/pr`).** Shared checkout — never `git add -A`.
- **One terminus: the QA-and-PR Report** (or hand back under `nested`).
- **Don't expand scope.** Out-of-scope problems you trip over → the report's Next line, not this leg.
