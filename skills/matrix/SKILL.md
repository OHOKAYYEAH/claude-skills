---
name: matrix
description: >-
  Price ONE proposed unit of work on the value/effort matrix and place it in a quadrant — DO NOW / PLAN IT / FILL-IN / DON'T — with the evidence behind each axis and a committed verdict. Fire when you're holding a proposal (a ticket, a parked doc, a "should we bother?" idea, a fix someone suggested) and want to know where it sits before deciding: "/matrix", "where does this sit on value/effort", "is this worth doing", "price this out for me". Measures rather than guesses — reads the code, the ticket, the pipeline, the doc — and says which axis is evidence and which is estimate. NOT /triage (that dispositions a BATCH of in-flight findings into DEDUPE/FOLD/FILE/LOG and enforces a one-row budget — this prices a SINGLE named thing and files nothing), NOT /recommend (that picks between options already on the table — this prices one thing against nothing), NOT /ticket (that FILES decided work — this decides whether it's worth deciding). Never ranks against the board.
disable-model-invocation: false
argument-hint: "<the ticket key, doc path, or description of the proposed work>"
---

Price this on the value/effort matrix and commit to a quadrant: $ARGUMENTS

## First — measure, don't estimate from vibes

**Go read the thing before you price it.** An effort number you invented is worse than
no number, because I'll act on it. Spend the tool calls:

- Named a **ticket**? Read it and its comments. The proposal in the summary and the
  reality in the comments often disagree, and the comments are usually righter.
- Named a **doc or a playbook**? Read it, then check whether it's still true. A parked
  plan rots: the fix may be half-done, the blocker may be gone, the tool may have
  changed. **Say so explicitly if the doc is stale or mistaken** — that finding is often
  worth more than the pricing.
- Named **work in a repo**? Look at what it actually touches. Count the files, the repos,
  the deploys, the approvals. "One line in many repos" is a different animal from "one
  line in one repo."
- Is there a **cheaper variant** nobody costed? Price that too — it frequently wins.

If the project has a record-reconstruction skill (one that pulls ticket, chat and git history
on a subject), chain it rather than re-deriving the history yourself.

## The two axes, in the user's actual currency

**Effort** is not story points. It's:
- Hours, and whose: if only one person can do it, their time is the real constraint.
- **Prod deploys and approvals required** — these cost calendar time and risk, not minutes.
- Blast radius if it goes wrong, and how reversible it is.
- Whether it needs someone else (an approval, a credential, a vendor, someone unavailable).
  Work that depends on an absent human is high-effort even when the diff is tiny.

**Value** is:
- **Recurrence** — does this stop a thing that keeps happening? A 90-minute fix that ends
  a recurring outage beats a 20-minute fix that tidies one file.
- What breaks, and for whom, if it's never done. Name the blast radius concretely.
- Whether it unblocks other work or is terminal.
- Whether the pain is already being absorbed by a workaround that works. A workaround
  that holds is real value already banked — it lowers the value of automating it.

Count **cost of delay** separately when it's real: something that gets more expensive the
longer it waits (an expiring credential, an approaching deadline, the one person who knows
it becoming unavailable) deserves saying out loud, because it can promote a low-value item on timing alone.

## Output shape

**Verdict** — one bold line: the quadrant and the call.

> **DO NOW — high value, ~2 hours, and it ends a recurring system-wide outage.**

**Value: <high/medium/low>** — 2–4 bullets, each concrete. What breaks without it, how
often, for whom. Cite the real numbers you found.

**Effort: <high/medium/low>** — 2–4 bullets. Hours, repos touched, deploys and approvals
needed, what could go wrong. Name the single most expensive part.

**Quadrant** — one of:
| | Low effort | High effort |
|---|---|---|
| **High value** | **DO NOW** | **PLAN IT** — needs a real slot; break it into landable pieces |
| **Low value** | **FILL-IN** — fold into adjacent work, don't schedule it alone | **DON'T** — say so plainly |

A batch triage of side findings runs this same grid (do now / fill-in → fold into the open
diff, plan it → file a ticket, don't → drop), with two deliberate differences: it measures
effort against the diff already open, and only *critical* severity earns a ticket there. So a
PLAN IT here may be a "log it, don't ticket it" in triage. That's the batch budget working,
not a contradiction.

**Confidence** — one line separating what you measured from what you estimated. Effort is
almost always the softer number; say which parts you'd bet on and which could double.

**Cheaper variant** — only if one exists. The 20%-effort version that captures most of the
value, priced the same way. If the cheap variant wins, say that in the verdict.

**Then** — one closing affordance: *`/go` to do it now*, or *`/ticket` to file it*, or, for
a DON'T, name what would have to change to make it worth revisiting.

## Rules

- **Commit to a quadrant.** "It depends" is not an answer. If it genuinely straddles a
  boundary, pick the side you'd act on and name the one fact that would flip it.
- **Never rank it against the board.** Emit the placement and the evidence; whoever owns
  the backlog owns the ordering. "This is more important than ticket X" is not yours to say.
- **File nothing, change nothing.** This is read-only pricing. `/ticket` and `/triage` do
  the acting.
- **A DON'T is a real answer** and often the most valuable one. Don't inflate value to
  avoid delivering it.
- If the honest answer is that the proposal is **the wrong shape** — the problem is real
  but the proposed fix isn't the right one — say that, price the right shape instead, and
  flag that you've changed the question.
