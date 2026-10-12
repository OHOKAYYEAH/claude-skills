---
name: autopilot
description: "Scaffold AND launch a SAFE autonomous run — a /loop, /goal, or /batch that drives a goal or a named skill/chain (e.g. /fortify) across a broad, deep, or repo-wide scope. Fire when the ask is \"run X over the whole repo / everywhere / until done\" and you want it set up safely (dedicated branch, checkable stop + hard cap, supervised first unit, confirm-before-begin) rather than hand-rolling the loop. NOT for single-session focused work (that's /work), and NOT for a one-off /loop|/goal|/batch you've already scoped yourself — autopilot is the safety-scaffolding layer on top of those primitives, not a replacement for them. User-gated launcher: it creates branches, commits, and starts unattended runs, so it never auto-fires."
disable-model-invocation: true
argument-hint: "[a goal, or a skill/chain + scope — e.g. \"/fortify the whole api repo\" or \"make every resolver in src/ handle null\"]"
allowed-tools: Bash(git *) Bash(ls *) Read Grep Glob Write
---

You are setting up a **safe autonomous run**. The user has work that's too broad or deep for one focused session — a skill to run over a whole repo, a goal to grind toward across many units — and wants it to run unattended without going off the rails. Your job is to do the fiddly, error-prone setup *for* them: scope the work, pick the right mechanism, bake in the safety rails, preview the exact plan, and — only after they confirm and watch the first unit — hand the rest to an unattended `/loop`, `/goal`, or `/batch`.

You are a **scaffolder and launcher**, not an engine. You compose the existing primitives (`/loop`, `/goal`, `/batch`) and whatever skill/chain the user named (`/fortify`, `/work`, …) — setting them up to run safely and starting them.

## What this is — and isn't

- **`/autopilot`** ← here. Broad/deep/repo-wide work you want to run *unattended and safe*. The value is the safety scaffolding (branch hygiene, a real stop condition, a hard cap, a supervised first unit, a vetted preview) that's tedious to get right by hand.
- **`/work`, `/tdd`, `/fortify` on one unit** — focused, single-session work. If it fits one session, the user doesn't need autopilot.
- **A bare `/loop` / `/goal` / `/batch`** — if the user has already scoped the run and knows the exact command, they can fire it directly. Autopilot earns its place when the setup is the hard part.

## Arguments

`$ARGUMENTS` is the mission: either a **goal** ("make every resolver handle null"), or a **named skill/chain + scope** ("/fortify the whole api repo"). No argument → ask what to automate; this is an interactive setup skill, so one clarifying question is correct here, not a guess.

## The workflow

### Phase 0 — Understand the mission
Parse the argument into three things: **the work** (a goal, or a skill/chain to run), **the scope** (repo / directory / module set / file glob), and **the implied definition of done**. Restate it back in one line so a misread surfaces now, not 200 units in.

### Phase 1 — Scope and decompose
Resolve the scope to concrete **units** — the things the run will iterate over. For a skill-driven run, units are whatever the composed skill operates on (e.g. `/fortify` works one module/feature at a time, so a unit is a module). Read the repo to estimate the unit count and rough size. This count drives both the mode choice and the backstop cap, so don't skip it — a run you can't bound is a run you shouldn't launch.

### Phase 2 — Choose the mechanism (recommend-and-confirm)
Propose the mode **with your rationale**; let the user override. Don't silently auto-pick. Heuristic:
- **Sequential "keep doing X until there's nothing left"** → `/loop` self-paced. (The common case — e.g. fortify the next high-risk unit, repeat.)
- **Converge to a single machine-checkable end-state** ("all tests green, lint clean") → `/goal`.
- **N genuinely independent chunks you want worked in parallel with a PR each** → `/batch`. **Confirm `/batch` actually exists in this Claude Code version before selecting it** (it's newer than loop/goal); if it isn't available, fall back to `/loop` self-paced and say so plainly.

### Phase 3 — Stop condition + backstop cap (refuse without both)
This is the core safety property. Before going further, pin down **both**:
- A **machine-checkable stop/done condition** — something the run can evaluate to know it's finished (e.g. "the composed skill reports no remaining high-risk units," "the work-list is empty," "the goal evaluator confirms the end-state").
- A **backstop cap** — a hard ceiling that stops the run regardless: max units/iterations, or a token budget.

If you cannot articulate *both* concretely, **do not launch.** Surface the gap and ask. Open-ended loops with no real stop are the single most common way autonomous runs cause damage — the cap is the seatbelt, the stop condition is knowing where you're going.

### Phase 4 — Safety rails
Lock these in (they're the defaults; deviate only on explicit instruction):
- **Dedicated branch.** Verify the working tree is clean first (stash or flag if not). Create a goal-named branch off current HEAD. **Never work on the user's current branch** — the run must be trivially discardable.
- **Commit per completed unit.** Each unit's output is committed on the branch (encode this in the run prompt, since the unattended mechanism does the committing). Durable, reviewable trail; easy to bail mid-run without losing finished work.
- **Never push.** Hardening/automation, not shipping. The user pushes deliberately, later.
- **Findings-not-fixes by default.** Autopilot inherits the composed skill's behavior — if the skill *reports* problems rather than patching them (as `/fortify` does with latent bugs), the run does the same. Do **not** add autonomous source-fixing unless the user's goal explicitly asks for it.

### Phase 5 — Build the run-plan artifact and preview (dry-run)
Compose the **exact command(s)** the run will fire — the literal `/loop …` / `/goal …` / `/batch …` invocation, including the embedded instructions (auto-pick next unit / don't ask, commit per unit, log findings instead of stopping, the stop condition, the cap).

Write a **run-plan artifact** capturing: mission, chosen mode + why, scope + unit list/count, stop condition, backstop cap, every safety rail, and the exact command. Put it at the repo root (`AUTOPILOT-RUN-PLAN.md`) so it travels with the dedicated branch as the first commit — an audit trail and a resume point that vanishes when the branch is deleted. **This artifact is the dry-run preview.** Show it to the user.

### Phase 6 — Confirm gate ① ("begin?")
Explicitly hand the user the gate: *here's the full plan and the exact command — begin, or adjust?* This is a real user-decision pause (it's why this skill isn't a fork). On a correction, loop back and revise the plan. On confirm, proceed.

### Phase 7 — Supervised first unit
Create the branch, commit the run-plan artifact, then **run exactly one unit inline** and show the result. This is the "watch the first backflip" check — the cheapest insurance against a misconfigured run torching a whole repo.
- For **`/batch`** (parallel fan-out, can't run "one first"), supervision instead means: show the full **unit decomposition** and get confirmation *before* spawning anything.
- If the user opted into **skip-straight-to-unattended** back in the preview (a run they already trust), skip this phase.
- **The composed skill's output is mid-pipeline, not a finish line.** A skill like `/fortify` ends its unit with a satisfying report block — treat that as input that flows into gate ②, **not a turn-ending yield**. Don't let a polished inner report tempt you to stop at unit one; you still owe the user the gate. (This is exactly how `/fortify` itself treats `/mutate`'s report — "mid-pipeline input, not a turn-ending yield.")

### Phase 8 — Confirm gate ② → go unattended
After the first unit, pause for the user's OK. On confirm, **launch the unattended run**:
- **Loop modes** are launchable directly from here — schedule the self-paced/interval loop via the loop machinery (`ScheduleWakeup` for self-paced, `CronCreate` for a fixed interval), firing the vetted prompt each iteration. This is true "fire it itself."
- **`/goal` and `/batch`** may have no model-drivable launch. If so, present the **exact vetted command** as the explicit launch step for the user to fire — framed as the final action, not a failure. (Honor "fire it itself" wherever the mechanism allows; degrade gracefully where it doesn't.) *Workaround — revisit when `/goal`/`/batch` expose a programmatic launch; until then, hand-back is the launch step for those two modes.*

The two gates are one-time, *before* the unattended phase. Once it's running, iterations fire without further confirmation — that's the entire point. The branch, the per-unit commits, and the run-plan artifact are how the user reviews and bails.

## Guardrails
- **No launch without both a checkable stop and a backstop cap.** Non-negotiable. When in doubt, refuse and ask.
- **Never push; never touch the current branch; verify a clean tree before branching.** The run must be discardable with zero collateral.
- **Recommend-and-confirm the mode** — never silently auto-pick loop vs goal vs batch.
- **Don't add autonomous fixing** the user didn't ask for; inherit the composed skill's findings-vs-fixes stance.
- **Scaffold and launch — don't reimplement.** If you find yourself rebuilding what `/loop`/`/goal`/`/batch` or the composed skill already do, stop; compose them instead.
- **Confirm `/batch` exists before offering it**; fall back to `/loop` self-paced and say so otherwise.
