---
name: triage
description: >-
  Decide, as one batch, which side findings from a piece of work deserve a
  ticket: dedupe against the tracker, then one disposition each: DEDUPE, FOLD
  (fix it now in this diff), MERGE, FILE (at most one new ticket per pass),
  ATTACH, LOG (FINDINGS.md), ASK, or DROP. Places each filed ticket in the
  active sprint or the backlog by urgency. Effort-first; decides without
  stopping to ask; never reorders the board. Run at the end of a task, before the PR
  opens, or on "triage these findings" / `audit`. NOT for filing one
  already-decided ticket.
disable-model-invocation: false
argument-hint: '<candidate findings, or a ticket key / date range to audit> [tokens: "audit" judge already-filed tickets · "dry" dispositions only, change nothing]'
---

A ticket is not free. Every one costs the person who orders the backlog a
decision: *is this more important than what's already queued?* Filing is cheap
for you and expensive for them, and that asymmetry produces a backlog nobody
trusts. A session that works one ticket and leaves four behind has not been
thorough. It has moved its findings onto someone else's plate without the
context needed to rank them. Left unchecked, one worked ticket can spawn several
new ones, none of them prioritized.

The opposite failure matters just as much: follow-ups left in a comment on the
parent ticket are durable but sit in no queue, and a real prod defect can hide
there for weeks. **So triage never defers a decision. It makes one per finding,
in-session, and says out loud what it dropped.** An undecided finding is the one
outcome that is not allowed.

## 0. Guard

- **Batch in, never per-item.** Holding one finding, you can't see that it is one
  of four from the same parent, and you can't judge "quick win" against the whole
  diff. Collect every candidate first, then triage once.
- **Don't stop to ask which bucket.** You are holding the code and the
  investigation; the person you'd interrupt is not. A wrong bucket costs one click
  to fix later. Only a destructive or irreversible action justifies a pause. ASK
  is a line in the report, not a pause.
- **`dry` token** → emit dispositions and stop; file nothing, fix nothing.
- **`audit` token** → judge tickets that already exist. Same matrix; dispositions
  become keep / merge-into / close-as-folded / close-as-not-worth.
- **No tracker access?** Still run the whole pass. Say the dedupe search was
  skipped, and turn each FILE into a drafted ticket (title, body, labels) for the
  user to create.

## 1. Collect the candidates

Everything this session turned up that is *not* the work at hand: pre-existing
issues a code review flagged, things noticed while editing, surprises in prod
data, gaps a test exposed, "we should probably…" asides. Include things already
fixed in passing: they show FOLD working, they aren't tickets.

For each, get three facts before judging it: **what breaks, who is affected, and
what the fix actually touches.** If you can't state the third, you can't judge
effort, so go read the code.

## 1b. Dedupe first: the cheapest outcome there is

Search the tracker on the whole batch **before** you estimate anything. A
finding an existing ticket already covers costs one comment: no estimate, no new
ticket. Estimate first and search last, and you pay for a judgment you then
throw away, or more often, you file the duplicate.

Search the distinctive nouns (the error string, the file or function name, the
record ID, the feature), not a paraphrase of the summary you were about to
write. Include **old and closed tickets**: an old To Do that already
diagnoses your finding is the best result available, and you only find it if
you look. Keep the query small: the fields you need, a capped result count, the
likely projects.

- **Already covered** → comment the new evidence on that ticket and say which key.
- **Covered only by the host ticket or its parent** → not a home. That ticket
  closes when this work ships, and the finding goes with it. Comment it there
  prefixed `leftover:` so the close-out re-triages it, and report it as
  `DEDUPE → <KEY> (host — re-triage at close)`.
- **Partially covered** → widen the existing ticket rather than creating a sibling.
- **Genuinely uncovered** → continue to §2.

## 2. The cut: the value/effort matrix

Every finding that no existing ticket covers lands in exactly one cell. **Effort
is scored first**, because folding is what keeps volume down: a quick win is
worth folding even at low value, because the ticket costs more than the fix.

|  | **Fold-able**: rides the open diff (§2a) | **Bigger lift** |
|---|---|---|
| **Critical** (§2d) | **FOLD**, unless §2c applies | **FILE**, marked urgent (after §2e) |
| **Moderate** | **FOLD** | **LOG** — real, but not a ticket |
| **Low** | **FOLD** if trivial, else **DROP** | **DROP** — the worst value/effort corner |

**Only the top-right cell creates a ticket.** A bigger lift has to be *critical*
to be worth displacing work someone already prioritized. Everything moderate
goes to LOG: durable and searchable, but out of the backlog.

**The axes.**
- **Effort is relative to the work at hand**, not absolute hours: *can this ride
  the diff that's already open?* §2a is the test, §2b is how to price it
  honestly, §2c lists what forces a fold out.
- **Value is a severity threshold** (§2d), with a deliberate middle band.

**It's the ordinary value/effort matrix, tuned for a batch.** Do now and
fill-in map to FOLD, plan it to FILE, don't to DROP. Two differences are on
purpose: a 20-minute fix whose host PR has already merged counts as a *bigger
lift* here, and a finding that is high value only because it recurs doesn't earn
a ticket. Only critical severity does.

**Exits around the grid**: dispositions a pass can reach outside the cells.
- **DEDUPE**, before the grid (§1b): an existing ticket already covers it.
- **ASK**, beside it: it isn't engineering work. It's a question only the
  product owner can settle, or someone waiting on an answer. One line in the
  report addressed to the user. A five-minute message filed as a ticket sits for
  weeks *and* never gets sent.
- **ATTACH**: fold-able in kind, but the work it belonged with has already
  merged. A ticket labeled to ride along with the *next* PR that touches that
  code, not scheduled on its own. Limit two riders per PR, or you've rebuilt the
  bloat as one unreviewable PR.
- **MERGE**, after the grid (§3): several survivors from one parent become one
  ticket.
- **The budget** (§5): one new ticket per pass caps the top-right cell.

**LOG** means: append to `FINDINGS.md` at the repo root (create it if absent),
or wherever your team keeps a findings log. One heading per finding: what
breaks, who's hit, file and line, the date, the evidence. Committed with the
work, so whoever next touches that code finds it with a grep, and `/work` step 2.5
reads it to fold entries into a diff that's already open there. It is the answer
to "this is real, but nobody is going to schedule it."

### 2a. Effort axis: is it fold-able?

All of these, or it isn't a fold:

- same repo, and same file or same kind of behavior as the work at hand
- covered by existing tests or one obvious new test
- it doesn't re-open a finished check in a way that costs more than the fix (a
  re-review of a two-line change is cheap; re-doing a long manual QA pass is not)
- **the work it rides on is still open**: the branch hasn't merged, so a new
  commit doesn't mean another CI run, redeploy, and re-QA
- **it doesn't change a contract another service or repo depends on**. That
  blocks a fold regardless of line count, because the cost is in the other repo
  and in deploy ordering, not in your diff

### 2b. The effort estimate is the input everything else rests on

A wrong estimate corrupts every decision after it. Two ways it goes wrong:

- **Fold-ability expires.** A one-line query guard looks cheap. But if its branch
  merged an hour ago and is on its way to prod, folding it means a new commit,
  CI, a redeploy, and re-QA, which is a bad trade for a guard that has never
  fired in production. **Ask *when*, not just *what*.**
- **An estimate that skips the callers is a guess.** Tightening a validation
  check looks like two lines. If another caller sends input the new check
  rejects, those two lines break that caller. **Read who calls it before you
  price it.**

When you can't estimate confidently, that uncertainty is a reason not to fold
(§2c): file it and say the estimate is the open question. Guessing low is the
expensive mistake. A wrong FILE costs one ticket; a wrong FOLD can break
production.

### 2c. The only things that override a fold

- it's in a **different repo**
- the decision **isn't yours**: a business call, another team's code, a question
  for the product owner
- it's a **migration** or a **shared-contract change** that needs its own review
- the **right behavior is unclear**
- it would **more than roughly double** the diff under review

**A finding can split.** Fold the unambiguous half; ticket the half that needs a
decision. Example: a delete endpoint has a missing `return` (an empty input falls
through to deleting everything: fold it now) *and* an open question about which
roles may call it at all (needs the domain owner: that half is the ticket).

### 2d. Value axis: weighed only for what didn't fold

- **Critical**: reachable security hole, data loss, wrong money, prod down,
  user-visible breakage → **FILE**, marked urgent.
- **Real but moderate**: a genuine defect nobody is blocked on → **LOG**. This is
  where backlog bloat comes from: each item is defensible alone, and together
  they're a pile nobody prioritizes.
- **Low value** → **DROP**. **Say what you dropped and why**, one line each,
  never silently.

**Only one finding?** Then this skill isn't needed. Hand the user a short
value-vs-effort read and let them decide. The reverse also holds: **inside a
pass, don't hand each finding back for that kind of read.** That reports to a
human, and this skill decides without stopping. The one exception is a DROP or
LOG you expect the user to argue with: say so on that report line and let them
pull it up themselves.

### 2e. Two checks before any FILE

- **Measure before you file.** If the severity rests on a fact you haven't
  checked, you're holding a question, not a defect, and the check is often
  cheap enough to just do. "It's slow and live in prod" is not a finding if
  the slowness was only measured somewhere else. **File what you measured,
  not what you inferred.** If measuring is expensive, file the *question* and
  say "unverified in prod" in the first line.
- **Price the fix, not the symptom.** A "one config line" fix isn't one line if
  the resource it points at doesn't exist yet. Confirm what the fix assumes is
  really there before you size it; the real size can move it from FILE to DROP.
  Guessing the fix small inflates a DROP into a FILE, the mirror of guessing it
  small enough to fold.

Both checks guard the same mistake: value asserted from a symptom instead of
established from the fix and its blast radius. Every claim in a ticket's
severity line should be something you checked this session.

## 3. Three or more from one parent: merge

Three or more survivors from **one** parent ticket means the parent's scope was
wrong, not that you found three tickets. **Merge them into one ticket with a
checklist.** Exception: a finding far more severe than the rest gets its own
ticket. A security hole buried as checkbox #3 is a hole nobody sees.

## 4. Place every ticket: now or later, but never reorder the board

A ticket filed into the backlog with no call on *when* is a ticket nobody looks
at again; people read the board, not the backlog. So every ticket this pass
files gets a **placement**, decided here from the evidence you already gathered:

- **NOW** → the active sprint, lane To Do. Use it when any of these hold:
  - it's live today and user-visible, or it's wrong money;
  - it carries the fast-follow label;
  - a hard date falls before the active sprint ends, or within ~6 weeks (or the
    fix's lead time) if sprints run longer. Read the sprint's end date instead of
    assuming two weeks; some teams run quarter-long sprints;
  - someone is blocked on it.
- **LATER** → the backlog, with a **due date** whenever a date applies, so it
  surfaces before it bites. Use it for latent issues, items with no date
  pressure, and hard dates far enough out to schedule later. Set the due date to
  the last safe start, not the deadline itself.
- **A merged ticket with mixed urgency:** if the urgent item is small, split it
  out as its own NOW ticket (or ship it straight away). Otherwise the whole ticket
  takes the placement of its most urgent item. Say which you did.

Print the placement with its one-clause reason on the report line, so the user
can overrule it at a glance. Usually they won't; that's the point. (If your team
wants every new ticket in the backlog regardless, drop NOW and keep the due dates.)

What stays off-limits is **rank**: the order *within* the sprint or the backlog
belongs to whoever owns the board. Dedupe against the board, yes; reorder it,
no. Also give each filed ticket:

- **severity + evidence**: what breaks, who's affected, whether it's live today.
  That's the backing for the placement.
- **A label saying it was found during other work**, on every ticket this skill
  files (e.g. `found-in-flight`; use your team's name for it). It lets anyone
  filter the backlog down to requested work. **Mandatory, not encouraged:** a
  filed ticket without it is a defect in this run, because anything keyed on the
  label (a board filter, a fan-out check) is only as reliable as the weakest
  filing. Set it when you create the ticket, not as a follow-up edit.
- **A fast-follow label** (e.g. `fast-follow`) when it's that, and only then. It
  implies NOW.
- **No priority field**, and no claim that it belongs above or below a specific
  other ticket.

## 5. Act

No pause.

**Budget: one new ticket per pass.** A second is allowed if the report prints
its §2c reason next to the first. **A third means stop**: either they're one
ticket with a checklist (§3) or they belong in the findings log. Say so and let
the user decide. (One is a default; tune it to your team. The point of a hard
number is that every ticket is defensible on its own, which is exactly how
backlogs bloat.)

1. **Folds**: do them in the current work. If a review already passed, re-review
   just the changed file and say so. If that turns out expensive, the finding
   now has a §2c reason: move it to FILE.
2. **Merges**: one ticket, checklist body, each item keeps its evidence.
3. **Files**: run §2e on each first, dedupe once more, then create them in one
   batch with the label. Pass each ticket's §4 placement too: NOW → active
   sprint + To Do; LATER → no sprint, plus the due date if one applies. Read it
   back: a NOW ticket missing the sprint field is invisible on the board.
4. **Drops**: no ticket, but listed in the report.
5. **Cross-link**: each new ticket cites the parent; the parent gets a comment
   naming the new keys.

## 6. Report

```
**Triage:** N findings → D deduped · F folded · M merged into K · X filed · L logged · A attached · Q asks · R dropped

DEDUPE  <finding> → <KEY> — already covered; commented
FOLD    <finding> — fixed in <where>
MERGE   <a, b, c> → <KEY> — <shared theme>
FILE    <KEY> [NOW · <sprint> | LATER · due <date>|none] — <what breaks, who's hit> — <why that placement>
ATTACH  <KEY> — rides the next PR touching <code>
LOG     <finding> — added to FINDINGS.md
ASK     <finding> — for you: <the question, or who is waiting>
DROP    <finding> — <why it isn't worth a ticket>
```

One line per finding. If many findings came from one ticket's work, say the
ratio plainly.

## When to run it

**Once, at the end of a task, before the PR opens.** FOLD only works while the
diff is still open (§2a). Run triage after the PR is up and every finding
routes to FILE, which turns the skill into a ticket printer. If you have an
automated build-and-review workflow, make this its last step before the
summary, and let nothing else in that workflow file tickets.
