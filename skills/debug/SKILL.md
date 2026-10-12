---
name: debug
description: >-
  Root-cause diagnosis for a bug whose cause is UNKNOWN: reproduce, gather
  evidence before theorizing, kill falsifiable hypotheses one experiment at a
  time, and confirm a cause that explains every observation. No fixing; hands
  the confirmed cause to /tdd. Fire on "why is this happening", "works on X but
  not Y", "started failing and nobody knows why". NOT /tdd (cause already
  known).
disable-model-invocation: false
argument-hint: "[the symptom — what's observably wrong, plus any error text or \"started after X\" context]"
---

You are **diagnosing, not fixing**. The output of this skill is a confirmed root cause; the fix belongs to `/tdd`, which takes the cause as its step-1 hypothesis. Keeping the two separate is the point — a fix written against an unconfirmed cause is a guess, and on old/shared code, a guess that plants regressions.

## Why diagnose-first

Shotgun debugging — edit something plausible, rerun, repeat — sometimes works and always teaches nothing. Worse, it can *appear* to work: the symptom moves, the cause keeps generating new symptoms, and now the diff contains three unrelated edits nobody can explain. The discipline below replaces "what might fix it?" with "what would I observe if hypothesis X were true?" — every experiment either kills a hypothesis or confirms one, so even a failed experiment is progress.

## When this fires vs. its siblings

- **`/debug`** — the cause is unknown; produce a confirmed diagnosis. ← here
- `/tdd` — the cause is known or hypothesized; write the red test that proves it, then fix.
- `/devtools` — the browser primitive this skill drives for UI evidence and repros.

## The loop

### 1. Pin the symptom — observable facts only

What happens, what should happen, when it started, and — often the best discriminator — **where it does NOT happen** (works in dev but not stage; fails for this user but not that one; only on the second click). Negative space constrains the hypothesis set more than the failure itself.

### 2. Reproduce

Get the cheapest *reliable* repro: a failing test beats a script beats a `/devtools` browser walk. If you can't reproduce it, don't theorize from vibes — go gather more evidence (step 3) until you can, or say plainly that this will be an evidence-only diagnosis with lower confidence.

**If the natural trigger is expensive — a reboot, a deploy, a nightly cron — synthesize the CONDITION instead of waiting for the cycle.** One attempt per reboot caps you at a handful of experiments a day, and the dead time between them is spent theorizing, which is precisely the failure mode this skill exists to prevent. Ask what *state* the slow event actually leaves behind, then produce that state directly: `pkill -9` for the unclean-exit flag a hard poweroff leaves, a hand-written cache row for the 3am job's output, a skewed clock for the expiry path. (Example: a boot-time bug that resisted many reboot-per-round attempts settled in two experiments once its trigger — an unclean-exit flag — could be reproduced on demand in seconds.)

### 3. Gather evidence before theorizing

- Read the actual error and surrounding logs end to end — not the first line, the whole trace.
- **"My fix changed nothing" is usually a LOADING problem, not a logic problem.** Before you re-theorize, prove the artifact you edited is the one actually executing: `python -c 'import pkg; print(pkg.__file__)'`, `node -e "console.log(require.resolve('pkg'))"`, and look for a **non-editable install shadowing your source** (`pip install .` leaves a *copy* in site-packages), a stale `build/`, a cached image layer, a running process holding the old code. **The tell is a test that fails *byte-identically* after your change** — that is not a stubborn bug, that's dead code. (Example: every edit to `src/` was inert because the venv held a copy; `pip install -e .` made the edits live, and only then did the real bug appear.)
- **Regressions have a birthday.** `git log` the implicated paths for recent changes; if a known-good commit exists, `git bisect` is usually cheaper than reading code.
- Inspect real runtime state (actual payloads, actual config, actual DB rows), not the state you assume. The bug is frequently the gap between those two. **When several users are affected, inspect each one's state — including per-user overrides and hand-applied workaround rows.** A fix derived from the reporter's account can be silently defeated on another account by a per-account setting or an old workaround, so verify the fix against every affected account, not just the first.
- **Browser-shaped bug? Reach for `/devtools` early.** Console errors, the network waterfall (status codes, payloads, timing), and live DOM/state inspection are primary evidence — and the default debugging instrument. Drive the real browser; don't reason about what it probably does.

### 4. Rank falsifiable hypotheses

Enumerate candidate causes. Each one must name its **discriminating observation** — what you'd see if it were true that you wouldn't see otherwise. "Something async, probably" is not a hypothesis; "the second request reuses the first request's cached session, so the stale user id appears in the second response" is. Rank by likelihood × cheapness-to-test.

### 5. Kill them one experiment at a time

One experiment per hypothesis, cheapest-discriminating first: targeted logging, a debugger breakpoint, a bisect, a minimized input, toggling exactly one variable — or, for browser behavior, a `/devtools` experiment (replay the request, tweak live state, block one script), often the cheapest discriminator of all. **Change one thing per experiment** — two changes per run means the result tells you nothing. Instrumentation (log lines, temporary flags) is fine; **fixes are not** — and track every instrumentation edit so it's reverted before handoff. Update the ranking after every result; a killed hypothesis is progress, not failure.

### 6. Confirm the root cause

The bar for "confirmed":
- It explains **all** observations from step 1 — including the negative space. A cause that explains the failure but not why prod is unaffected is incomplete.
- It **predicts**: perturb the cause and the behavior changes exactly as predicted.
- You made **one honest attempt to refute it**. Stopping at the first plausible cause is the classic trap — the leading hypothesis earns confirmation by surviving an attack, not by being likeable.
- **A setting that is *present* is not a setting that *fired*.** `brave://policy`, `printenv`, a green check in an admin UI — each proves the value was *read*, never that it took *effect*. App-level heuristics, precedence rules and safety overrides silently win, and they leave the config looking perfectly correct. Verify the **behaviour** the setting is supposed to cause, not its presence. (Example: a session-restore policy showed `OK` while a crash-recovery heuristic overrode it, so the real defect — "the restore never actually fires" — stayed hidden behind a green check.)

### 7. Hand off to /tdd

The confirmed cause becomes `/tdd`'s step-1 hypothesis, and its red-for-the-right-reason gate is the *independent* proof of this diagnosis. If a red test can't be produced from the cause, the diagnosis is wrong — come back to step 4 with that as new evidence, don't force the fix.

## Close-out

Keep it light — this runs inline and usually feeds `/tdd` next; don't end on a heavy terminal block that reads as "stop here":

- **Symptom:** what was observably wrong.
- **Hypotheses killed:** each, with the experiment that killed it (one line apiece).
- **Root cause:** the confirmed cause + what confirmed it (the prediction that held).
- **Instrumentation:** reverted ✓ (or list what remains and why).
- **Next:** `/tdd` with this cause — or, for an evidence-only diagnosis, the confidence level and what repro is still missing.

## Guardrails

- **Diagnose, don't fix.** The moment you're editing source to *solve* rather than to *observe*, you've left this skill — stop and route through `/tdd`.
- **Revert instrumentation.** Temporary logs and flags must be gone before handoff; a diagnosis that leaves debris becomes someone else's mystery bug.
- **One variable per experiment.** Compound experiments produce uninterpretable results — slower than two clean ones.
- **Attack the leading hypothesis.** Look for the observation that would *refute* it, not more observations consistent with it.
- **Time-box guessing.** If two rounds of experiments haven't discriminated between hypotheses, switch modes: bisect, minimize the repro, or widen evidence gathering. Deeper guessing from the same evidence is the failure mode.
- **No commits or pushes.** Diagnosis produces knowledge, not commits.
