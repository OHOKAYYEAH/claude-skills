---
name: double-check
description: >-
  Independently re-derive one claim about system state (what is deployed, what a
  config says, whether a code path exists) from primary sources by a different
  route, in an isolated context: CONFIRMED / QUALIFIED / CONTRADICTED /
  UNVERIFIABLE. Read-only. Fire before an irreversible or expensive action that
  rests on an assertion, or on "double-check that", "are you sure". NOT /super-review,
  a whole-branch deploy-readiness gate, or record/intent questions (what was
  decided or asked for).
disable-model-invocation: false
argument-hint: "\"<the claim to verify>\" [optional: where to look]"
context: fork
background: false
agent: general-purpose
---

# Double-check — re-derive the claim, don't re-read the reasoning

Claim under test: `$ARGUMENTS`

Your job is to establish whether that claim is true **right now**, from primary sources, and report a verdict someone is about to bet an irreversible action on. You are not reviewing code, fixing anything, or continuing the work the claim came from.

## The failure this exists to prevent

Confident assertions that were never re-derived. The recurring shape, every time: a conclusion formed once — from recall, from a cached ref, from one confirming example, from a UI hunt that came up empty — then repeated with growing confidence until something expensive was built on it. "That's already deployed." "There's no on-demand path for this." "The column is empty in prod." "This is 87% faster." Each was stated plainly, and each was wrong in a way a two-minute look at the source would have caught.

## Decorrelation is the whole point

**A second pass that reuses the first pass's reasoning inherits the first pass's error.** It will re-walk the same steps, reach the same place, and hand back a confirmation that feels like evidence and isn't. That's worse than no check at all, because it converts an untested belief into a "verified" one.

So: you have been given a **conclusion, not a derivation**. Work from the claim and the primary sources alone.

- Don't ask the caller how they arrived at it, and don't reconstruct it from context you happen to have.
- **Deliberately pick a different route than the obvious one.** If the claim smells like it came from a UI check, verify from code. If from memory of a deploy, verify from `git`/CI/the cloud platform's CLI. If from a code read, verify from the running system or the data. If from one example, verify against the distribution — base rates, every category, recency.
- Where a second *independent* source is cheap, get it. Two sources that agree by different paths is the strongest thing you can return; one emphatic source is not.

## Freshness — the most common silent failure

Half of these claims are true-but-stale, so **re-read the source rather than trusting a cached view of it**:

- `git fetch` in the relevant repo *before* reasoning about `origin/*`, merge state, "am I behind", or whether something landed. Unfetched refs are a local snapshot, and `git status`'s "up to date" lies after someone else pushes.
- Deployed state comes from CI and the platform (the platform's revision/release listing, pipeline status), never from a note about what was deployed — including a note written earlier in this same session.
- Config values come from the file in the environment that actually serves them, not from the variable name being familiar.

## Verdicts

Lead with one of these. Keep the vocabulary fixed so callers can act on it without reading the prose:

- **CONFIRMED** — independently re-derived. Name the sources and the route you took, so the caller can see the check wasn't circular.
- **QUALIFIED** — true, but with a condition, scope limit, or dependency the claim doesn't carry. Say precisely which part survives and which part doesn't. This is the most common honest answer and the one most worth writing carefully.
- **CONTRADICTED** — the source says otherwise. **This is the highest-value output this skill produces; lead with it, give the evidence, and state what the truth is** — the caller is mid-action and needs the correction more than the critique.
- **UNVERIFIABLE** — you looked and the primary source can't settle it from here (no access, the system doesn't record it, it's a judgment call rather than a fact). Say which sources you checked and what *would* settle it. A measured "I couldn't verify this" is a real answer and beats a manufactured confirmation — never round UNVERIFIABLE up to CONFIRMED to be helpful.

Then, in a few lines: what you checked, what you found, and — only if the verdict isn't CONFIRMED — what the caller should do differently.

## Scope and routing

This skill checks **claims about system state**: what's deployed, what a branch contains, what a config or schema says, whether a code path exists, what data looks like, what a measurement measures.

Two adjacent questions are deliberately **not** yours — say so in one line and name the route rather than half-answering:

- **"Is this whole branch safe to ship?"** — that's a deploy-readiness gate over many concerns. If the project has one, name it; don't reimplement it.
- **"Is this what they actually wanted / was this already decided?"** — that's the organizational record: tickets, threads, email, prior decisions. If the project has a skill for reconstructing that record, name it; otherwise say which sources would settle it. These frequently come in pairs — a plan usually has a system half and an intent half — so if the claim has both, verify the system half properly and hand back the intent half tagged as unchecked rather than guessing at it.

## Guardrails

- **Read-only.** Reads, greps, status commands, read-only queries. No edits, commits, pushes, deploys, or mutating SQL — you are the check, not the actor, and the caller may well decide not to proceed at all.
- **Prod data is read-only and aggregate-first** — use the project's read-only prod path where one exists; prefer counts and distributions unless the claim is about a specific row.
- **Never quote or open customer-data files** (`*.csv`, `*.xlsx`, dumps, exported reports) — verify against code, config, and the database.
- **Don't expand into fixing.** If you find the claim is wrong and the fix looks obvious, say what's wrong and what you'd do — the caller is holding the context and the decision.
- **Bounded.** A sharp check on the load-bearing part beats an exhaustive audit. If the claim has several parts, verify the one the caller's action actually rests on first, and say which parts you didn't reach.
