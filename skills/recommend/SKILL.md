---
name: recommend
description: "Your one \"what now?\" command — you don't have to know which case you're in. Checks the session for live open decisions first: if any, commits to a pick on them; if none, recommends what to do next (from a staged plan, breadcrumbs, or the natural follow-up). Either way: a header line naming which case it found, a numbered top pick + why (usually one move; a sequence or parallel lanes only when the work calls for it), 2–3 rival options, and `/go` / `/go N` to act. Fire on \"what would you do\", \"just pick\", \"what should I do next\", \"what now\", end-of-flow drift. NOT pricing ONE proposal (\"is this worth doing at all?\") — /matrix. NOT the factual where-are-we + full remaining queue — /report."
disable-model-invocation: false
argument-hint: "[optional focus or scope]"
---

I'm offloading the call. I context-switch constantly and often can't tell whether there's a live decision waiting on me or I just need to pick what's next, so you figure out which, say which, and commit.

## 1. Find the case

Scan the session for **live open decisions**: a question you asked me that I never answered, options you laid out that I never picked between, a fork the work is blocked on, a choice I said I'm mulling. "Live" means it still matters. A choice the work has already moved past doesn't count.

- **Decisions found → decision mode.** Pick on the one that blocks the most work. If there are several, the header says how many, the pick covers the top one, and the others are listed as later options.
- **None found → next-step mode.** Recommend what to point at next, sourced in this order: (1) an explicit plan or queued "let's do X next"; (2) breadcrumbs: half-finished edits, "we should also…" asides, a question left hanging; (3) the sensible default for the moment: tests for what just shipped, open the PR, switch tickets, take a break. Process moves count, so don't bias toward more code.

Decision mode wins when both apply, because an open decision usually blocks the next step anyway.

## 2. Output shape

**Header**: one italic line saying which case you found, so I never have to wonder:
- *`2 open decisions — picking on the deploy-order one.`*
- *`No open decisions — here's what I'd do next.`*

**Then a numbered list.** #1 is the pick, marked `→ recommended`:

```
1. → recommended: <the call, stated as a decision or a concrete action>
   - <why: what tipped it — the key constraint, signal, or tradeoff>
   - <why, if a second reason earns its line>
   - <assumption I'm making, if any: "assuming X matters more than Y">
2. <alternative> — <when you'd pick this instead>
3. <alternative> — <when you'd pick this instead>
```

- **#1's why**: 1–3 bullets naming what *made it win*, not just "it's cleaner".
- **#1 is usually one move.** Make it a plan only when the situation earns one, never to look thorough:
  - **a sequence** when steps depend on each other (investigate → decide → draft the email), in order;
  - **parallel lanes** when a piece is ready to start now, waits on nothing in the sequence, and running it alongside saves real time. Write each as a `parallel:` line naming the slice to start in its own new session, with a handoff memo when the lane leans on this thread.

  A plan's sequence runs here. If the window is already high (~250K+), its first step is `/handoff`, which judges continue / compact / fresh. In decision mode the plan grows only from what the answer unblocks.
  ```
  1. → recommended: <the call, one line>
     - here: <step> → <step>
     - parallel: <slice> (<why it can run alongside>)
     - <why it wins>
  ```
- **Options 2–4**: always show 2–3 real alternatives, one line each, built around the condition that flips the call. Alternatives are *rivals*: a move that competes with #1 or a different shape of it. A compatible move worth doing now joins #1's plan; one that isn't stays out. If there's honestly only one sane move, say so in one line instead of padding.
- In next-step mode, alternatives are *different things to point at*, not the rest of the queue in order. The ordered queue is `/report`'s Next section.

**Closing line**: *`/go` to run #1 · `/go N` for another.* (`/go` on a plan launches its parallel lanes, then runs the sequence here.) Skip it only when #1 is "wait / don't act yet". If #1 is a real chunk of work and "is it even worth it?" is the live question, add: *`/matrix` to price it first.*

## Rules

- **Commit.** No "it depends", no "both are valid". If you can't pick without one fact, ask that one sharp question instead of the list.
- **Lean but not cryptic.** Enough to sanity-check the call, not a full analysis.
- **Forward only.** No recap of what's done; that's `/report`.
- Name the *kind* of move honestly: "ship the PR", "stop and write tests", "switch tickets".
- No preamble, no signoff.

If I've added a focus below, narrow to just that slice: $ARGUMENTS
