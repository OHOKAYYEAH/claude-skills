---
name: confidence-check
description: >-
  Audit how well-founded a response is: tag each load-bearing claim by source
  (read this session / recalled / inferred / assumed), lead with how much of
  what matters was actually read, and name the one weak claim worth checking.
  Fire on "how confident are you", "what here is actually verified", or before
  acting on a long report. NOT /double-check (verifies one named claim).
disable-model-invocation: false
argument-hint: "[optional: what to audit — a file path, \"the ship report\", \"session\"; default is the previous response]"
---

# Confidence-check — where did each claim come from?

Target: `$ARGUMENTS` — or, if empty, the previous assistant response. A path → read that file. "session" → the standing claims this session is currently acting on.

Your job is to separate what is **known** from what is **believed** in the target, so the user can see at a glance which parts are safe to act on and which one to check first. You are not re-verifying anything — that's /double-check. You are sorting.

## Why this exists

/double-check only helps once someone knows which claim to doubt. The expensive misses don't announce themselves: "that's already deployed" (recall), "there's no on-demand path" (a UI hunt that came up empty), "87% faster" (measured warm), "9 screens affected" (counted imports, not renders). Each sat in a report stated as flatly as the claims beside it that had been read from source. Provenance is the thing that differed, and it's invisible unless someone writes it down.

## Why it runs in this context

Grading provenance means looking at how each claim was derived — which tool call, which memory, which leap. Only the context that made the claims can see that. It is the opposite of /double-check, which works *because* it's handed the conclusion without the reasoning. Keep them apart: this finds the soft claim, that one tests it.

## 1. Pull out the load-bearing claims

A claim is load-bearing if a decision or next action rests on it — "the PR is open", "all 64 suites pass", "nothing else runs these tests", "this is tracked in TICKET-123". Skip framing, opinions and recommendations; those aren't facts to source. Usually 4–10. More than ~12 means you're listing, not selecting.

## 2. Tag each by provenance — by evidence, not by feel

The trap: a session grading its own work calls things verified because they *feel* verified. So each tag is defined by what you can point at:

- ✅ **Read** — a tool result in *this session* shows it, and you cite it (the command, file:line, API response). No pointer → not ✅, however sure you are.
- 🧠 **Recalled** — from memory files, a handoff, a peer session, CLAUDE.md, or an earlier turn's assertion that wasn't itself backed by a read.
- 🔗 **Inferred** — derived from other claims, or generalized from one example or a partial search.
- ❓ **Assumed** — nobody checked; it was the default reading.

Two refinements catch the common misses:

- **Staleness demotes ✅.** A read of mutable state (git refs, CI status, deployed revisions, ticket status) stays ✅ only if nothing could have moved since — unfetched `origin/*`, a status read before another session pushed, this morning's deploy check. Give the age; demote to 🧠 when it's stale.
- **Absence is 🔗 at best.** "There's no X" backed by a search is inferred from a bounded hunt — say what was searched.

## 3. Pick the one to check

Of the non-✅ claims, which would hurt most if wrong, weighted by how close the next action is to irreversible? Name it and the check that fits:

- system state (what's deployed, a config value, a code path, data shape, branch contents) → `/double-check "<claim>"`
- record or intent (what was decided, requested, tracked, deferred) → a search of the record: the ticket and its comments, the chat thread, commit history, or a project-specific record-check skill if you have one

Offer it; don't run it. A `/go` from the user runs it — and they often wave a weak claim off because it doesn't gate anything they're about to do.

## Report

Lead with the verdict; it's what the user reads while juggling.

**Confidence: <N of M> load-bearing claims read this session — <safe to act on / act after checking #k / don't act yet>**

| # | Claim | Source |
|---|---|---|
| 1 | <claim, one line> | ✅ <cmd / file:line / API response> |
| 2 | <claim> | 🧠 <where it was recalled from> |
| 3 | <claim> | 🔗 <what it was derived from> |

**Check first:** #k — <why it matters now> → `/double-check "<claim>"` (or the record search that fits). `/go` runs it.

If every load-bearing claim is ✅, say so in the verdict line and stop — no padded table, no invented concern.

## Guardrails

- **Read-only, and no mid-audit upgrades.** Don't run checks to turn a 🧠 into a ✅ while auditing — that quietly becomes a partial double-check and hides which claims were soft when they were made. Tag what's there; checking is the follow-up.
- **Don't soften a tag to be polite.** A 🧠 on the assistant's own earlier claim is the point of the exercise, not an admission of error.
- **One check, not a queue.** Name the single most consequential weak claim; two only if genuinely tied. The table carries the rest.
