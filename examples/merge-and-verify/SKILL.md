---
name: merge-and-verify
description: "The project land-leg for ONE reviewed, open PR: merge it (escalating gate: dev on go-ahead, staging re-confirm, prod always confirm), watch its CI deploy green pinned by merge SHA, prove it live, sanity-QA the deployed env (skip if no UI surface), then tear down this session's worktree. Fire on \"merge it and check CI\". NOT the full dev→staging→prod promotion ladder (the default after /ship, which chains this as its first rung) or env-branch promotion PRs (which also chain this). Project-scoped example (genericized)"
disable-model-invocation: true
argument-hint: "[optional PR ids / source branch / scope hint] [tokens: \"noqa\" skip post-deploy QA · \"qa dev\"/\"qa staging\" force the QA env · \"nested\" hand back to a composite]"
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate one hop of a deploy ladder as its own skill: merge a reviewed PR, watch its CI deploy pinned to the merge SHA, prove the change is live, then sanity-QA the deployed env — with the merge gate escalating dev → staging → prod. Don't install it — adapt the pattern.

Take a **reviewed, open PR** the rest of the way: **merge it → watch CI deploy it green → prove it live → sanity-QA the deployed env.** `/qa-and-pr` and `/ship` stop at **PR opened** because the PR is the user's review boundary; this leg starts once they have reviewed and said go. It verifies what pre-merge QA can't: that CI actually **built and deployed** the merged artifact (a broken Docker `COPY` or a missing env var is invisible to a local dev server), and that it **works on a prod-like environment** (ideally a staging env refreshed from prod data).

**Hard contract: this skill always ends with the Merge-and-Verify Report (step 9).** It either lands-and-verifies, or it stops at a gate (no go-ahead / CI failed / awaiting approval / a staging regression) and says exactly why — it never trails off mid-leg. The common failure mode is an inner step (the background CI watch, `/qa`) returning and you writing a turn-ending wrap-up; don't — your next move is the next step. **Exception — `nested`:** a composite is driving; hand the report content back as mid-pipeline input instead of emitting it as a terminus.

## The gate (read this first — it's the whole reason this leg is separate)

**Never merge without the user's go-ahead.** The authorization is usually conversational prose, not a bare `/go` — "merge it and check CI", "go ahead and merge the dev and staging PRs then poll staging" both count. The gate **escalates by destination environment**:

- **dev** → proceed on a clear go-ahead (non-prod writes are pre-authorized).
- **staging** → **re-confirm before merging, even if pre-authorized.** Staging is pre-prod; the next stop is the customer.
- **prod (the default branch)** → **hard stop. Always confirm explicitly**, every time, no matter what was said earlier. Merging to a prod branch is a prod deploy.

Not certain you're authorized for the env you're about to merge into → **stop and ask**: say what you'd merge where, and wait. A merge is not reversible the way an unpushed commit is.

## Argument parsing

`$ARGUMENTS` = optional PR/branch/scope hint + optional tokens:
- **`noqa`** → skip the post-deploy QA pass (step 6).
- **`qa dev` / `qa staging`** → force the QA target. An override only; step 6 infers the right env by itself.
- **`nested`** → a composite owns the final report; do the work but hand the Merge-and-Verify Report back as mid-pipeline input rather than ending the turn. Default off.
- A bare number / list of numbers → PR id(s). A branch name → resolve its open PR. Anything else → scope hint, passed to `/qa`.

## Helpers this leg leans on

Three small project scripts sit behind the steps below; the skill describes what each must do, not where it lives:
- **The PR helper's merge mode** (the same REST helper `/pr` uses to open PRs) — looks up the open PR for a source→dest pair, merges it with a merge commit, refuses to delete an env branch as the "source", and prints the bare merge-commit SHA on its last line.
- **A CI status helper** (for a CI with runs, jobs and manual approval steps, e.g. GitHub Actions or CircleCI) — prints a branch's latest pipeline run, pulls a failed job's logs, re-triggers a run on a branch, and approves a job waiting at a manual approval step.
- **A CI watch helper** — watches exactly one pipeline to a terminal state and exits on a fixed code contract (step 4), with its own fixture tests.

## The workflow

### 1. Resolve what to merge

- **PR ids given** → use them. **A branch given** (or none → current branch) → the PR helper's merge mode looks the id up from source + dest (errors clean on 0 or >1 open PRs). The dest is the service's integration branch from the project's branch table; staging PRs target `staging`.
- **An older PR: measure what it would still change today, via the computed merge.** Part of it may already have landed through a sibling branch, leaving residue its title no longer describes — and the merge stays clean, so nothing warns you. Neither plain diff answers this: `origin/<dest>...origin/<source>` shows what the PR added when it was cut, and the two-dot tip diff counts everything `dest` gained since as the PR "removing" it. After a `git fetch`, diff `dest` against the merge result — empty means nothing is left to land:
  ```
  TREE=$(git merge-tree --write-tree origin/<dest> origin/<source> | head -1)
  git diff --stat origin/<dest> "$TREE"
  ```
  Whether the residue is still worth merging is a separate call from whether it merges.
- **Identify the destination env(s)** from the dest branch(es) — this drives the gate and the QA target (step 6). The integration branch (e.g. `dev`) = dev; `staging` = staging; the default branch = prod.
- **Batch (multiple PRs)** → establish **dependency order** before merging anything: migration/backend first, then the API code/consumer that calls it, then the frontend last. Order not obvious from the diffs → ask.

### 2. The gate

Apply the escalating gate above for **each** destination env in scope. Don't proceed past this step for any env you lack a clear go-ahead on.

### 2b. Pre-merge-E2E services — read the branch's own E2E run first

If a service runs its E2E suite on branch pushes **before** merge, and nothing after the merge runs it again, the branch's own E2E run is the only E2E verdict a change ever gets; read it before merging. (Promotion PRs between env branches have no such run — skip. Services that run E2E after the merge get it inside the deploy pipeline step 4 watches.)

From inside the service repo, get the source branch's latest pipeline with the CI status helper, and confirm that pipeline's revision is the PR's head commit — a verdict on an older commit is stale.
- **E2E job success** → green isn't clean yet: count screenshots in its artifacts (the CI API's job-artifacts listing, paths containing `screenshots`). Zero → clean. Any → a test failed and passed on retry; name it as a flake in the report and proceed.
- **Failed** → classify each failing test with `/e2e`'s red-diagnosis taxonomy (environment / flake / outdated-by-intent / pre-existing / caused-by-diff); the CI provider's test-results API filtered to failures lists them. **Caused by the diff → don't merge**; the fix goes through a fresh `/ship`. **Outdated by intent → hold too**: the spec fix rides this PR before it merges, or every later branch inherits the red. Anything else → ⚠️ with the caveat, and merge on the go-ahead.
- **Still running** → background-watch it (the CI watch helper, pinned to the head SHA and the E2E workflow) and decide when it lands; don't merge ahead of a verdict that's minutes away.
- **No pipeline or no E2E job for the head commit** → say "no pre-merge E2E verdict" and proceed.

### 3. Merge — in dependency order, gate-per-merge

First, from inside the service repo, note the dest branch's current pipeline number with the CI status helper — step 5's pre-merge baseline. **If that pipeline is still running** (another merge's deploy), watch it to terminal with the CI watch helper (pinned to its SHA) before merging. Two deploys to one env race: whichever server deploy finishes last is what serves, while CI shows green for both. Then merge with the PR helper (by PR id, or by source + dest), with a message naming the branch and PR number.

- Default strategy is a merge commit (matches repo history). The source branch is closed on merge by default, but the helper forces that off when the source is an env branch (dev, staging or prod), so a promotion merge can't delete one. **Don't keep a feature-branch source open by default** — feature, fix, chore and release branches close on merge; the helper already protects the env branches. Keep one open only when the user says it will be reused.
- On success it prints `state=MERGED`, the merge summary, and the **bare merge-commit SHA on its last line** — capture it; step 4 pins the pipeline with it.
- **Batch = gate-per-merge, NOT merge-all-then-watch.** Watch each merge's deploy green (step 4) before merging the next dependent PR — later code depends on the earlier deploy being live (e.g. code that reads a column a migration just added). Independent PRs may overlap; when in doubt, serialize.

### 4. Watch CI to green (deploy verification)

Merging triggers the deploy pipeline, so this watch *is* the deploy verification. From inside the service repo, run the CI watch helper **backgrounded** (`run_in_background`) on the dest branch, pinned to the merge SHA from step 3, and read its output when it completes.

It watches exactly **one** pipeline — pinned by merge SHA, or by the pre-merge pipeline number as a baseline when there's no SHA — and refuses to run unpinned, because right after a merge the branch's newest pipeline is still the previous, already-green one. It decides the verdict in a single expression (green only when every workflow is `success`) and reports API failures as failures. The last line is the verdict; the exit code is the contract:

| exit | means | next |
|---|---|---|
| `0` | green | step 5 |
| `1` | a workflow failed | it prints the log-fetch command for each failed job; step 5's red-workflow diagnosis |
| `2` | timeout (default 45 min; set it above your slowest deploy-plus-E2E run) | not a failure — report "still running after Nm", then re-run the watch or hand back the pipeline link |
| `3` | awaiting manual approval | it prints the approval job and how to approve it; approve only if the user authorized the deploy that gate guards |
| `4` | no pipeline for the pin within ~3 min | a dropped webhook: re-trigger a pipeline on the branch, then re-run the same watch (the triggered pipeline builds the branch head, i.e. the merge SHA). **If the repo deploys on tags**, this is expected: the merge alone deploys nothing — raise the tag push as the next action |
| `5` | CI API unreachable | say so; claim no verdict |

A workflow filter judges only the matching workflows (e.g. the deploy workflow when a sibling test workflow is noisy); timeout and interval tune the wait. **Don't hand-roll a poll loop** — ad-hoc loops are how false greens and silent no-ops ship; fix the helper and add a test instead. **Known gaps:** after you rerun failed jobs, some CIs keep the failed attempt and the rerun under one workflow name, so the watch keeps reading FAILED — until the helper can pin the rerun attempt, follow the rerun's job with a bounded status check via the CI API and say so in the report. If the repo deploys on tags, a tag-triggered run has no branch, so the watch can't pin it (exit 4) — find it in the CI's run list and poll it until it waits for approval or goes terminal. A run that's queued with no jobs started is CI queueing, not a failure. During a CI-provider incident status lags too: a job can read blocked while its detail shows it done, and an approved step can still read as awaiting approval for minutes (exit 3 again). Trust job detail and the deployed revision; re-sending an approval is harmless.

**The wait owes a hold report.** If backgrounding the watch ends the turn with nothing else callable, emit `/report`'s **mid-flight variant** (what merged, what's deploying, what it gates) instead of a bare "polling CI." Non-terminal by contract: go straight to step 5 the moment the watch reports.

### 5. Verify — prove it live, and diagnose red before judging it

**A green pipeline means a job exited 0, not that the new artifact is serving.** Before step 6, prove it by function:

- **Probe what the change affects.** A `curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}"` matrix over 3–5 affected routes is enough; capture it **before** the deploy lands for an unambiguous before/after. For a frontend, a served bundle-hash flip works too.
- **Ask the deploy platform which revision is serving** (e.g. `kubectl rollout history`, your cloud's revision or deployment list, or your host's releases list) — against **the env that just deployed** (checking a dev deploy against prod shows no new revision and reads as a false red). List the serving revision plus the last few with their creation times: the previous revision's date also exposes a deploy that has been silently stale.
- **Verify the end state, not a mid-flight sample.** Any deploy step that updates many resources in sequence looks half-reverted mid-run. Wait for the workflow to go terminal, or poll until *every* resource satisfies the assertion; tell CI's writes from yours by each resource's last-updated timestamp.
- **Trust the API over the CI web UI**, which can show a stale "Running" for a finished workflow.
- **Env unreachable** (IP allowlist / WAF, no session) → running the thing still beats inspecting it: re-trigger a pipeline and let its own steps answer.

**A red workflow is diagnose-first, not an automatic 🛑.** Pull the failing job's output with the CI provider's MCP or API, or the CI status helper's log fetch — a FAILED watch already printed that command for each failed job. Then:

- **Before calling a red job "pre-existing" or "unrelated", check the PR branch's own pipeline AND the dest branch's pre-merge pipeline** (the number from step 3), reading each one's **full** job list:
  - green on the branch, red on dest pre-merge → pre-existing on dest.
  - red on the branch → the branch brought it (or never fixed it) — not pre-existing.
  - green on both → the merge combination broke it; treat it as caused by the change.
  - no branch pipeline ran that job → the branch baseline is unknown; say so instead of calling it unrelated.
- **Infra / CI-image issue unrelated to the change, with the deploy job green** → **✅ with a caveat**, flagged as a team CI issue separate from this change.
- **A real failure caused by the merged change** → 🛑. The fix goes through a fresh `/ship`/`/work` cycle so review and gates run again — not a quiet re-push.
- **A red E2E job** → classify each failing test with `/e2e`'s red-diagnosis taxonomy before anything above: most E2E reds have turned out to be environment or flake.
- **A green E2E job** (a post-merge suite) → green isn't clean while the suite retries failed tests: count screenshots in its artifacts. Any → name the retried tests as flakes in the report; not a stop.

### 6. Post-deploy QA — target inferred natively (skip `noqa`)

A second sanity pass on the **deployed** code, against the most prod-like env that just went green:

- **Staging dominates dev.** Merged to staging (or dev *and* staging) → **`/qa staging`**. Merged only to dev → **`/qa dev`**. Step 4 already confirmed the deploy is green, so the ordering is automatic.
- **Merged to prod (the default branch)** → never mutational `/qa` on prod. Hand off to a read-only post-deploy prod smoke check with the scope hint instead (the user logs into prod themselves). A composite driving the full promotion ladder passes `noqa` and runs that smoke check itself, so this only fires for a standalone prod merge.
- **Skip only when nothing the change does reaches a screen** — config, docs, test-only, or backend code no page calls → note *"no UI surface — CI-green deploy is the proof"* and go to the report. A backend change a page renders (an API field, a validation) gets the pass: the deployed env already runs the whole stack, so it's cheap here. `/qa`'s Step 1 owns the test.
- **Run it:** invoke `/qa <env>` (a target implies `run`) with the scope hint — it drafts the scenarios and walks them via `/devtools` against the deployed env. `qa dev`/`qa staging`/`noqa` override the inference.
- **QA gate:**
  - **Clean pass** → ✅ verified end-to-end.
  - **A regression on dev/staging** → 🛑 the code is **already deployed** there but broken. Surface loudly: *"deployed to <env> but QA found X — do NOT promote to prod; fix needed."*
  - **`/devtools` unavailable** → say so; the CI-green deploy still stands as the proof, but flag the QA gap honestly.

### 7. Show what's live — /before-after (skip if the QA was skipped)

If step 6 ran a QA pass with any UI surface, invoke `/before-after` with the scope hint. It answers **"what's actually live on the deployed env"** — the page worth having when someone asks next week whether a fix went out. Frames come from the step-6 pass; don't re-drive the browser. `/before-after` never gates and returns one line for the report. No UI surface, `noqa`, a QA that couldn't run, or `/before-after` not installed → skip it and say so.

**Auto-open the sheet only when the env that just deployed is staging** — prod-like data makes it the authoritative before/after, and it lands while the user is away mid-ladder. On a **dev** hop, return the path and leave it.

### 8. Tear down this session's worktree (only if the merge landed it)

**This is the first moment teardown is provably safe:** before the merge you may still need to push a review fix from that tree; once the PR merges, the tree is disposable. Run it only when **both** hold:
- This session is working out of (or spun up) a manual worktree under the worktrees dir — check `git rev-parse --git-common-dir` / `git worktree list`. A main-checkout session has nothing to tear down → skip silently.
- **A PR merged in step 3 carried that worktree's branch.** Merged something else, or nothing merged (gate refused / CI failed / QA regression) → skip. Never tear down a tree whose work didn't land.

Tear down **only this session's tree** with the project's worktree-cleanup tooling — never a sweep-all mode, which touches trees other sessions own. Re-verify safety first (no uncommitted or unpushed work) and never `--force`, so a **HOLD** is a legitimate outcome — report it and move on; don't clear the blocking files to force removal.
- **Build artifacts are not "uncommitted work."** A tree that ran a dev server usually holds logs, generated files or installed dependencies that read dirty and HOLD. Say so plainly; the user can clear them and re-run the cleanup.
- **Removing the tree deletes the directory the shell may be sitting in.** Run this *after* everything else in this leg; if the cwd is inside that tree, `cd` out first.

Skip entirely under `nested` if the composite will continue working in that tree (e.g. a promotion-ladder composite still has a staging or prod hop to run) — the driving composite tears down at *its* end, not mid-ladder.

### 9. Merge-and-Verify Report (terminus)

```
## Merge-and-Verify Report — <scope>
**Merged:** <PR #N <repo> <source→dest> · merge_commit <sha7>> (· batch: #N→#M in dependency order)
**Pre-merge E2E:** <branch E2E job on <sha7> — clean / N retried (flakes: …) / red: <verdict> / no verdict — or "n/a (this service runs E2E post-merge)">
**CI:** <pipeline #X on <branch> — green ~Nmin / FAILED at <job>: <why> / awaiting approval: <job> / timeout / no pipeline> (+ retried E2E tests, if any)
**Live:** <how it was proven — route probe / bundle hash / serving revision <name> on <env>>
**QA:** <env — clean, N scenarios / findings / skipped: no UI surface / skipped (noqa) / 🛑 couldn't verify: reason>
**Shown (/before-after):** <proof sheet: /abs/path (opened | path only)> — or "skipped: <no UI surface / noqa / QA couldn't run>"
**Worktree:** <torn down: <slug> / HOLD: <slug> (<why>) / n/a — main checkout>
**Verdict:** <✅ deployed & verified on <env> / ⚠️ deployed, caveat: <e.g. E2E red on CI-image issue> / 🛑 <what stopped it>>
**Next:** <e.g. promote dev → staging / push the release tag (if the repo deploys on tags) / nothing — done>
```

**Under `nested`:** produce the same content but hand it back to the composite as mid-pipeline input — don't end the turn on it.

## Guardrails

- **Don't fake verification.** CI couldn't be watched, the artifact couldn't be proven live, or `/qa` couldn't run → say so in the report; don't claim "verified."
- **One terminus: the Merge-and-Verify Report** (or hand back under `nested`).
- **Don't expand scope.** Out-of-scope problems you trip over → the report's Next line, not this leg.
