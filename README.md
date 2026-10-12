# claude-skills — a working agent-skills suite

*The skills I use day to day with Claude Code, cleaned up so you can borrow ideas or install the portable ones. Refreshed October 2026.*

> **It's a harness, not 57 loose files.** The skills lean on CLAUDE.md priming, settings.json hooks, MCP servers and a file-based memory system. The catalog is tiered by portability so you know what's drop-in; [SETUP.md](SETUP.md) covers the rest.
>
> **Browsing for ideas (the main use):** clone it somewhere outside your skills directory and ask your agent: *"Read this repo's README catalog and examples/, compare them with my own skills, and suggest ideas worth borrowing."*

---

## Skills are functions

A skill is a folder with a `SKILL.md`: YAML frontmatter (`name`, `description`) and a body holding the procedure. Treat it as a function: a named unit of process with one job and a clear contract, called by name. You call it (`/tdd`), and so do other skills: an orchestrator like `/work` is a function that calls functions. Developers already pull repeated code into functions; skills do the same for the *process* of development, and the principles that make good code make good skills.

## Design principles

1. **Single responsibility.** One skill, one job. Atoms compose; a do-everything skill can't.
2. **Invoke by name; descriptions are a bonus.** These skills are built to be called explicitly, by you or by an orchestrator, not picked by the model from their descriptions. When a description fires a skill unasked, that's often useful, but nothing depends on it (see *Keeping the listing lean*).
3. **Rule of three.** Chain skills ad hoc freely; when the same 3+-skill chain keeps recurring, promote it to a standing composite. Not before.
4. **Structure over pressure.** When a chain breaks, fix the architecture, not with "YOU MUST CONTINUE" in capitals. Explain the why; the model generalizes from reasons.
5. **Orchestrators run autonomously.** A skill that drives a chain (`/work`, `/wrap-up`) runs to the end on its own. It makes the non-critical calls itself, one printed line each (`Decision: X — because Y`), and halts only for an irreversible or prod action, a business call the record can't settle, a finding only you can resolve, or a blocked prerequisite. A halt names the question *and* its recommended answer. A halt you answer with "yes, the obvious thing" is a bug in the orchestrator.
6. **The most complete orchestrator is the entry point.** `/work` is a building block; a project composite on top of it (`/ship` = `/work` → gate → land) is what "build this" means in that project.
7. **Standards live in one place.** A rule two skills apply gets one home, a shared reference file, and each skill keeps a short gist plus a pointer, so the copies can't drift.

## Keeping the listing lean

Every listed description sits in the agent's context in every session, and the listing has a size budget; past it, Claude Code starts dropping descriptions. Since these skills are called by name, most don't need one listed.

- **Name-only for most skills.** `"skillOverrides": { "<skill>": "name-only" }` in Claude Code's `settings.json` keeps a skill invocable and chainable but lists only its name, at no description cost.
- **A short list keeps its description**, and only skills that need it: ones the model should reach for from the situation unasked (`/tdd` before a bugfix, `/blast-radius` before a contract change), or ones you trigger in plain words ("are we done?" → `/done-check`).
- **Name-only lowers self-firing; it doesn't stop it.** The model can still pick a skill by its name, so a safeguard like "run only when asked" goes in the first lines of the body, which loads on every invocation. In the description, it would vanish with the listing.
- **Never set `disable-model-invocation: true` on a skill anything chains.** It stops the model running the skill even when asked mid-prompt, and a chain that reaches it stalls. Keep it for what the model must never start, like a prod release you type yourself.

## Chaining: what keeps a pipeline whole

Atoms compose into orchestrators. These are the lessons from chains that broke:

- **A report-shaped step runs in a fork.** A skill that ends on a report ends the turn; inline in a pipeline that's a `goto`, and the chain dies. Run it isolated (`context: fork`, plus `background: false` when the caller waits on it) and the report comes back as a return value. `/review-plan`, `/super-review`, `/mutate`, `/blast-radius` and `/sec-review` fork themselves.
- **No hidden halts.** Under a caller, a skill hands back one line and returns. A finished-looking block or a "`/go` to proceed" prompt *is* a halt, which is why `/recommend`'s decision rule lives inside `/work` as prose rather than as a chained call.
- **Escalate, never pause.** A forked step can't ask you anything, so what it can't settle comes back tagged `[needs-user]`, and the orchestrator decides whether that's a halt.
- **End on a hard contract.** `/work` always ends on `/report`'s block; `/super-review` on its Recap. Completion is structural, not hopeful.
- **The hand-back carries every field the caller routes on,** and the caller handles every status the inner skill can return, by the inner skill's own rules.
- **Pointers are explicit.** Only the invoked `SKILL.md` loads, so "the /x rules apply here" loads nothing; write `Read <full path>`.
- **Arguments steer; they don't select modes.** Every skill does the right thing with none. Positional arguments are fine where an orchestrator owns the contract.

## Why maintain process when the models keep improving?

- **Capability scaffolding** works around what the model can't do yet. It **depreciates**: every release makes some of it dead weight, and deleting it is a win.
- **Standards scaffolding** encodes what *good* looks like: the definition of done, what to verify, the bar. It **appreciates**: a smarter model follows it more faithfully, so the same skill yields better output.

A frontier model is generically excellent; it doesn't know that *we* require a red test before a bugfix or a blast-radius check on a schema change. Skills carry the part no model release ships. `/succession` runs that sort on each release, so the depreciating half gets deleted instead of applied harder.

## The pipelines at a glance

```text
/ship (project composite — see examples/)
 └─ /work
     1. orient (find or freeze the spec) ─ 2. plan + /review-plan (fork)
     3. build, test-first via /tdd ─ 3b. /spec-check against the spec
     4. /mutate (+ /test when the diff has none)
     5. /super-review (fork)
          /code-review ─ recall-biased sweep ─ comment pass
          ─ /blast-radius + /sec-review when the surface warrants ─ Recap
     6. /triage the side findings ─ 7. /report (standalone only; /ship reports itself)
 └─ gate ─ /qa-and-pr (local browser QA via /devtools, /e2e, open PR) ─ /before-after → /present

/rollout (project composite)
 └─ /merge-and-verify (dev) ─ /promote (staging, verified) ─ /prod-ready gate
    ─ ⏸ your go ─ /promote (prod) ─ /smoke-prod ─ /report
/wrap-up            /done-check ─ clear what a later step can ─ /compound ─ teardown ─ report
```

Every box is also a skill you can run on its own; the pipeline is just the standing order.

## What actually gets used

*Counted from 1,373 Claude Code sessions over 120 days (June–October 2026) by `/harness-audit`'s usage extractor, which reads the session transcripts. "Typed" means I called it; "chained" means another skill did.*

**What I type: a handful of entry points.** `/go` (352), `/report` (133), `/recommend` (76), `/wrap-up` (73), `/notes` (67), `/handoff` (47), `/tldr` (38). The rhythm is propose → accept: a report or `/recommend` names the next move, and `/go` takes it. Most build work starts as `/go` on a "build this" recommendation, not as a typed `/ship`.

**What other skills call.** `/super-review` (148, every one chained), `/merge-and-verify` (148), `/done-check` (130), `/pr` (110), `/compound` (109), `/promote` (93), `/work` (89), `/ship` (77, via `/go`), `/qa-and-pr` (72), `/mutate` (68). That's *skills are functions* with numbers on it: the building blocks are almost never typed, because the orchestrators call them.

**The bread and butter: `/ship`.** 84 runs, 7 of them typed; the rest came from `/go`. One run is `/work` (plan → `/review-plan` → test-first build → `/spec-check` → `/mutate` → `/super-review` → `/triage`) → a gate that stops only for what the user alone can decide → local browser QA plus the E2E specs that cover the diff → a PR → a before/after proof sheet. After review, `/rollout` takes the PR up dev → staging → prod, verifying each hop. `/ship` and its legs are project-bound, so they're read-only examples in [`examples/ship`](examples/ship/SKILL.md). To build your own for a repo, run [`/create-ship-skill`](skills/create-ship-skill/SKILL.md): it reads the repo, interviews only what it can't read, and writes the land-leg, the `/ship` composite and, for a PR-gated project, the deploy ladder.

## The compounding loop

The suite is a codebase, and it earns its keep the same way: each piece of work should improve the system that does the work. `/compound` mines a finished session for durable lessons and folds them back into the skills; `/create-skill` authors new ones; `/curate` audits the repertoire's structure; `/harness-audit` scores each skill against real session transcripts; `/succession` re-grades the whole harness on each model release. Skills that stop earning their keep get archived, not deleted. The industry calls this *compound engineering*.

---

## The catalog — tiered by portability

Each skill links to its folder. **Requires** flags the substrate it needs to actually work (detail in **[SETUP.md](SETUP.md)**). If there's no Requires note, it's drop-in.

### Tier 1 — Drop-in
*Pure reasoning / test / review work. Copy the folder and go.*

**Build & test**

| Skill | What it does |
|---|---|
| [`/tdd`](skills/tdd/SKILL.md) | Write the failing test first, confirm it's red for the right reason, then implement. |
| [`/test`](skills/test/SKILL.md) | Audit a diff for missing in-process tests (branches, boundaries, error paths) and add them. |
| [`/mutate`](skills/mutate/SKILL.md) | Inject realistic bugs into changed code one at a time; tests that don't catch them are blind spots. |
| [`/fortify`](skills/fortify/SKILL.md) | Coverage + mutation hardening for an existing module at rest (not a diff). |
| [`/debug`](skills/debug/SKILL.md) | Systematic root-cause for a bug whose cause is unknown — evidence before theories. |
| [`/work`](skills/work/SKILL.md) | The workhorse orchestrator: plan + review-plan → build test-first via `/tdd` → mutate (+ test) → super-review → triage → report. Runs to the end on its own; halts only on the tiers above. |
| [`/autopilot`](skills/autopilot/SKILL.md) | Scaffold and launch a *safe* autonomous run (`/loop`, `/batch`) that drives a skill across a broad, repo-wide scope. |

**Review & verification**

| Skill | What it does |
|---|---|
| [`/blast-radius`](skills/blast-radius/SKILL.md) | Inverts the telescope: what *unchanged* code (incl. sibling repos) depends on this change? |
| [`/review-plan`](skills/review-plan/SKILL.md) | Critique a multi-phase plan before building: assumptions, sequencing, reversibility. Forked, so it's chain-safe inside `/work`. |
| [`/sec-review`](skills/sec-review/SKILL.md) | Chain-safe, diff-scoped security review. |
| [`/super-review`](skills/super-review/SKILL.md) | The pre-ship review gate, in a fork: native `/code-review` + a recall-biased sweep, a comment pass, then `/blast-radius` and `/sec-review` when the diff touches a contract or security surface. Fixes what's bounded, tags the rest, always ends on a Recap. |
| [`/postmortem`](skills/postmortem/SKILL.md) | Retroactively apply the build + ship gates to work that skipped them. Reads deploy/tracker info from your CLAUDE.md. |
| [`/double-check`](skills/double-check/SKILL.md) | Independently re-derive one claim about system state (what's deployed, what a config says) by a different route before acting on it. |
| [`/confidence-check`](skills/confidence-check/SKILL.md) | Tag each load-bearing claim in a response by source (read / recalled / inferred / assumed) and name the one worth checking. |

**Planning & specs**

| Skill | What it does |
|---|---|
| [`/interview`](skills/interview/SKILL.md) | Interrogate intent before building something ambiguous. |
| [`/spec`](skills/spec/SKILL.md) | Freeze the agreed intent from a brainstorm into a short spec (users, success criteria, in-scope vs deferred) before building. |
| [`/mockup`](skills/mockup/SKILL.md) | Preview an unbuilt UI change as a throwaway static mock, reusing the project's real design tokens. |
| [`/deep-research`](skills/deep-research/SKILL.md) | Wide multi-source web research with every load-bearing claim verified against the fetched text. Needs web search/fetch. |

**Decisions & orientation**

| Skill | What it does |
|---|---|
| [`/recommend`](skills/recommend/SKILL.md) | Options on the table → pick one, commit, say why. Kills decision paralysis. |
| [`/brainstorm`](skills/brainstorm/SKILL.md) | Think a question through before committing: widen the options past your framing, a tradeoff for each, and a pick with why. |
| [`/worth-it`](skills/worth-it/SKILL.md) | Evidence-checked verdict on adopting a tool or stack given your existing setup: replace part of it, add it alongside, or skip it. |
| [`/matrix`](skills/matrix/SKILL.md) | Place one proposed piece of work on the value/effort matrix (do now / plan it / fill-in / don't) with evidence for each axis. |
| [`/go`](skills/go/SKILL.md) | Act on the last recommendation without retyping it. |

**Communication**

| Skill | What it does |
|---|---|
| [`/explain`](skills/explain/SKILL.md) | Unpack what the agent just did, why, and one concept worth learning. |
| [`/contextualize`](skills/contextualize/SKILL.md) | Re-pitch a finding at a lower assumed-context level, rebuilding the background it stood on. |
| [`/report`](skills/report/SKILL.md) | A one-line verdict + icon-keyed status table + numbered Next checklist. |
| [`/tldr`](skills/tldr/SKILL.md) | Compress the agent's last response to the high-signal bits. |
| [`/bigpicture`](skills/bigpicture/SKILL.md) | Zoom out on in-flight work as one page: bottom line, a map of every moving part, and the one mechanism the risk turns on. |
| [`/distill`](skills/distill/SKILL.md) | Distill a transcript, article or file into a TL;DR plus the substance at a set compression, each point anchored to the source. |
| [`/readable`](skills/readable/SKILL.md) | Turn a raw transcript into a readable edition: near 1:1, in the speakers' own words, with a drift check proving nothing was added. |
| [`/steps`](skills/steps/SKILL.md) | Extract the actionable steps from the last response into a who-does-what checklist. |
| [`/notes`](skills/notes/SKILL.md) | Verbatim scratchpad — drop a thought, it formats it, doesn't editorialize. |

**Working on the suite itself**

| Skill | What it does |
|---|---|
| [`/create-skill`](skills/create-skill/SKILL.md) | Author a new skill in house style (atomic, chainable, fork-safe). |
| [`/create-ship-skill`](skills/create-ship-skill/SKILL.md) | Author a project's own ship pipeline: the land-and-verify leg, the `/ship` composite on top of `/work`, and for PR-gated projects the post-review deploy ladder. Uses `examples/` as the model. |
| [`/curate`](skills/curate/SKILL.md) | Health-audit the whole library: overlap, gaps, single-responsibility violations, token cost. |
| [`/harness-audit`](skills/harness-audit/SKILL.md) | Longitudinal usage-and-value audit of the suite from real session transcripts — which skills earn their keep, rated 1–5 with cited evidence. |
| [`/succession`](skills/succession/SKILL.md) | On a new model release, sort every steering passage into standards (keep) vs capability scaffolding (deletion candidate). Read-only. |
| [`/scout`](skills/scout/SKILL.md) | Mine a named external skill creator's public work for principles worth adapting by hand. Installs nothing. |

### Tier 2 — Needs an MCP, a tracker, or CLAUDE.md content
*Work anywhere, but read a connection target or assume a connected tool.*

| Skill | Requires | What it does |
|---|---|---|
| [`/devtools`](skills/devtools/SKILL.md) | Chrome DevTools MCP + a ports/URLs map in your CLAUDE.md | Drive a real browser to QA, reproduce bugs, chase console/network errors. |
| [`/qa`](skills/qa/SKILL.md) | (when run) chains `/devtools` | Draft a behavioral browser-QA scenario list; `/qa run` walks it. |
| [`/present`](skills/present/SKILL.md) | `python3` (+ the `markdown` and `pygments` packages for docs); engine bundled in `bin/` | Put a finished thing in front of you as one styled HTML page: screenshots become a captioned sheet, a markdown doc a rendered read-only copy. Opens a tab, sends a file when headless, or publishes an Artifact. |
| [`/before-after`](skills/before-after/SKILL.md) | `/devtools` for live frames, `/present` for the page | Capture before and after frames of a change and hand them to `/present` as one proof sheet. |
| [`/ticket`](skills/ticket/SKILL.md) | a tracker (e.g. Jira via MCP) or an in-repo tickets dir | File (or find) the ticket for a unit of work — dedupe first. |
| [`/setup-ticketing`](skills/setup-ticketing/SKILL.md) | — (installs it) | Install a lightweight, AI-first, in-repo ticket system. |
| [`/setup-worktrees`](skills/setup-worktrees/SKILL.md) | — (installs it) | Install a per-session git-worktree convention (plus its teardown skill) into a repo. |
| [`/triage`](skills/triage/SKILL.md) | a tracker the agent can search and write; without one it drafts tickets for you to file | Batch-decide which in-flight findings earn a ticket: dedupe first, fold quick wins into the open diff, log the moderate ones to `FINDINGS.md`, file at most one new ticket per pass. |
| [`/spec-check`](skills/spec-check/SKILL.md) | a tracker/chat/email MCP + your projects listed in its `references/sources.md` | "Did we build what was actually asked for?" — rebuild the final agreed spec from its sources and compare it to what shipped. |
| [`/envset`](skills/envset/SKILL.md) | Linux shell | Get a third-party API key from you into an env file without it passing through the chat, then verify it. |

### Tier 3 — Needs the harness (hooks + the memory system)
*These assume parts of the substrate exist. See [SETUP.md](SETUP.md) before expecting them to work.*

| Skill | Requires | What it does |
|---|---|---|
| [`/done`](skills/done/SKILL.md) | the `done-rename.sh` UserPromptSubmit hook | Close out the session: retitle it `[DONE] …` instantly (the hook does the real work; the skill is the fallback). |
| [`/wait`](skills/wait/SKILL.md) | the same hook | Tag the session `[WAIT] …` — blocked on an outside answer, not on code. |
| [`/done-check`](skills/done-check/SKILL.md) | — (reads git across nested repos) | "Are we done, safe to close?" — a verdict plus only the loose ends that would be lost. |
| [`/wrap-up`](skills/wrap-up/SKILL.md) | chains `/done-check`, `/triage`, `/compound` | Take finished work all the way to a tidied, codified, safe-to-close state. |
| [`/compound`](skills/compound/SKILL.md) | the file-based memory system | Mine a finished session for lessons, fold them back into skills/memory. |
| [`/tend-memory`](skills/tend-memory/SKILL.md) | the memory system | Losslessly compress the always-loaded memory index when it's over budget. |
| [`/retire`](skills/retire/SKILL.md) | the memory system | Archive stale memory entries — out of the loaded index, kept on disk. |
| [`/tangent`](skills/tangent/SKILL.md) | tmux (Linux `/proc`, or `ps` on macOS) | Chase a side thread without blocking this one: fork the current session into a new tmux window with its full context and launch flags. |
| [`/handoff`](skills/handoff/SKILL.md) | session memory + CLAUDE.md auto-load | Decide the context move (continue / compact / fresh) and write the paste-ready handoff. |

### Shipped as its own plugin

A skill meant to be *used* rather than browsed ships as a separate plugin, so you can take it without the suite. Like the suite it installs turned off: turn it on after you add it. It lives in `plugins/<name>/`, never also in `skills/`, so enabling both never gives you two copies.

| Plugin | Skill | What it does |
|---|---|---|
| `tldw` | [`/tldw`](plugins/tldw/skills/tldw/SKILL.md) | Too long; didn't watch: distill a YouTube video from its transcript into a TL;DR plus the substance, in one of three shapes, with a timestamp link on every point. Pasting a bare YouTube link runs it too (a bundled `UserPromptSubmit` hook). Needs `python3`. |

### Tier 4 — Project-scoped examples (ideas, illustrated)
*This repo exists to help you ideate on your own suite, and some of the best ideas only show up in project skills — the ones wired to one team's tracker, deploy ladder and data. So they're here as **read-only examples** in **`examples/`** (not `skills/`): genericized, not installable, and not meant to run elsewhere. Read them for the pattern, then build your own version.*

**Build → land → deploy.** How project glue composes the generic atoms into one team's shipping flow.

| Skill | The idea it illustrates |
|---|---|
| [`/ship`](examples/ship/SKILL.md) | The thin composite, and the project's default "build this": `/work` → gate → local-QA-and-PR → `/before-after`. "Build it right, prove it, land it." |
| [`/qa-and-pr`](examples/qa-and-pr/SKILL.md) | The land-leg: bring up a local env, seed if thin, browser-QA, run the E2E specs, open a PR. |
| [`/e2e`](examples/e2e/SKILL.md) | The durable half of browser QA: run the E2E specs that cover the diff, diagnose every red before judging it (environment / flake / outdated-by-intent / pre-existing / caused-by-diff), and graduate a verified QA path into one new spec only when a critical journey has none. |
| [`/pr`](examples/pr/SKILL.md) | The landing leaf the two above call: conventional commit → stage-by-path → push → open PR against the integration branch. |
| [`/merge-and-verify`](examples/merge-and-verify/SKILL.md) | One hop of the ladder: merge → watch CI deploy → prove it's live on that env. |
| [`/rollout`](examples/rollout/SKILL.md) | The deploy-ladder orchestrator: a reviewed PR all the way dev → staging → prod gate → prod, chaining the three below. Autonomous until the one hard stop — your go-ahead for prod. |
| [`/promote`](examples/promote/SKILL.md) | Promote one long-lived env branch to the next as a safe merge PR, with a merge-tree pre-check so a promotion's real size is known before it opens. |
| [`/prod-ready`](examples/prod-ready/SKILL.md) | A deploy-readiness gate for work you're returning to cold: rebuild deploy state from durable artifacts (git, CI, migrations, config), not memory, and end on GO / GO-WITH-CONDITIONS / NO-GO. |
| [`/smoke-prod`](examples/smoke-prod/SKILL.md) | A read-only post-deploy prod check: prove the deploy didn't break prod without writing anything there. |

**Personal tooling.** Bound to one person's machine and accounts, but the idea travels.

| Skill | The idea it illustrates |
|---|---|
| [`/poll`](examples/poll/SKILL.md) | Wait for someone's reply without spending tokens: a script does the repeated checking as a background command, and the session wakes only when a reply lands. |
| [`/open`](examples/open/SKILL.md) | Hand work to a new parallel session: a handoff memo when it leans on this thread, its own worktree when it would share a checkout, the driver skill up front. |
| [`/relay`](examples/relay/SKILL.md) | Message another live agent session and relay its reply, or coordinate several sessions on shared work with one named lead. |
| [`/peek`](examples/peek/SKILL.md) | Read another live session's recent turns without interrupting it, before you message a busy peer. |

> **Not included:** project skills whose substance is one project's business domain (support, research and reporting workflows), and tooling bound to one machine's layout.

---

## Installing the portable skills

**Take one skill:** copy its folder into your agent's skills directory. For Claude Code that's `~/.claude/skills/<name>/` (every project) or `.claude/skills/<name>/` (one repo). Each skill is a folder with a `SKILL.md`, the open [Agent Skills](https://agentskills.io) format, so other agents with skill support can read it too. Read it before you install it; it's instructions your agent will follow.

**Take the whole suite in Claude Code:** this folder is also a plugin marketplace. Add it with `claude plugin marketplace add OHOKAYYEAH/claude-skills` (or the path to a local copy), then install `skills-suite` (it installs turned off) — see [SETUP.md](SETUP.md#install-the-plugin). Tier 3 needs the harness pieces in place first (same doc). Tier 4 is read-only example material: the plugin never installs `examples/`.

## How I run it: parallel sessions

The orchestrators are built to run unattended, so the real speedup is running several at once: one session per ticket or worktree, each driving its own `/work` or `/ship`. That needs a way to see which sessions are working, which are blocked on you, and which are done. Mine is hand-built: one tmux window per Claude session, named after the session; the `/done` and `/wait` hook (in [`substrate/hooks/`](substrate/hooks/README.md)) retitles both the session and the window, so state shows in the tab bar; and a small local web dashboard reads Claude Code's own session files and tmux, then shows one row per session with its state and, for `/ship` runs, a stage-by-stage progress bar. `/tangent` forks a side thread into a new window without blocking the current one, and the `/open`, `/relay`, `/peek` and `/poll` examples show the cross-session pieces.

You don't need to build that yourself. Agent multiplexers such as [herdr](https://terminaltrove.com/herdr/) now do much of it out of the box (workspaces of agent panes, with a blocked / working / done / idle status per agent). Start there, and borrow the skills for what happens inside each session.

## Honest limits

- This is **one person's suite**, refreshed from a live setup now and then. It's tuned to how I work; treat it as a source of ideas, not gospel.
- **No evals.** I believe the suite produces better output; I haven't measured it with/without. `/harness-audit` shows which skills get used and whether their output was acted on, but that's usage evidence, not a controlled comparison. That's the standing gap.
- **Context tax.** Name-only listing keeps descriptions out of context, but every skill still costs a line, and every listed one its description. The bar for skill N+1 rises with N; flat libraries reportedly degrade past ~80 skills.
- **One-session horizons.** Forks give each review step fresh context, but the model is still the sequencer, and long pipelines hit context rot and self-grading bias. The frontier is moving the loop into code (fresh context per phase, tests decide done); these skills are the per-iteration standard inside that, not the outer loop.
