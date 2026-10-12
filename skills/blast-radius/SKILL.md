---
name: blast-radius
description: >-
  Map what UNCHANGED code depends on what the diff changed, and whether it still
  holds, in the same repo AND sibling repos. Enumerates changed contract
  surfaces (signatures, DB columns, GraphQL fields, config/flags, props, new
  kinds of rows a new writer inserts) and hunts silent behavior changes the
  compiler will not catch. Fire before
  shipping a change to a shared contract surface, especially prod hotfixes on
  old code. Chain-safe. NOT /code-review (diff correctness).
disable-model-invocation: false
context: fork
background: false
agent: general-purpose
argument-hint: "[branch-or-PR# | commit-range | (default: working tree)]"
allowed-tools: Bash(git *) Bash(grep *) Bash(rg *) Bash(ls *) Bash(cat *) Bash(awk *) Bash(wc *) Bash(find *) Bash(sed *) Read Glob Grep
---

You are mapping the **blast radius** of an in-flight change, **in this isolated fork**. The other review skills point the telescope *inward* — "is the changed code correct?" You point it **outward**: *what unchanged code depends on what this change touched, and does it still hold?* The danger you exist to catch is the consumer that the author never opened — a caller in another file, a resolver in another repo, a report that read the column you just narrowed.

The highest-value find is the **silent behavior change**: a function whose signature is unchanged but whose behavior shifted (returns active-only rows now; a validator that warned now throws; a default flipped). The compiler won't flag it, `/code-review` reading the diff won't see the consumer, and tests pass — but a caller three files (or one repo) away quietly breaks. That class is the priority hunt.

## Why this runs isolated

The Blast Radius Report at the end is a satisfying terminal block. Run inline in the main loop, it tempts the model to end the turn — abandoning a caller's chain (`/super-review`'s mandatory recap, or `/work`'s pipeline). The fork **contains** that terminal cue: the report returns to the caller as a result, and the caller keeps control. Same structural fix `/sec-review`, `/review-plan`, and `/mutate` use.

This skill is **read-only** — it greps, reads, and traces; it never edits. So unlike `/mutate`, the fork here isolates context only; there's nothing to restore.

## Arguments

`$ARGUMENTS` may contain:
- Nothing → analyze the current branch's uncommitted/in-flight changes against the integration branch.
- A branch name → analyze that branch against integration.
- A PR number / URL → analyze the PR's source branch against its target branch.
- A commit range (e.g. `abc123..def456`) → analyze exactly that range.

Resolve this at the top of Phase 0. If ambiguous, ask once before starting.

## Repo topology — discover the seams, don't assume them

Cross-repo consumers only exist where the project has siblings. Establish the topology before you trace:

- **Read the root `CLAUDE.md` and the current repo's own `CLAUDE.md`** for the layout — a multi-repo workspace or monorepo vs a single standalone repo — and for any section naming which repos or packages consume which, over what contract (generated OpenAPI or protobuf clients, a shared DB, message-queue payloads).
- **Multi-repo workspace or monorepo** (sibling git repos side by side, or packages in one repo): a diff lives in *one* repo or package; its cross-repo consumers live in *siblings*. Locate the workspace root and list the siblings so cross-repo greps can run. (Typical seams: generated API clients, a database two services read, a message a queue carries between services.)
- **Single standalone repo:** say so plainly — the fan-out is in-repo only. That's a legitimate, smaller pass, not a skipped step.

**When siblings exist, a blast-radius pass that stops at the current repo's boundary has missed the exact class of failure this skill exists for.**

## The workflow

### Phase 0 — Survey & scope

In parallel where possible:

1. **State:** `git rev-parse --show-toplevel` (current repo root), `git branch --show-current`, `git status`, `git remote get-url origin`. Identify *which repo or package* the diff is in.
2. **Base branch:** from the repo's `CLAUDE.md`, if it names the branch new work is based on. Fall back to the remote default branch. If neither resolves, ask.
3. **Diff:** `git diff <base>...HEAD` (committed) plus the working-tree diff (if dirty). Capture the changed-file list with `git diff --stat <base>`.
4. **Topology:** resolve the layout per the section above — workspace root + sibling list, or confirm the repo is standalone.

### Phase 1 — Enumerate changed contract surfaces

Walk the diff hunk by hunk and extract every surface *other code can depend on*. For each, classify the **risk shape** — this drives how hard you hunt in Phase 2:

- **Additive** (new optional param with a default, new field, new export) → low risk; a quick existence check usually suffices.
- **Signature-breaking** (param added/removed/reordered/retyped, export renamed or removed, required field dropped, return *shape* changed) → the compiler/typechecker will catch most in-repo consumers; **cross-repo consumers over GraphQL or raw SQL will NOT be caught at compile time** — those are the residual risk.
- **New row shape — a new writer inserts rows an existing table never held before** (a new mutation or job writing rows, or an existing writer producing a new combination: a refund dated today, an item on a still-pending order, a row linked to its counterpart only by a text field) → a silent behavior change for every *reader* of that table. The schema and every read query are unchanged, so nothing flags it.
- **Silent behavior change — same signature, different behavior** → the priority hunt. No compiler help, no diff-read help. Examples: a query now filters `WHERE active = true`; a validator switched from warn to throw (fail-closed); a default value flipped; a function that returned all rows now returns a page; rounding/timezone/null handling changed.

Surfaces to enumerate:
- **Exported functions / classes / consts / hooks / types** — both signature changes and behavior changes.
- **DB schema** — migrations, added/dropped/renamed columns, changed nullability/defaults/types (an ORM schema file, plus raw SQL). Who SELECTs or writes that column, including other repos and report queries?
- **New row shapes** — any insert/create path the diff adds, or any row whose field combination is new (dates, statuses, sign, link columns left null). Write down the shape: "rows like X, with properties A, B, C". Skip this surface when the diff only reads, or when it writes rows exactly like the ones the table already holds.
- **GraphQL schema** — added/changed/removed types, fields, args, enum values, nullability. Trace into the generated/consuming clients and app queries.
- **Shared config / env vars / feature flags / constants** consumed elsewhere.
- **API routes / endpoints, queue or event message shapes.**
- **Shared React component props** (for components used in more than one place).

Output of this phase: a list of `<surface> — <risk shape>` lines. If the diff touches **no** shared surface (purely-internal change, test-only, copy/styling), say so plainly and short-circuit to a 🟢 report — do not manufacture surfaces.

### Phase 2 — Fan out to consumers (in-repo AND cross-repo)

For each surface, find **every** consumer:

- **In-repo:** `rg`/`grep` for the symbol; trace imports and call sites; for DB columns, grep the column name across queries and ORM models.
- **Cross-repo:** for any surface on a known seam (API schema field, shared DB column, queue message shape), grep the sibling repos too — generated client dirs, resolvers, the consuming app's query files. This is the step that catches the schema-coupling class.
- **For silent behavior changes**, grep finds the call sites but won't tell you they're broken — the call still compiles. For each consumer, **reason explicitly**: does this caller rely on the *old* behavior? (e.g., a report that assumed "all rows" now silently drops the inactive ones.) State the invariant the consumer assumed, then check whether the change preserves it.

- **For a new row shape, the consumers are the table's readers, not the writer's callers.** List every reader of the table: ORM queries on the model, raw SQL, SQL functions, views and materialized views, batch jobs, reports and exports, generated documents such as invoices, and cross-repo integrations. For each one, name the assumption it makes about rows (every order has exactly one shipping row, the parent is active, a status only moves forward, a quantity is never zero, rows can be deleted or edited independently), then check it against the new shape. Include the write paths that act on existing rows too (delete, edit, clone), because a new row shape can make an existing write path unsafe. With many readers, split the sweep across parallel searches and report which ones you covered.

If a surface has many consumers, don't truncate silently — if you cap the trace, say what you didn't follow.

### Phase 3 — Verify each consumer holds

Tag every consumer found:
- ✅ **Safe** — additive change, or the consumer doesn't touch the changed aspect.
- ⚠️ **At-risk** — the consumer *may* depend on old behavior; needs a human eye or a test. Default here when you can't prove safe.
- 🔴 **Broken** — definitely breaks: signature mismatch, removed field still referenced, behavior change the consumer demonstrably relies on.

Note where a typechecker *would* catch it (lower residual risk) versus where it *won't* — cross-repo GraphQL/SQL contracts and same-signature behavior changes are the won't-catch zone. **Do not run cross-repo builds** — they're heavy, deps may be uninstalled, and the value here is the reasoning, not the build. Point at where the compiler would/wouldn't help instead.

### Phase 4 — Blast Radius Report

Return this block as your result to the caller. It fires on every outcome, including "contained — no shared surface touched."

```
### Blast Radius Report
**Status:** <🟢 contained / 🟡 review needed / 🔴 breaks consumers>
**Scope:** <repo · base branch · N files>

**Changed contract surfaces:**
- <surface> — <additive / signature-break / SILENT behavior change>

**Consumer map:**
- <surface> → <consumer file:line> — <✅ safe / ⚠️ at-risk: why / 🔴 broken: why>
  (one line per consumer; group under the surface)

**Cross-repo crossings:** <each seam the change reaches into a sibling repo, file:line — or "none">

**Silent behavior changes (compiler won't catch):** <each same-signature behavior shift + the consumer assumption it violates — or "none">

**Recommended verifications:** <a test to add, a consumer to eyeball, a cross-repo deploy-lockstep note — or "none"; when a changed surface is a shared UI component, name the adjacent screens that render it as browser-QA targets>
**At-risk (⚠️):** <one bullet each, or "none">
**Broken (🔴):** <one bullet each, or "none">
```

## Guardrails

- **Read-only.** Surface findings; never edit code or fix consumers — that's the caller's decision.
- **Cross-repo is mandatory when the diff touches a seam.** An API schema field or shared DB column change is not fully analyzed until you've grepped the sibling repos. Stopping at the current repo's boundary is the failure mode this skill exists to prevent.
- **Hunt the silent class hardest.** Signature breaks are mostly compiler-caught; same-signature behavior changes are not. Weight your effort accordingly.
- **Don't manufacture blast radius.** A purely-internal or additive change gets a short 🟢 report. Mirror the no-manufactured-nits rule — an honest "contained" is a valid, valuable result.
- **Don't touch data files.** Never open or quote the contents of customer-data files (`*.csv`, `*.xlsx`, dumps, `*.sql` data scripts, exported reports) — trace code and schema, not data.
- **Don't run cross-repo builds or migrations.** Reason about where the compiler would catch a break; don't spend the time (or risk the side effects) running it.
