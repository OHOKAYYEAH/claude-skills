---
name: go
description: Act on the most recent recommendation, proposal, or stated judgment in the conversation. The user is greenlighting without retyping — "go ahead with what you said." Don't ask "should I proceed?". Stop only for risky/hard-to-reverse actions or when you genuinely cannot pick without more info.
disable-model-invocation: false
argument-hint: "[optional focus or scope]"
---

Greenlight on the most recent recommendation, proposal, or stated judgment in this conversation — typically the block immediately above in this turn, or in the most recent assistant turn. The /go invocation IS the green light — don't ask "should I proceed?", "want me to start?", or "sound good?". Mathematical!

**What counts as actionable is broad:** a recommendation, a proposal, a stated judgment — *and* a forward-looking **"Next" / "next steps" / "up next"** section that caps a status or orientation response. If that closing section lists several items rather than one committed pick, act on the one marked recommended / top / first, and name which you picked in your transition line. (Generic by design — keyed off the *shape* of a trailing next-step section, not off any particular skill.)

**A plan with `parallel:` lanes** (a `/recommend` #1): launch every lane first, each in its own new session, then run the `here:` sequence. Reversed, a `/handoff` first step can end the turn before any lane launches.

**`/go N`** (a bare number as the argument) acts on item N of that numbered list instead of the top pick — `/recommend` ends on exactly this affordance. Name the item in your transition line. No numbered list on the table → ask which thing N means.

- Begin the work directly. One short transition line is fine ("Going.") but no permission-seeking pause.
- For multi-step work, use TaskCreate to track it and start on step 1.
- For one-shots (single edit, single command), just do it.

**The one exception — stop and ask if:**

- The action is **risky / hard-to-reverse / has wide blast radius** (destructive ops, force-push, sending messages, modifying shared infra, publishing to third parties — per the system's "Executing actions with care" guidance).
- You **genuinely cannot pick** without more info. In that case, ask **one** sharp question — don't refuse to commit and don't pad with hedges.
- **Nothing is staged to act on.** If there's no prior recommendation, proposal, or stated judgment in conversation context, ask one short question ("What would you like me to act on?") rather than guessing or sliding into `/recommend` territory.
- **A condition the recommendation relied on may have gone stale.** If it asserted anything time- or state-dependent — the clock ("after market close", "before the 22:30 sync"), "origin hasn't moved", "tests are green", "the deploy is live" — and it wasn't made moments ago, re-check that condition first (`date`, `git fetch`, the status command). Still true → act. No longer true → stop and say what changed. (Example: a "safe to push, it's after hours" note that is a day old by the time /go lands is no longer true.)

Otherwise: commit, execute, report results.

If I've added a focus below, narrow the work to just that slice: $ARGUMENTS
