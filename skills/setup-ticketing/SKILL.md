---
name: setup-ticketing
description: Install a lightweight, AI-first, in-repo ticket system into the
  current project — a tickets/ dir of one-file-per-ticket markdown with YAML
  frontmatter, no index file (grep is the index), plus a CLAUDE.md block that
  declares the repo's tracker so every future session (and tracker-aware skills
  like done-check, postmortem, handoff) discovers it automatically. For small
  repos that don't warrant a hosted tracker (Jira, Linear). Fire ONLY on an explicit request — "set up
  ticketing here", "give this repo tickets", "/setup-ticketing" — never
  proactively because a repo happens to lack a tracker; it writes files and a
  convention, so a spurious fire has teeth. REFUSES repos whose CLAUDE.md
  already declares a tracker (e.g. a repo already on Jira) — one repo, one
  tracker. NOT a daily ticket-CRUD skill — after setup, filing/closing tickets
  needs no skill at all; the conventions block teaches every session to do it
  with plain file edits. NOT /create-skill (authors skills; this installs a
  data convention).
disable-model-invocation: false
argument-hint: "[optional: ID prefix override, e.g. AB]"
---

Install the ticket system into the project in scope, then get out of the way.
The system is the deliverable; this skill should never be needed twice in the
same repo.

**Why this shape** (context for judgment calls, not dogma): it assumes you
interface with tickets through Claude Code — so the format optimizes for
model reads/writes over human browsing. One file per ticket keeps a ticket
one cheap targeted read. **No index file, ever** — in practice a
BACKLOG.md index bloats into inline prose walls and drifts from reality;
`ls`+`grep` over frontmatter answers every board question with zero drift.
Status flips in place (no moves to done/) so paths and IDs stay stable
forever.

## 0. Guard

- Explicit request only; never proactive.
- Read the repo's CLAUDE.md first. If it already declares a tracker — Jira,
  another system, or a previous tickets/ install — **surface that and stop**.
  One repo, one tracker; migrating is a different conversation.
- A `tickets/` dir that already exists without a CLAUDE.md block is a
  half-install: say so and offer to finish (write the block), not re-init.

## 1. Derive the prefix

Uppercase initials of the hyphenated repo name: `acme-budget` → `AB`,
`dnd-ai-vault` → `DAV`. `$ARGUMENTS` overrides. State the prefix in the
final report — it's the one thing worth the user noticing. IDs are `PREFIX-NNN`,
zero-padded to 3, sequential, **never reused** — a dropped ticket's number is
retired with it.

## 2. Create the structure

`tickets/` at repo root (+ `.gitkeep` only if no tickets are filed in the
same session). Nothing else — no README, no template file, no index. The
conventions live in one place (CLAUDE.md block below); duplicating them into
tickets/ would just create a second copy to drift.

## 3. Write the CLAUDE.md block

Append to the project's CLAUDE.md (create the file if the repo has none),
adapting the prefix. This block is the whole daily-use system:

    ## Tickets (in-repo tracker)

    This repo's tracker is `tickets/` — one markdown file per ticket,
    `tickets/AB-NNN-short-slug.md`. No external tracker, no index file: `ls`+`grep`
    is the board. Skills that file or check tickets (postmortem,
    done-check, handoff) file HERE.

    ---
    id: AB-NNN          # PREFIX + 3-digit seq; next = highest existing + 1; never reuse
    title: One-line summary
    status: open        # open | doing | done | dropped — flip IN PLACE, never move the file
    priority: p2        # p1 now-ish | p2 normal | p3 someday
    created: YYYY-MM-DD
    blocked_by: [AB-004]   # optional — omit unless real
    tags: [artifact]       # optional — omit unless useful
    ---
    Body: freeform, as short as the idea allows — why it matters, rough
    acceptance shape, links. On close, append one line:
    "Done YYYY-MM-DD: <what shipped, sha>" or "Dropped: <why>".

    Live board: `grep -H '^status:' tickets/*.md | grep -v -e done -e dropped`
    File tickets for: decided follow-ups, parked ideas worth keeping, scoped
    chunks of future work. Not for in-flight session state (that's the
    session/handoff), not for someday-maybes not worth a file.

## 4. Land it

Follow the project's commit convention (for a small solo repo,
often commit+push directly). If tickets are being filed in the same breath —
the usual dogfood case — file them first, one commit for the lot.

## 5. Report

One line: prefix, path, board command, and (if any) tickets filed. The right
follow-up isn't a skill health-check — it's simply filing the first ticket.
