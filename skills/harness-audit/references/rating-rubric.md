# Harness-audit — rating rubric

## The headline score: Proven Value (1–5)

Rates **value when the skill ran**, judged from what it actually emitted (its `slices/<skill>.json`) — NOT how often it ran. Every score cites evidence (session id + the moment). No citation → no claim.

- **5 — Load-bearing.** Repeatedly changed the outcome: caught real bugs, killed surviving mutants that led to added tests, produced findings you acted on, prevented a bad ship, saved obvious rework. The record would be visibly worse without it.
- **4 — Reliably useful.** Regularly does its job well; occasional runs where it added little, but the norm is real value.
- **3 — Mixed / unproven.** Runs and produces plausible output, but the record rarely shows it *changing* anything — hard to see the counterfactual. Often the "ran clean, found nothing" skills; distinguish "nothing to find" from "didn't look hard."
- **2 — Mostly ceremony.** Fires but the output is routinely ignored, redundant with another skill, or so shallow it's decorative. Frequent friction/override right after.
- **1 — No observable value / actively costly.** Always no-ops, always overridden, misfires, or its output misled. A retire/rework candidate.
- **Insufficient signal** — too few or too thin instances to judge honestly. Say this; never guess a number to fill the cell.

## Frequency is NOT quality — report it separately

Invocation count, work-volume, sessions, and last-used are their own columns, never folded into the score. A skill invoked twice can be a 5 (`/handoff` when context is dying); a skill invoked 140× can be a 3 (`/go` is a trivial actuator). Interpret them independently:
- **High freq + low value** = ceremony tax — the loudest fix target.
- **Low freq + high value** = keep, don't let low use fool you into retiring it.
- **Zero freq (dead)** = staleness, judged below — NOT a value score.

## Friction / override signal

Each episode carries `next_user` — the human turn that followed. Scan it for correction ("no, not like that", "you missed", re-instruction, abandonment, a redirect to a different approach). A skill whose output is frequently corrected or discarded right after is over-scored on raw output alone — dock it and note the pattern.

**Known limitation (v2) [workaround]:** `next_user` is noisy — it sometimes captures harness-injected content (a chained skill's command header, a `<local-command-caveat>` from `/copy`) rather than a genuine human turn, so friction is *under*-detected. Treat friction as a soft, corroborating signal, not a primary score driver. Fix when the extractor's `is_human_turn` filter is tightened to exclude injected/wrapper turns.

## Composite decomposition (`/work`, `/super-review`, any project ship composite)

Don't just score the composite. Read the slices of its chained legs and rate each leg's *contribution to the whole*:
- `/mutate` — did it surface surviving mutants, and did those lead to real added tests? (Look for "KILLED/SURVIVED", "added test", mutant descriptions.)
- `/tdd` — is the red-first step real (a genuine failing test first) or skipped?
- `/code-review`, `/super-review` — findings that were real and fixed, vs manufactured nits?
- `/review-plan`, `/blast-radius`, `/sec-review` — did they change the plan / catch a cross-repo break / find a real exposure?

The payoff question that matters: **is the test/quality spine visibly improving the work, or is it expensive ceremony?** Answer it with citations.

## Known attribution blind spots — do NOT call these "dead"

The transcript under-reports these cases; confirm before flagging any as sediment:
- **Hook-backed skills** (e.g. `/done`, `/wait`) — if a UserPromptSubmit hook intercepts and blocks them before the LLM (as a session-renaming hook can), they leave no `<command-name>` or Skill tool_use. Absence here ≠ unused.
- **Native CLI skills are not user skills at all.** `summary.json` now carries `native_builtins_used`, and any skill with `is_native_builtin: true` is bundled with the CLI — it has no SKILL.md *by design*, cannot be retired, and must never enter the sediment bucket. Some are aliases (`/review` → `/code-review` since CLI 2.1.223), which is why one can show invocations, no definition, and odd argument handling all at once. If such a name is rotting inside one of your chains, the fix is to stop naming it in the chain — not to "retire" it.
- **Native-skill-behind-a-fork-wrapper, and renamed skills** — a wrapper absorbs its inner skill's attribution, and a renamed skill's older runs log under its old name. `/sec-review` does not call the native `/security-review`, so rate it alone. The native name looking thin is expected; judge the pair together.
- **Inline-token chaining** — a composite that pulls a sub-skill in by inlining its instructions (a token/Read) rather than a Skill tool_use leaves no invocation for that leg. Its work may be attributed to the parent.

A genuine sediment finding is a skill that is **defined, in inventory, has a real user-facing purpose, and shows zero invocations AND zero attributed work in the window** with none of the above explaining it.

**Don't reach for a stock example here — check the window.** A skill that looks like "an experimental skill that never caught on" can score a 5 the next month; a hardcoded example ages into a thumb on the scale.

**Project-scoped skills are inventoried** (from each session's `cwd`), so they can appear in `dead_skills`. An appearance there means "no use in *this window*", not "never earned its keep": some carry their own ledger/log recording use just before the window opened. Read `defined_in` to see which project owns a skill before judging it.
