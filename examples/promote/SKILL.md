---
name: promote
description: >-
  Promote one long-lived env branch to the next in the deploy chain —
  `dev`→`staging` or `staging`→the prod branch — as a safe merge PR. Runs a
  merge-tree clean/conflict pre-check, opens the promotion PR (direct if clean,
  resolve-to-source branch if conflicted), then chains /merge-and-verify to
  gate + merge + watch the deploy + QA — forcing the no-close-source option so
  the promotion never DELETES the source env branch. Fire ONLY on an explicit promote request — `/promote dev
  staging`, "promote dev to staging", "promote PROJ-123 to staging", "release
  staging to prod"; NEVER proactively (it deploys to staging/prod). Carries the
  WHOLE source branch forward, so it's a release-readiness call on everything on
  the source branch, not a per-feature action. NOT /pr (feature→integration,
  commits + pushes; the source IS the env branch). NOT
  /merge-and-verify (this CHAINS that; /promote adds the pre-check + the
  no-close-source safety). Staging hop re-confirms; prod hop hard-stops.
  Project-scoped example (genericized).
disable-model-invocation: true
argument-hint: <from> <to> [noqa] [nested]  (e.g. `dev staging`; omit the pair to infer the next chain hop; tokens pass through to /merge-and-verify)
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate one idea: **an env-branch promotion is its own atom — pre-check the merge before opening anything, carry the whole source branch knowingly, and hard-code the one safety flag whose default would delete a long-lived branch.** The real version encodes one team's repos, PR helper, CI triggers and version-tag rules; everything identifying here has been genericized. Don't install it — adapt the pattern.

Promote one env branch to the next in the chain, as a merge, without the
footguns. This is the release hop *after* a change has landed on `dev` — and it
carries the **whole** source branch, so it's a readiness call on all of `<from>`.

**Run only on an explicit promote request** — it deploys.

**And every PR from an env branch into `staging` or a prod branch goes through this skill** — docs-only releases included. "The branches are content-aligned" and "this merge deploys nothing" stay unverified until step 3a's ride-along list says so; another session may have merged to `<from>` minutes ago. The project backs this with a hook that blocks the PR create when this skill wasn't invoked since the user's last message.

**Standalone (not under a rollout driver)?** Run the rollout's parallel-session check before step 3 (see the `/rollout` example), so every session whose change rides this promotion knows it's shipping.

## Helpers this skill leans on

Two small project scripts sit behind the steps below; the skill describes what each must do, not where it lives:
- **The PR helper** (the same REST helper the `/pr` example uses) — `create` opens a PR for a source → dest pair from a title and a description file; `merge` merges a PR by id. Its merge closes (deletes) the source branch by default, which is exactly why step 4 exists.
- **A version-check helper** — `bump <patch|minor> <branch>` computes the next release number from the remote's tags and, if the branch doesn't already carry it, pushes a short-lived release branch that sets it (printing `NOOP`, `BUMP`, or `FAIL: … already exists`); `verify <ref> [--pre-merge]` checks that a commit's version file carries the next unreleased number and contains the last release, printing `OK: tag vX.Y.Z` or `FAIL`.

## 1. Resolve the hop + repo
- Args `<from> <to>` (e.g. `dev staging`). If omitted, infer the next hop from the
  repo's chain (e.g. `dev→staging→main`; repos can differ in their branch names, so keep
  a per-repo table). Confirm the pair if ambiguous.
- One repo per run (each is its own PR + deploy). Promoting a change that spans
  repos (e.g. a backend service + the frontend that calls it) → run `/promote` per repo,
  backend first, so staging's backend is live before you QA the frontend there.
- `git fetch origin` first — you're about to reason about `origin/<from>` vs
  `origin/<to>`, and stale refs lie.

## 2. Pre-check: clean or conflicted?
`git merge-tree --write-tree origin/<to> origin/<from>` (non-destructive; git ≥2.38).
- No `CONFLICT` lines → **clean** → step 3a.
- `CONFLICT` lines → step 3b. Skipping this check risks discovering the conflict
  only mid-merge. (The usual cause is env branches that drifted apart because the
  same fix was once landed twice, as separate PRs to each branch, instead of being
  merged up the chain.)

## 2b. Staging hop only — claim the release's version number
A release gets its number once, here, on `<from>`, so dev, staging and prod all
report the version its prod tag will carry. From the service repo root, run the
version-check helper's `bump <patch|minor> <from>` — `minor` if anything in the
ride-along list is a feature, else `patch`. The next number comes from the remote's
tags, so a stale version file self-heals.
- `NOOP` → `<from>` already carries this release's number (a second staging hop
  before prod). Carry on.
- `BUMP` → it pushed that release branch off `origin/<from>`. Open a PR from it
  into `<from>` with the PR helper, then merge it (closing this source is fine; it's
  throwaway). A PR, not a push: some repos reject direct pushes to their integration
  branch. No deploy watch — the staging deploy exercises the same code. Then
  `git fetch` and redo step 2.
- `FAIL: … already exists` → a parallel session is mid-release on this repo. Its
  release carries whatever is on `<from>`; wait for its branch to merge, then re-run.

Skip it for a repo whose release tooling owns its own version numbers. A trunk-based
repo has no staging hop: run `bump <level> main` and merge its PR into `main` (that
merge's pipeline is the release); 4b's checks still gate the approval and the tag.

## 3a. Clean → direct promotion PR
The source is the env branch itself — nothing to commit or push. Summarize what's
riding along (`git log --oneline origin/<to>..origin/<from>`) into a description
file, then open the PR with the PR helper: source `<from>`, dest `<to>`, title
`Promote <from> → <to>`, and the description file.

## 3b. Conflicted → resolve-to-source branch, then PR that
A direct PR can't carry conflict resolutions. Branch off `<to>`, merge `<from>`
in, and resolve **to `<from>`** (the ahead/canonical side):
`git checkout -B promote/<from>-to-<to> origin/<to>` → `git merge origin/<from>`
→ `git checkout --theirs <conflicted>` (theirs = `<from>` here) → but KEEP
legitimately env-specific files as `<to>`'s (e.g. a staging-only config file or
script) → commit → push → open the PR with source
`promote/<from>-to-<to>` and dest `<to>`.

## 4. Gate + merge + verify — chain /merge-and-verify, never close the source
Invoke `/merge-and-verify` on the promotion PR, passing through any `noqa` / `nested` token
this run was invoked with (`/rollout` passes `nested` so the rung's report comes back to
it instead of ending the turn). It applies the escalating gate
(dev on go-ahead · **staging re-confirm** · **prod hard-stop**), merges, watches
the deploy green, and QAs the deployed env.

> **⚠️ THE footgun this skill exists to prevent — the no-close-source option is
> mandatory.** A promotion PR's source is a long-lived env branch. The PR helper's
> merge defaults to closing the source branch, which would **delete `dev` /
> `staging`** on merge. When you chain `/merge-and-verify` here, the merge MUST
> keep the source open. This is non-negotiable — say it explicitly in the
> handoff so it survives into the merge step. (Better still, make the helper
> refuse to close an env branch at all.)

## 4b. Prod hop only — stamp the release with a version tag

A prod deploy that leaves no version number behind leaves nothing durable saying
*what* is live — and "what's actually in prod?" is a question every later session
asks. The prod hop isn't done until the shipped commit carries an annotated tag.
**The order depends on what triggers the prod deploy, because if a repo deploys on tags,
the tag IS its trigger:**

- **If the repo deploys on tags** — tag **first**; the tag push is the deploy. Cut it
  with the repo's committed release script from a clean checkout of `origin/staging`,
  then let the prod workflow run (approving its manual approval step, if it has one).
  Check `git ls-remote --tags origin vX.Y.Z` before re-running anything — never re-run
  a release that already pushed its tag.
- **If the repo deploys on a branch push** — deploy first
  (merge + approve any manual approval step + prove the artifact live), **then** tag
  that merge commit:
  `git tag -a vX.Y.Z -m "<ticket> — <one line>" <sha> && git push origin vX.Y.Z`.
  Confirm the tag push is inert in the repo's CI config first: a branch-only
  filter typically ignores tags (many CI systems skip tags unless a tag filter says
  otherwise), and a condition that demands `branch == main` can't be satisfied by a
  tag push, whose branch is empty.
- **If the repo's CI would misfire on a tag — do NOT tag yet.** A condition that only
  excludes branches can *match* a tag push (empty branch) and then fail on settings it
  can't resolve: a red run and noise, not a deploy. Add a "not a tag" guard, ride it up
  the normal chain to the prod branch, then tag.

**The tag's number is the version file at the shipped commit — never pick one by
hand.** A hand-picked tag is how a repo ends up tagged `vX.Y.Z` while every branch's
version file still reads an older number. The version-check helper enforces it, twice:
- **Before opening the prod PR:** `verify origin/staging --pre-merge`. `FAIL` → this
  release never got its number (step 2b skipped), or a parallel rollout took it. Fix
  it on staging with `bump <level> staging` + a PR into `staging`, let that deploy,
  and re-verify.
  **A trunk-based repo** has no prod PR — its prod hop is
  approving the manual approval step on `main`'s pipeline once the bump PR (`bump <level> main` →
  PR into `main`) has merged. Run `verify <the waiting run's commit> --pre-merge`
  before approving. It compares against the last tag, never `main`'s own file; with
  no tag at all it WARNs instead (check the live app version by hand).
- **At tag time**, after the deploy is proven live: `verify <merge sha>`.
  `OK: tag vX.Y.Z` → tag exactly that. `FAIL` → don't tag; report it. It also fails
  when the commit doesn't contain the last release — older code went out (the
  stale-approvals trap below).

**Never run a committing version bump on a prod branch.** If the repo deploys prod on a
*push* to that branch, the bump commit itself kicks off a second prod deploy.

**Runs left waiting on approval are a backlog and a trap** (e.g. a prod workflow with a
separately approved deploy step that updates many resources). Before merging, find the
last prod-branch run where that step succeeded and diff everything it deploys (its code,
the DB schema/migrations, its prod config) from that SHA — approving it ships all of it,
not just this change. After the deploy is proven live, **cancel every older prod-branch
run still waiting on approval**: approving one later redeploys OLDER code over what just
shipped. (A cancel can show as still running for a few seconds; confirm the waiting job
never ran.)

## 5. Terminus
`/merge-and-verify`'s report is the terminus (it covers the merge, deploy, and
QA). If asked to promote a full chain in one go (`dev→staging→prod`), **stop
after staging and re-confirm before the prod hop** — never auto-continue to
prod. On the go-ahead, invoke `/promote staging <prod-branch>` fresh — the prod-only
rules in 4b only apply when this text is loaded for the prod hop. If promoting multiple
repos, report each and note the next repo.

**Stopping at the prod hop requires a breadcrumb that outlives the session.**
The hard-stop is a pause, not a decision to skip — but nothing tracks a pause,
so the release silently parks: green and verified on staging, never re-raised,
until someone happens to ask why the fix isn't live. Before ending, put the
pending hop where it will resurface **without** the transcript: a one-line
comment on the ticket ("verified on staging — awaiting prod hop"), and leave
the ticket in a non-terminal status. Name it in the report too, but the ticket
is the durable half.
