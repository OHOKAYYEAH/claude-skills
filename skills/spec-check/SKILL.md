---
name: spec-check
description: >-
  Intent-fidelity check: does the built diff match its spec (a FROZEN SPEC, or
  the ratified intent /work planned from)? Runs in an isolated fork that sees
  only the spec and the code, never the build's rationale, and returns a recap:
  each criterion met / gap / diverged, gaps tagged for the caller, divergences
  listed for the caller to decide. Chained by /work after the build; standalone
  on "did we build this to spec?" or "does this match the ticket?". Without a
  frozen spec it reconstructs one from the ticket and its sources. NOT
  /code-review (is the code correct), NOT /qa (does it behave).
disable-model-invocation: false
context: fork
background: false
agent: general-purpose
argument-hint: "<spec location (ticket key | memory path | handoff path | quoted scope) or feature> [diff: <worktree path> <base ref>]"
---

Answer one question: **does the built thing match what was agreed?** Whether the code is
correct and whether it runs are `/code-review` and `/qa`'s questions. This is intent in,
conformance out.

Run in a fork on purpose. The build session has spent hours justifying every shortcut it
took; you haven't. You see only the spec and the code. That separation is the value, so
don't go looking for the build's reasoning in order to excuse a gap. Use it only to
classify a divergence (step 3).

## 1. Load the spec

Find the baseline in this order:
1. **The spec location in the args** — a ticket key (read its newest comment starting
   `🔒 FROZEN SPEC`), a memory or handoff path (read the file), or the user's approving
   words quoted inline. A handoff or quoted scope *is* the spec; don't reconstruct around
   it. A handoff is AI-written, so anything it narrows or drops from the ticket's criteria
   is a divergence, not part of the spec.
2. **By scope** — the ticket's newest `🔒 FROZEN SPEC` comment, else a `spec-*` memory
   whose title matches (scan the memory index).

Found one → it *is* the spec. Do one cheap drift check: is there a ticket comment dated
after the freeze (or the handoff or approval) that changes the ask? Carry any such drift
as a divergence; don't rebuild the spec around it.

**No frozen spec** (an old ticket, or a standalone ask on specless work) → reconstruct one.
Read this skill's `references/sources.md` (e.g.
`~/.claude/skills/spec-check/references/sources.md`) and follow it. It maps each project to
its sources and gives the rules for reconciling an ask that changed over time. Chained runs
from `/work` usually take this path too when they pass only a ticket key: `/work` treats
ratified ticket criteria as the spec rather than re-freezing them.

## 2. Load what was built

The diff in the args (`git -C <worktree> diff <base ref>...HEAD` plus untracked files from
`git status --porcelain`, because `/work` doesn't commit). If there's no diff arg, use the
ticket's landed commits or branch. Read the code behind each in-scope item. You're reading
what the code *says* it does, not running it.

## 3. Compare

For each **in-scope item** and each **success criterion**, pick one:

- **met** — the code does it. Cite `file:line`.
- **gap** — the code doesn't do it, or does part of it. Tag it:
  - `[caller-resolvable]`: the missing piece is buildable from the spec as written. The
    caller builds it.
  - `[needs-user]`: building it needs a decision the spec doesn't contain.
- **diverged** — the code deliberately does something other than the spec says, such as
  a narrower rule, an extra behavior, or a different UX. Report it; don't judge it. The
  caller holds the build's context and decides whether it stands (`/work` step 3b).
- **unverifiable here** — the criterion's check is `QA:`, so it's proven by a browser walk,
  not by reading. Pass the walk item through to the recap so the QA pass can pick it up.
  Don't mark it met.

Also check the **Deferred** list. A deferred item that shows up in the build anyway is scope
creep: mark it **diverged**.

## 4. Recap — always the last thing you emit

```
### Spec-check Recap
**Status:** <✅ built to spec | 🔧 gaps owed — caller-resolvable | ⚠️ diverged and/or gaps needing a decision | 🛑 can't verify — <why>>
**Spec:** <ticket key, when there is one · location · frozen <date> | handoff | quoted | reconstructed · drift since: none | <what>>
| # | Item / criterion | Verdict | Evidence / note |
**Gaps:** <each: what's missing · tag · where it belongs> | none
**Built differently:** <each divergence: what the spec said → what was built · what changes for a user> | none
**QA walk:** <criteria only a browser walk can prove> | none
```

When more than one applies, Status goes to the highest: 🛑 > ⚠️ > 🔧 > ✅. **🛑 is for when
there's nothing to measure against**: no spec findable and nothing to reconstruct from, or
no diff. It's never for a hard verdict. Write each Built-differently item in plain terms,
for a reader who never saw the build: what a user would notice, not which function moved.
