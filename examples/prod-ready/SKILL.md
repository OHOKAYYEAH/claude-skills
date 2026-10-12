---
name: prod-ready
description: Deploy-readiness confidence gate for a branch/PR you're returning to cold — "I parked this thinking it was prod-ready; days later, is it actually safe to ship to staging/prod?" Reconstructs deploy state from durable artifacts (git, CI, config, migrations, infra, ticket) instead of trusting conversation memory, runs the project-specific production-risk checklist, and ends with a GO / GO-WITH-CONDITIONS / NO-GO verdict. Fire on "is this prod-ready / safe to deploy / ready for staging / ready to promote?". NOT a code-correctness review — that's /code-review (this checks deploy safety and verifies that gate was passed); NOT a session-closeout or plan-phase-reversibility check. Project-scoped example (genericized).
disable-model-invocation: true
argument-hint: [optional: target env (staging|prod) | branch/PR — defaults to this branch's next promotion]
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate one idea: **deploy safety is a separate gate from code correctness, and it must be rebuilt from durable artifacts (git, CI, config, migrations, the ticket) rather than from anyone's memory** — ending in one GO / CONDITIONS / NO-GO call. The real version carries one team's per-repo deploy topology; everything identifying here has been genericized. Don't install it — adapt the pattern.

# Prod-readiness gate

This is a **deploy-readiness confidence gate** for a branch/PR you're returning to **cold** — "I parked this days ago thinking it was basically prod-ready; is it actually safe to ship to staging/prod now?" It answers one question — *how confident are we this is safe to deploy to the target environment?* — and ends with a **GO / GO-WITH-CONDITIONS / NO-GO** verdict.

The defining constraint: **reconstruct readiness from durable artifacts, not from conversation memory.** Whoever invokes this may not remember the nuances — that's the whole reason to run it. So rebuild the picture from git, CI, the configs, the migrations, the infra, the ticket, and any saved notes, and trust those over recollection.

**What this is NOT:** a code-correctness review — that's `/code-review` ("does the code work?"). This is the *deploy-safety* layer on top. Even correct code can be unsafe to ship: an unreviewed destructive migration, a secret the target env can't read, a sibling repo that must deploy in lockstep, a branch that doesn't actually reach prod. prod-ready *verifies the code-correctness gate was passed*, then checks everything **deployment** depends on. Run `/code-review` for the inward pass; run this for the outward, operational one.

**The deploy-topology reference.** The real skill ships a references file next to it (not included here): a per-repo table of prod triggers (branch push vs tag), manual approval gates, how each repo's migrations reach prod, the Terraform layout, and the cross-repo contract seams. The steps below consult it — and it is dated, so the live CI config always wins where they disagree.

## Principles

- **Read-only. This gate never deploys, approves a manual approval step, pushes, or applies a migration** — it surfaces and recommends; shipping stays a deliberate human action.
- **High signal, low noise.** Surface only what genuinely bears on deploy safety. An honest 🟢 GO is the most valuable output — don't manufacture risks to look thorough (same discipline as never manufacturing review nits).
- **Fetch before you judge remote state.** Run `git fetch` in the service repo before reasoning about ahead/behind/merged — `origin/*` is a stale local snapshot otherwise.

## Step 0 — Orient (reconstruct the cold context)

Resolve the target environment from `$ARGUMENTS` (`staging` / `prod`); default to this branch's next promotion. Then rebuild state:

- **Repo, branch, target → trigger.** Identify which service repo the diff lives in and map the branch to what it deploys. Prod triggers can differ per repo (a push to the prod branch, or a version tag) — look each one up in the deploy-topology reference.
- **`git fetch`, then position.** How far is this branch ahead/behind the trigger ref for the target? Already merged? Based on the right integration branch (per the project's branch table)?
- **The diff.** `git diff <trigger-ref>...HEAD --stat` plus the working tree. What surfaces does it touch — code / migrations / config / API schema / infra? This scopes every check below; a surface it doesn't touch is a check you skip.
- **CI status.** Is the branch green in CI? (The project's CI API notes have the recipes.) Red or never-built-on-the-trigger-ref is a fast 🔴/🟡.
- **Durable notes — the part you forgot.** Sweep the record for the ticket or the branch's subject: the tracker (ticket + comments + changelog), chat, email, git history and your prior sessions — a research skill does this in a fork, if your project has one — and note what the record says **and what it's silent on**. Cold-return is exactly the case where memory is the unreliable narrator: "what was I waiting on" (a stakeholder sign-off, a deferred item, a coordination dependency) is usually already written down somewhere you aren't looking. Also read the PR description and any saved notes about this branch. Minimum: check the tracker for the ticket the branch name / commit messages point at.

## The checklist

Run each dimension against the diff's actual surface. Skip cleanly what doesn't apply — a copy-only change skips migrations, secrets, and cross-repo. Don't pad.

### 1. Code-correctness gate passed?
prod-ready leaves correctness to `/code-review` but verifies that gate was *passed*: is there evidence this diff was reviewed and tested (PR approval, an in-session review, green unit/E2E tests)? If the diff is non-trivial and there's no such evidence — especially returning cold — the honest call is **🟡: run `/code-review` first**. Point at it; don't re-run the full review here.

### 2. CI / pipeline health
Green on the target's trigger ref, with tests + lint + typecheck (and E2E where the pipeline runs it) passing? A change that's green on the integration branch but never built on the prod branch hasn't proven it deploys.

### 3. Branch → deploy-coordinate correctness
Does this branch *actually reach* the target env, and only that env?
- **Gitflow vs trunk.** A feature branch usually must merge integration → default before it reaches prod (e.g. `develop` → `main`). "Prod-ready" for a feature branch often means "ready to merge toward the prod ref," not "deploy this branch as-is."

### 4. DB migration safety — the highest-stakes check
If the diff adds/edits a migration (whatever ORM or migration tool a repo uses), this is where prod breaks hardest. Nail two things:

- **What the migration does, and whether it's reversible.** Read it. Flag destructive/locking ops — `DROP COLUMN/TABLE`, `ALTER ... SET NOT NULL` on populated tables, type narrowing, renames, non-concurrent index builds on large tables. These have no in-pipeline rollback; recovery is a database backup restore. A destructive migration is a 🔴 until there's a backup/rollback plan and a human who knows what it does.
- **How — and whether — it reaches the target env.** This is the easy-to-miss part, and the mechanism differs per repo (look up which is which in the deploy-topology reference, then trace the live deploy job to confirm — CI drifts). Two risk patterns to recognize:
  - **Auto-migrate-on-approve:** the migration runs unattended *inside the deploy* right after the manual approval. The approval click is the only gate — **approving the deploy IS approving the migration**, with no checkpoint between it and the schema change. Know exactly what will run before anyone approves.
  - **No-auto-migrate:** the prod deploy path applies *no* migration. A new migration then needs an explicit out-of-band application plan, or the deployed code hits a schema missing the change.

### 5. Config, secrets & flag parity
Does the target env have everything this code needs at runtime?
- **New env vars / secret references:** added to the target env's config and present in the target env's secret store, with the deploy allowed to read them — otherwise the deploy fails when it fetches them.
- **Per-env feature flags:** is the flag in the right state for the target? Flags are per-env and easy to misremember (e.g. a feature flag that is on in dev/staging and off in prod). Confirm the target's value; don't assume.
- **Config drift:** a value that works in dev via a default may be unset in prod.

### 6. Cross-repo lockstep
Does this change a contract a *sibling repo* consumes — an API field/shape, a shared DB column, a schema the other side validates against, or any other shared contract? In a multi-repo system the worst prod failures are schema-coupling breaks: two services that must deploy in lockstep, shipped one at a time. If yes, deploying this repo alone breaks the consumer → **coordinate the sibling deploy**, or it's a 🔴. Trace the seams — every client module, handler or query on the consuming side — enumerate each consumer of the changed contract and confirm it still holds.

### 7. Infra / Terraform & rollback containment
- **Terraform is applied manually, never by CI.** If the diff touches the Terraform tree, no deploy pipeline applies it — confirm it's been planned/applied for the target env.
- **Rollback story.** Name the path in the verdict. A container platform that keeps prior revisions rolls back by routing traffic to the previous one; a migration does not. "Revision rollback, no schema change" is reassuring; "destructive migration, restore-from-backup only" is a flag.

## The verdict (always ends here)

Emit this block. It fires on every outcome, including a clean 🟢 — the verdict *is* the report, so don't write a separate wrap-up before it.

```
### Prod-Readiness Verdict
**Target:** <staging | prod>  ·  **Scope:** <repo · branch → <trigger-ref> · N files>
**Verdict:** <🟢 GO  /  🟡 GO WITH CONDITIONS (N)  /  🔴 NO-GO>

<one line: the confidence call in plain words>

- **Code-correctness gate:** <reviewed + green / run `/code-review` first / N/A trivial>
- **CI:** <green on <ref> / red / never built on <ref>>
- **Branch → env:** <reaches <target> via <ref>; fresh / N behind; based correctly / must merge X→Y first>
- **Migrations:** <none / N; destructive? <y/n>; reaches <target> via <mechanism>; rollback: <path>>
- **Config & secrets:** <parity ok / <secret> missing from <env>'s secret store / flag <X> must be <val> for <env>>
- **Cross-repo:** <contained / sibling <repo> must deploy in lockstep>
- **Infra/Terraform:** <no infra / applied / manual apply needed for <env>>

**Conditions to clear (🟡):** <numbered; each line = the single action that clears it>
**Blockers (🔴):** <each real prod risk + why it blocks + what would unblock>
```

Close with the affordance line — *"Otherwise clear to deploy to `<target>` — or say go and I'll work the conditions (grant the secret, file the follow-up, coordinate the sibling), then re-emit the verdict."* — never offering to deploy itself.

## Guardrails

- **Never deploy, approve a manual approval step, push, or apply a migration.** This is a gate, not a deploy tool. The most it does on a go-ahead is clear surfaced *prep* conditions (grant a secret, file a ticket, write a note) and re-verify; the actual ship stays a human action, and genuinely risky/outward actions still pause for confirmation.
- **Don't open customer-data files** (`*.csv` / `*.xlsx` / dumps / data `*.sql`) — trace code, schema, and config, not data.
- **The reference file is dated; the configs are truth.** If the deploy-topology reference disagrees with the live CI config, trust the config and note the drift.

## Where to look

- Per-repo prod triggers, approval gates, migration mechanics, Terraform layout, cross-repo seams: the deploy-topology reference described above.
- Config and secrets: the target env's secret store. CI API recipes and deploy commands: your project's own ops docs.
- Live prod DB state (schema version, row counts) when a check needs it: a read-only prod DB connection, if your project has one.

*Automating this as a CI gate (future): the operational checks here can run headless via `claude -p`, triggered on a staging deploy — a v2 idea, not wired yet.*
