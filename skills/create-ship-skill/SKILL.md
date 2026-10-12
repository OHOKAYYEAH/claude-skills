---
name: create-ship-skill
description: "Author a project's shipping pipeline: a project-scoped land-and-verify leg (/qa-and-deploy, /qa-and-land or /qa-and-pr, named for what the project actually does) that QAs in a real browser via /devtools and runs the covering E2E specs; where it earns one, a project /ship that chains ticket → front stop → /work → a who-can-resolve gate → that leg → /before-after; and for PR-gated projects, a post-review deploy ladder that takes a reviewed PR up every env. Fire ONLY on an explicit request (\"create the ship skill for this repo\", \"set up /qa-and-deploy here\", \"give this project a shipping pipeline\"), never because a repo lacks one: it writes files and encodes a workflow. Asks first whether the project warrants a pipeline at all, reads the repo before interviewing, and asks only what it can't read: where the artifact runs, how to PROVE a deploy is live, and the irreplaceable human gate. NOT /create-skill (general skill authoring), NOT /qa or /devtools (the primitives the leg chains)."
disable-model-invocation: false
argument-hint: "[optional: the project path, or a hint like \"no deploy target\" / \"PR-gated\"]"
---

**Run only on an explicit ask** ("create the ship skill for this repo", `/create-ship-skill`) — never because a repo lacks a pipeline. It writes skill files and encodes a workflow, so a spurious run has teeth.

Author the shipping pipeline for the project in scope. The output is **one to three
project-scoped skills** in `.claude/skills/`:

1. **A land-and-verify leg** — the half `/work` deliberately stops short of: run the project's
   gates, verify the change in a real browser through `/qa run` → `/devtools`, run the durable
   E2E specs that cover the diff, take whatever human-judgment stop the project needs, then
   commit and land.
2. **A `/ship`** — a thin composite: resolve the ticket → (front stop) → `/work` → a gate on its
   super-review verdict → the land-leg → `/before-after` proof → one report at the end. Emitted
   **where it earns one** (step 5).
3. **A deploy ladder** (a project `/rollout`) — only for PR-gated projects with more than one
   deployed env: the post-review leg that takes a reviewed PR up every env, verifying each hop.
   Offered, not assumed (step 6).

This is the specialized sibling of `/create-skill`. That skill authors *any* skill from an
interview; this one authors *this specific pattern*, which is worth its own tool because the
pattern is invariant while its parameters are wildly project-specific — and because getting those
parameters wrong produces a pipeline that lies about what it verified.

**Read real ones before drafting.** Existing pairs share one skeleton with different
land-legs, and reading them side by side is how you see which parts are structural and which
are parameters. Read any `/ship` pairs you already have in other projects' `.claude/skills/`,
plus the reference set in this collection's `examples/` if you have it: `ship` + `qa-and-pr`
(with `e2e` and `pr` as the atoms the leg chains), and the post-review ladder `rollout`,
`merge-and-verify`, `promote`, `prod-ready` and `smoke-prod`. Two shapes worth knowing:
- **Local-QA-first, PR-gated** (the examples) — QA locally, open the PR; CI deploys after a
  human reviews + merges, and the post-review ladder verifies each env up to prod.
- **Hosted, two-branch** — local browser QA → land on `staging` → QA the staging deploy; prod
  moves only at a manual, batch-reviewed release step. The front stop (spec + mockup) before the
  build, a light route for low-risk diffs, a look-gate before the push, deployed-SHA assertion
  after.

The two shapes have converged on one `/ship` skeleton; where they still differ, the difference
is a real project parameter (where QA runs, what lands where), not a style choice.

## 0. The warrant gate — does this project need one?

**Ask before building.** Not every repo does, and a pipeline over a repo with nothing to verify
is pure ceremony that will rot unread.

- **Warrants one:** a runnable artifact with a browser surface — a web app, a site, a game, a
  dashboard. Something `/devtools` can actually walk.
- **Warrants a reduced one:** a CLI, a library, a data pipeline, a cron. There's no browser walk,
  so the leg is gates + land, and the "QA" is running the thing on real input and reading the
  output. Say so plainly rather than staging a browser phase that can't fire — and consider
  whether that's just `/work` plus a commit, not a skill.
- **Warrants none:** a content or notes repo (prose, data, config), or anything where landing is
  `git commit && git push` and there is nothing to verify. **Say that and stop.** Recommending
  against your own skill is the correct output here.

If the project is borderline, ask the user — one sharp question, not a survey.

## 1. Discover — read the repo before asking anything

Everything in this list is readable. Asking about it wastes the user's attention and signals you didn't
look. Gather, then bring only the gaps to step 2.

- **Package/scripts** — `package.json`, `pyproject.toml`, `Makefile`. What are `dev`, `build`,
  `test`, `typecheck`, `lint`? Are there project-specific gates already scripted (an audit, a
  bench, an env-gated suite)?
- **The dev server** — how is it started, what port, is it bound to localhost or all interfaces,
  is there a helper script (`./dev-frontend.sh`) or is it a raw framework command? Is one
  **already running**? Multi-app repos and worktrees shift ports — never hardcode the default.
- **The deploy target** — a `vercel.json`, `railway.toml`, `Dockerfile`, `fly.toml`, a GitHub
  Actions deploy workflow, or nothing at all. **Nothing at all is a real and common answer.**
- **Git convention** — `git remote -v`, default branch, whether history shows direct-to-main
  commits or merge commits from PRs. Don't assume; read the log.
- **CLAUDE.md** — repo-root and any nested. This is where the project's hard rules live
  (prod-first, shared-checkout discipline, legal guardrails). If there ISN'T one, note it — the pipeline's rules may be the first written record, and that's worth telling the user.
- **Existing skills** — `.claude/skills/`. A `/worktree`, `/close-ticket`, or `/sync-main` already
  present should be **chained, not reimplemented**.
- **Test cost** — how long does the suite actually take? A slow suite changes the pipeline's shape
  (targeted subsets while iterating, one full run before the push) and belongs in the emitted
  skill as a number, not a vibe.
- **Parallel-session risk** — is this checkout routinely shared? Directories owned by other work
  make stage-by-path non-negotiable and worth naming explicitly.

## 2. Interview the axes you can't read — chain /interview

Invoke **`/interview`** for what's genuinely open. Let it pick the ~4 that matter; don't ask what
step 1 already answered.

The axes that determine the pipeline's shape:

**a. Where does verification happen — before or after the push?** This single answer picks the
whole shape, and the rule is: **verify wherever the code actually runs.**
- Local is fragile / the real thing only exists deployed → **deploy-then-verify**: push to a
  non-prod target, QA that deploy, promote later. (e.g. land on `staging`, then a manual release step)
- Local *is* the artifact, no hosted target → **local-only**: all gates before the push, nothing after. (e.g. a local game or desktop app)
- There's a human review gate → **local-verify, then PR**: QA locally, then open the PR.
- Both? Encode it honestly — a hosted project can QA every diff locally (FE-only against the deployed
  staging backend, backend diffs against a local backend on a non-prod DB), then QAs again on
  staging after the land. A pipeline can branch on scope; it just has to say which branch it took.

**b. How do you PROVE the deploy is live?** Only for hosted projects, and the naive answer is
wrong in a way that costs hours. **A 200 from a health endpoint is not proof your build shipped** —
a failed build leaves the *previous* deployment serving traffic, so health stays green while your
commit never went out. Get the project's real answer: assert the **deployed commit SHA** matches
what you pushed (`railway status --json` → `latestDeployment.meta.commitHash`,
`vercel inspect`, the platform's equivalent). Encode that command in the emitted skill. Also
capture: how long the deploy takes, and how to read a *failed* build's log (CLIs often default to
the last *successful* deployment, so you must pass the failed id or you'll read a stale green log).

**c. What is the irreplaceable human gate?** **The highest-value question in this interview.**
Every project has one thing automation cannot judge, and the pipeline's job is to stop for it
rather than paper over it with a green suite.
- A hosted web app: **look** — the user approves a desktop+phone proof sheet before the push.
- A game: **feel** — the user *plays* it, because goldens are regression tripwires, not fidelity
  proofs; a green suite proves the game loads, never that it plays right.
- A data pipeline's might be *"does this output look sane"*; a writing tool's might be *"read the
  generated copy."*

Whatever it is: it becomes a **real turn-ending pause** in the leg, with a **named bypass token**
(`nopreview`, `noplay`) that is **recorded in the report** when used. A silent skip of the human
gate is the failure mode this whole question exists to prevent. Also pin down **when it fires** —
which diffs have a delta it can judge — so it isn't asked on a docs change.

**d. What gates would a generic land-leg have no idea about?** Mine step 1 and the conversation
for these; they're what makes the emitted skill worth more than a template. Real examples:
a legal/IP check on the built bundle plus the one *known* benign hit so it isn't re-diagnosed
every ship; a path that must return 403; a committed artifact whose diff is the review surface;
an env-gated slow suite; a suite that must run foreground because a backgrounded run gets killed
and reads as a pass; staging by path around a parallel session.

**e. The risk-surface taxonomy for proportionality.** Which directories are heavy (a contract,
determinism, auth, money, migrations), which are light (docs, copy, comments)? Classification is
**by surface, not size** — a 3-line auth or timing change is heavy; a 200-line copy change is not.

**f. Close-out.** What's left standing after a land — a worktree, a branch ref, a ticket, a dev
server? Chain the project's existing skill for each where one exists.

**g. Does a front stop earn its place?** Some projects want intent and look approved *before* the
build, because a wrong direction costs the whole build: a frozen spec (`/spec nested`) for
non-trivial scopes, and a `/mockup` for scopes that introduce or restructure a rendered surface.
If yes, it is one of `/ship`'s planned pauses (alongside the human gate and the gate's one real stop), fires only
when there's something new to approve, and has a bypass token for the look half.

**h. Tracker and after-merge.** Does work here live on a board (chain `/ticket` up front, carry the
key into the PR and the close-out)? For a PR-gated project: who merges, how many envs sit between
the merge and prod, and how is each hop proven live? That's the raw material for step 6.

## 3. Name the leg for what it actually does

The name is a promise about the workflow. Pick from what step 2a established:

| shape | name | because |
|---|---|---|
| hosted, verified after the push | `qa-and-deploy` | there is a deploy, and QA follows it |
| no hosted target, verified before the push | `qa-and-land` | it lands; nothing deploys |
| PR-gated, verified before review | `qa-and-pr` | it ends at a PR, not a merge |

Don't reach for `qa-and-deploy` out of muscle memory. A leg named "deploy" in a repo with no
deploy target sends the next reader hunting for a step that doesn't exist — and the cross-project
consistency it buys isn't worth a name that lies. If the user prefers one name everywhere, that's their
call to make explicitly, not yours to assume.

## 4. Draft the land-leg

Keep the skeleton; the project supplies the parameters. Sections, in order:

0. **Gates** — cheapest first, each one a *stop* rather than a note: typecheck, suite, build, plus
   the project-specific gates from 2d. Name the real commands and the real costs.
1. **Serve** — check for an already-running server before starting one; note the port it actually
   printed; give the URL the user would actually open (which on a server bound to a
   LAN/VPN address is not `localhost`).
1.5 **Seed if thin** — a local DB too empty to exercise the change makes the walk a lie. Check
   the rows the scope needs; when thin, seed it, reading a richer non-local copy **read-only** and
   writing nowhere but local. Skip when the scope has no data dependency.
2. **Browser walk** — `/qa run <target>` with the scope hint. Seed it with **project-specific
   scenarios** and the **real DOM ids/selectors** you read in step 1. This is what separates a
   useful leg from a generic one: a walk that names the actual surfaces beats "test the app."
   When `/ship` hands down spec acceptance criteria (`walk: <items>`), walk each one and report a
   verdict per item. Keep the frames: `/ship` turns them into the proof sheet.
2.5 **Durable specs** — if the project has an E2E suite, run the specs that cover the diff (the
   `/e2e` example shows one such step): diagnose every red before judging it (environment / flake
   / pre-existing / caused-by-diff), and only a caused-by-diff red stops the leg. Graduating a
   verified walk into **at most one** new spec per ship keeps the suite growing without becoming
   the ship.
3. **The human gate** from 2c — a real pause, with the bypass token and how to present it
   (pictures go in one proof sheet — `/before-after` builds it, if installed).
4. **Land** — stage **by path**, never `git add -A`; re-verify the staged set; the project's commit
   convention and trailers; the branch/PR convention; and the divergence rule (rebase onto origin,
   **re-run the gates because the tree moved**, fast-forward push, never force-push).
5. **Report** — one terminus, with a line for each gate so a skipped one is visible, and an
   `E2E:` line printed verbatim (specs run, reds, graduated) as evidence the suite actually ran.

**Frontmatter:** `disable-model-invocation: false` (it must be chainable by `/ship` — a `true`
inner skill balks and short-circuits the chain), and an `argument-hint` carrying the scope hint,
the `nested` hand-back token, and the human-gate bypass token.

## 5. Draft /ship — where it earns one

**Emit it when** the project's build path is `/work` and the land-leg has real gates to sit behind.
That's most projects that warranted step 0. **Skip it when** the land-leg is trivially short, or
the build isn't `/work`-shaped — a two-skill chain the user runs ad-hoc doesn't need a standing
composite, and `/create-skill`'s bar applies here too.

Keep it **thin**: classification + gate + report, nothing else. If you're writing leg-work into
`/ship`, it belongs in the leg.

0. **Base freshness + target** — `git fetch`, name the target branch (it sets the base), read
   the drift, route (fast-forward, or isolate in a worktree if the project has a `/worktree`
   skill and the drift/parallel-session risk warrants it). For a slow local stack, you can also
   fire the env boot **in the background** here, so it's warm by the gate. That warm-up is never
   a gate: it never waits and never reports, and the land-leg owns the real bring-up.
0.2 **Ticket** — `/ticket` with the scope hint, if 2h said work lives on a board. It dedupes, so
   the usual answer is "already tracked as X"; carry the key to the PR and the close-out. Never a
   gate: a tracker hiccup is a clause on the report's Next line.
0.5 **Proportionality** — classify the risk surface from 2e and **state it in one line before the
   build**, so a misread surfaces now. Two documented routes: full (`/work`) and light (inline
   edits + suite/typecheck + one `/code-review low`). The light route's **dropped gates get named in
   the report** — improvised gate-dropping is what this step exists to replace. **Unsure → heavy.**
   Include the escalation valve: the light route is revocable mid-flight.
0.6 **Front stop** — only if 2g said so. Freeze the spec and/or show the mockup in **one** message
   ending on one question; resume on the go-ahead. No stop when nothing new needs approving.
1. **Build** — `/work noreport` (+ ticket key or spec location, + scope hint, + `tdd` if passed).
   `/work` owns the whole front half: plan + `/review-plan`, its own `Decision:` lines, build
   test-first, `/spec-check`, `/mutate` (+ `/test` when the diff has none), `/super-review` in a
   fork, and the main `/triage` pass while the diff is still open. Include a **resume entry**: if
   `/work` already finished this scope in-session with a recap and no edits since, skip to the
   gate with a printed `Build: resumed` line, instead of rebuilding or improvising a skip.
2. **The gate** — it routes on **who can resolve a finding, never on its severity**:
   - **✅** → **your immediate next action is the land-leg call, with no prose first.** This is the
     documented stall: `/work` hands back on a satisfying green verdict and the model wraps up the
     turn there, leaving the work built but unlanded.
   - **🔧 fixes owed / `[caller-resolvable]`** → not a gate. Decide each (a `Decision:` line), fix,
     re-run `/super-review` on the fixed diff, continue. You hold more context than the fork did.
   - **`[needs-user]`, pre-existing and not widened** → land anyway; carry it to the report's Next
     line as a triage candidate. The hole is live whether or not this ships.
   - **`[needs-user]`, introduced or widened by this diff** → the one real stop. Deliver the Ship
     Report with the finding, the recommended option and one question **in the same turn**; never
     end a turn mid-investigation. If the leg ends at a PR, a question about intended behavior (not
     a defect) rides in the PR description instead of stopping the build.
   - Also read the spec-check outcome: a carried gap is not-✅; built-differently items are FYI;
     QA-walk items go down to the leg as `walk: <items>`.
3. **Land** — `<leg> nested` (+ scope hint, + walk items, + bypass token if passed). The leg's
   gates are `/ship`'s gates; if it stops, `/ship` stops. A real QA regression goes back through a
   fresh `/ship` cycle, never a patch-and-repush, so the review gate sees the fix.
3.5 **Show + close out** — `/before-after` builds one proof sheet from the leg's frames (it never
   gates; a backend-only diff returns one honest clause). Then the close-out from 2f.
3.7 **Triage sweep-up** — only candidates that didn't exist when `/work` triaged (things QA or the
   E2E step found). The one-new-ticket budget is per *ship*, not per call; nothing else in the
   pipeline files follow-ups.
4. **Ship Report** — the single terminus, one line per stage so a skipped one is visible:
   Ticket · Gates (route) · Spec · Built · Verified (incl. the `E2E:` line) · Shown · PR or
   Shipped · Triage · Next. For a PR-gated project, Next points at the deploy ladder.

## 6. The deploy ladder — offer it for PR-gated projects

`/ship` ends at PR-opened, by design: that's the review moment, and **`/ship` never merges.** In a
PR-gated project with several envs (say dev → staging → prod), the post-review half is its own
composite (a project `/rollout`; the `/rollout` example shows one), kicked off by the user's
go-ahead on the Ship Report's Next line. Offer it when 2h found more than one deployed env; skip
it when merge-to-main *is* the deploy.

Its shape, as in the `examples/` ladder: **merge + verify the first env** (watch CI, prove the
commit is live, QA there) → **promote** to each next env as a merge PR with a pre-check of its true
size → **a prod-readiness gate** rebuilt from durable state (git, CI, migrations, config), never
from memory → **the one hard stop: the user's go for prod** → promote to prod → **read-only prod
smoke**. Each hop is its own atom so it can also run alone. Emit only the hops the project
actually has.

## 7. Verify + hand off

- Folder name == `name:` for each emitted skill. Frontmatter valid. All `disable-model-invocation: false` (the `examples/` carry `true` only because they're read-only).
- **`/ship`'s description claims the default-builder role** ("the default builder in <project>: any
  ready-to-build ticket goes here, not to standalone /work"). Without that, the model picks the
  shared `/work` for "let's build X" and the work stops unlanded.
- **The hand-back tokens are load-bearing, not decoration.** `/work noreport` and `<leg> nested`
  exist so neither leg emits a satisfying terminal block that stalls the pipeline. If you drop
  them, `/ship` reliably halts mid-chain. Confirm both are wired.
- **Location is project scope** — `.claude/skills/` in the repo, checked in. These chain shared
  atoms (`/work`, `/qa`, `/devtools`), which is the correct dependency direction; **never** push
  a project's shipping policy down into your user-level `~/.claude/skills/`.
- Sanity-check every command you wrote by **running it** — the port, the health/SHA probe, the
  legal grep. A pipeline whose first step is a typo'd script name is worse than none.
- **The Ship Report has a line per stage**, including the ones that were skipped and why. A
  report that only lists what ran hides the gate that didn't.
- Offer `/curate <name>` as a follow-up health check. Suggest, don't invoke.

## Guardrails

- **Recommending against building it is a valid, sometimes correct output.** Step 0 is a real gate.
- **Read the repo before interviewing.** Asking what `package.json` would have told you burns the
  attention you need for the questions only the user can answer.
- **The human gate is the point, not a formality.** Every emitted leg has one, it's a real
  turn-ending pause, its bypass is explicit and recorded. A pipeline that can silently skip the
  one judgment automation can't make is a pipeline that will eventually ship something wrong with
  a green report attached.
- **Never claim verification you didn't do.** The emitted skill must say "stop and report" when the
  deploy is still propagating, the app is unreachable, or the suite didn't finish — and must not
  offer "the tests pass" as a substitute for the behavioral claim. Encode the honest-scope habit
  (unit-tested-only, deferred-to-next-cron, QA'd-local-prod-confirmed) rather than a binary.
- **Don't launder a decision you can make into a question.** The emitted gate stops only for a
  finding the user alone can resolve and this diff introduced. Every other halt is a cost, paid in
  the user's attention, and the halts that end in "yes, do the obvious thing" are bugs in the gate.
- **Findings are decided inside `/work`,** while folding one into the open diff is still cheap.
  The emitted `/ship` sweeps up only what QA found later, inside one budget per ship. A ship that
  leaves four new tickets behind is the failure, not diligence.
- **Stage by path.** Every emitted leg says it. It's the easiest real damage a land-leg can do,
  especially in a checkout shared with a parallel session.
- **Chain the project's existing atoms** (`/worktree`, `/close-ticket`, `/sync-main`) rather than
  inlining their logic. Same reason `/ship` stays thin.
- **Don't over-fit to the most developed example.** It's the most tempting to copy
  wholesale — but half of any real pair is platform specifics (Vercel/Railway/Supabase, a CI
  vendor) and a deploy stance that is *wrong* for a project whose artifact is local. Copy the skeleton and
  the hard-won reflexes (assert the SHA, stage by path, name the dropped gates); re-derive
  everything else from step 2.
