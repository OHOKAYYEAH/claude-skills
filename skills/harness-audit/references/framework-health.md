# Framework health — signal definitions

The skill-level stages of `/harness-audit` ask *"did this skill earn its keep?"*. This
section asks the question one level up: *"is the workflow as a whole healthy?"* — did the
decisions it made hold, and how often did the person and the AI have to pull back into line
with each other?

The framing: one person measuring their own AI-assisted workflow off the artifacts it
already produces. Which design decisions got made and how often they held; how often work
had to go back for a correction; how often the person had to get in line with the AI, or the
AI with the person; and whether quality issues fall as more of the work runs through the
workflow. Those are four signals. This file defines **1** and **3**; 2 and 4 are below under
*Deferred*.

**Every signal is defined over artifacts, never over skills.** A skill is how *this* harness
happens to produce an artifact; the definitions must hold for any framework that leaves the
same records behind. The *AI-DLC mapping* column shows the equivalent record in AWS's
AI-DLC (an open-source rule-file workflow for AI-driven development), as one example of the
definitions travelling to a setup where `extract_framework_health.py` doesn't run.

## Signal 1 — decisions held

Which design decisions got made, and how often they held. A decision **held** if the work
built on it was not sent back to change it.

| Part | Artifact | Counts as held | Counts as not held | AI-DLC mapping |
|---|---|---|---|---|
| **1a. Spec fidelity** | Each `/spec-check` result (a forked Skill result whose `toolUseResult.commandName` is `spec-check`) | The **first** check of a spec came back ✅ built to spec | First check came back 🔧 gaps owed or ⚠️ divergences / needs the user's call | The first review of a construction unit against its approved requirements/design docs in `aidlc-docs/` |
| **1b. Autonomous decisions** | A `Decision: <call> — because <why>` line an orchestrator printed (`/work`'s contract), paired with the next human turn | The next human turn did not reverse it | The next human turn was a `corrected_ai` (see signal 3) | A stage the model completed without a gate, judged by the next `audit.md` entry |
| **1c. Re-freezes** | A `🔒 FROZEN SPEC` header whose `supersedes:` field names a prior freeze | — (reported as a raw count) | A re-freeze **after** a `RED:` or `Build:` line in the same session: intent changed once building had started | A requirements/design doc revised after its approval gate passed |

**Boundary cases:**
- **Which spec a check belongs to.** Key a check on the ticket in its `**Spec:**` line (plus
  the comment id when the line names a frozen-spec comment), not on the session or the line's
  wording, which varies run to run. Work moves sessions on `/handoff`, so keying
  on session would score a fix-and-rerun as a fresh first pass and inflate the ✅ rate. No
  ticket in the Spec line → the spec file path in it (last two parts) → the first ticket key
  in the result → the session id, in that order.
- **A new freeze comment is a new spec**, so its first check is a first pass. A check that
  names only the ticket is a rerun of any earlier check of that ticket.
- **A spec first checked before the window** makes every in-window check of it a rerun, so a
  monthly window never scores the fix-and-rerun as the first pass.
- **The baseline need not be a frozen spec.** `/spec-check` falls back to the ticket's
  acceptance criteria when no frozen spec exists, and many runs will. A first pass against acceptance criteria still counts: the
  decision being tested is "what we agreed to build", wherever it was written down.
- **🛑 can't verify** is excluded from the 1a denominator and reported as its own count. A
  check that couldn't run says nothing about whether the decision held.
- **Status wording varies** with the output style ("✅ built to spec", "Built to spec.", "The
  build matches the spec"). The extractor reads the emoji on the `**Status:**` line (or, with
  no Status line, the earliest one in the first 300 characters), and anything without one
  goes to the labelling pass.
- **A re-freeze before the build** is discovery doing its job, not a failure. Only
  after-build re-freezes count against signal 1.
- **A Decision the human *extended*** ("yes, and also do X") held. A Decision the human
  *redirected* ("no, use the other table") did not. Silence followed by a `/go` held.

## Signal 3 — realignment (people ↔ AI)

How often the people had to get in line with the AI, or the AI with the people. Unit of
analysis: **a pair** = the last AI message before a human turn, plus that human turn. Pairs
are built from the human turn backwards, so a reply that lands after dozens of tool calls
still pairs with the message it answers.

| Class | The human turn… | Direction |
|---|---|---|
| `accepted` | approves, continues, or extends what the AI proposed or did; includes a `/go` after a real recommendation | aligned |
| `corrected_ai` | says the AI was wrong — wrong fact, wrong approach, wrong scope, ignored an instruction — and points it elsewhere | AI gets in line with the person |
| `changed_ask` | changes or narrows what the person wants *because of* what the AI showed (a finding, an option, a risk) | person gets in line with the AI |
| `rubber_stamp` | approves a stop the AI should not have made: it asked permission for the obvious next step, or for a call it had the context to make. Typical: "yes", "go", `/go` after "Want me to…?" | wasted alignment cost |
| `other` | a new, unrelated request; a question about something else; chit-chat; a pasted log | not a realignment event |

**Boundary cases:**
- **`/go` is not automatically `accepted`.** It is the commonest answer to a needless halt.
  If the AI's message ends by asking permission for something it was already licensed to do,
  the `/go` is `rubber_stamp`; if it ends on a recommendation among real alternatives, it is
  `accepted`.
- **`rubber_stamp` needs both halves:** the AI asked permission for a step it could have
  taken on its own, *and* the reply only approves it. A real fork ("ship now or park it?",
  "merge, or are you reviewing first?") answered with a pick is `accepted`. Asking before an
  outward-facing action (a tracker write, a merge, a sent message) is a legitimate stop, so
  approving it is `accepted`. A reply that approves *and* raises something new is `other`.
- **`corrected_ai` needs the human to say the AI was wrong.** A status update ("1. done,
  2. done"), a new request, "what do you recommend?" or a design musing is `other`, however
  long. Supplying a fact the AI got wrong ("those times are UTC, not local") is
  `corrected_ai`; supplying one it simply lacked is `other`.
- **Most turns that open a new topic are `other`.** Expect `other` to be a large share; it
  is not a failure class.
- **CLI-local commands are not replies.** `/model`, `/rename`, `/compact` and the like are
  skipped, so the turn typed after them still pairs with the AI message.
- **One Decision counts once.** A forked or branched copy of a session replays the AI message
  that carries it; only the first reply to consume it scores it.
- **Interrupts are a flag, not a class.** `[Request interrupted by user]` sets `interrupted`
  on the pair whose human text follows it; that text gets a class like any other (usually
  `corrected_ai`).
- **A question back** ("why that table?") is `other` unless it plainly signals disagreement
  ("why would you touch prod?" → `corrected_ai`).
- **Corrected *and* changed the ask** in one turn → `corrected_ai`. The AI being wrong is the
  stronger signal.
- **A reply to a sub-agent's result** pasted by the AI counts against the session's AI, not
  the sub-agent: the person only ever answers the main session.

**AI-DLC mapping:** every user reply is logged raw in `aidlc-docs/audit.md` next to the
question or completion message it answers, which is exactly a pair. AI-DLC v2's typed audit
events make two classes mechanical: `GATE_REJECTED` ≈ `corrected_ai`, a gate approved with
no edits after a "proceed?" ≈ the `accepted` / `rubber_stamp` split.

## Numbers, small n, and what goes in the report

- **Months are UTC calendar months.** A window that ends mid-month labels that month partial.
- **Small-n rule:** a month (or a pooled figure) with **n < 5** reports counts and says
  "insufficient signal" — never a percentage.
- **Signal 1 is raw counts, never a rate.** Its inputs are rare (a handful of spec-checks
  and Decision lines a month at one developer's volume), so report "4 of 11", pooled over the window, with
  the per-month split in brackets. 1b (Decision lines held) reads high by construction: the
  next reply usually answers the final report, not the Decision. Treat it as informational.
- **Signal 3 is sampled**: up to 60 pairs per month by deterministic stride. *Every* pair
  that carries a Decision line is labelled too (signal 1b needs all of them), but those
  outside the stride stay out of the signal-3 rates, which would otherwise over-weight
  orchestrator turns. Report the month's total pair count beside the sample size.
- **Validate before scoring.** Every unlabelled item must get a label from the class set, or
  `score` fails. Spot-check about 10 labels against their pairs before trusting a run,
  weighted to the blurry boundaries: `rubber_stamp` vs `accepted`, `changed_ask` vs
  `corrected_ai`.
- **Citations by reference only:** a session-id prefix (8 chars), a ticket key and a month.
  Never a transcript excerpt: the audits dir may be committed and pushed.
- **Exclude the auditing session** (`--exclude-session`): designing or debugging this signal
  generates Decision lines and spec-check text about itself.

## Known blind spots

- **Measure the property, not the artifact.** Signal 1 asks whether the build held to the
  *ratified* intent, wherever it lives (a frozen spec, the ticket's criteria, a handoff).
  A rarely produced artifact is not a defect by itself: frozen specs stay rare where
  ratified ticket criteria already do the job. Never change the workflow just to
  give a signal input; that is the metric steering the work.
- `/spec-check` and the `Decision:` contract only exist where an orchestrator ran; ad-hoc
  sessions contribute to signal 3 only.
- Labels come from a model; check a cheaper labeller against the spot-check before trusting it. The rates are directional;
  the spot-check is what makes them trustworthy enough to quote.
- **Rewinds and edited messages pair by file order**, not by `parentUuid`, so after a rewind
  a reply can pair with the wrong AI message (a small share of pairs). Below the
  labeller's own noise; fix it before anyone reads single pairs as evidence.
- **The labeller reads untrusted text** (transcripts quote tickets, chat and mail written by
  others). It runs as a read-only Explore agent told the input is data; a Read-only agent
  definition would close the remaining Bash/MCP access.
- One developer means small samples. Trends need several months, and ticket mix (a
  bugfix-heavy week vs a feature week) moves signal 3 more than the framework does.

## Deferred

- **Signal 2 — corrections** (how often work had to go back for a correction): fix
  or revert commits touching the same files within ~14 days of a merge, plus reopened tickets.
  Needs git across every repo involved; tool-neutral, so it maps to any framework unchanged.
- **Signal 4 — quality vs pipeline share** (whether quality issues fall as more of your
  work runs through the workflow): the share of tickets that went through the pipeline
  against post-merge defects, month over month. Mostly noise at n = 1 developer; it gets
  more useful if others use the same workflow and their records can be pooled.
