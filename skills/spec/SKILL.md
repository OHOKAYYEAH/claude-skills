---
name: spec
description: >-
  Freeze the intent agreed in a discovery thread into a short FROZEN SPEC before
  the build: intent, success criteria that each name how they're verified, in
  scope vs deferred, a feature/bugfix/refactor lens, and the approved mockup.
  Written to the ticket (memory only without a tracker) so it survives
  compaction and is the baseline /work plans from and /spec-check checks
  against. Fire on "spec this", "freeze/lock the spec", or chained by
  /work or a project ship skill. NOT /interview (intent still open), NOT
  /spec-check (checks a build against the spec), NOT /mockup (locks the look,
  which this links).
disable-model-invocation: false
argument-hint: "[optional: ticket key or feature — omit to spec the current thread] [optional \"nested\": an orchestrator owns the approval stop]"
---

**Fire only when the intent is settled** — the user says so, or an orchestrator (`/work`,
or the project's ship skill if it has one) calls this at the start of a build. Never
mid-discovery: freezing a half-formed idea turns an open question into a false requirement.

Discovery is the open-ended part of the process: ideas bounced back and forth, sometimes a
`/mockup` or `/interview`. This skill closes it. It distills what was agreed into one short
artifact that outlives the conversation. The build plans from it, and at the end
`/spec-check` asks whether the build matches it. A spec that exists only in the chat
gets lost when the context is compacted; a frozen one doesn't.

## 1. Distill

Pull the settled intent from the thread, plus any ticket, prior spec, or approved
`/mockup` design spec in play. You're capturing a conclusion, not reopening it: fill every
field the conversation already answers, and leave real blanks for step 2.

**Re-freezing?** If a `🔒 FROZEN SPEC` already exists for this scope (step 3's lookup),
start from it and change only what the thread changed. The new write supersedes it.

## 2. Coverage pass — thin, scope-adaptive

Catch what a tired person skips; don't interrogate. Check the core plus the one lens that
matches the work type. Ask the user only about gaps that would **change the build**,
batched, once. Anything still open becomes an explicit **open question** in the artifact,
never a silent omission.

- **Core:** who it's for; success criteria; the in/out boundary (the deferred list is as
  valuable as the in-scope one); risks and unknowns.
- **feature** → behavior, including the error / empty / loading states, plus any
  performance, security or data/migration impact.
- **bugfix** → repro, root-cause hypothesis, regression radius, the guard test.
- **refactor** → the invariant to preserve, blast radius, how equivalence is proven.

**Every success criterion names its check** — `test`, `QA: <what to walk>`, or
`inspect: <what to read>`. That turns the criterion into something `/spec-check` can
verify and the QA pass can walk. A criterion you can't name a check for is still vague;
sharpen it or move it to open questions.

## 3. Home — ticket first

1. **The ticket.** A key in the args or in the session → use it. The project has a tracker
   but no ticket yet → chain **`/ticket`** with the intent line to find or file one (add its
   `file` token when no build is starting now, so the ticket lands in the backlog rather
   than In Progress), then use the key it returns. Write the artifact as a **comment** (not
   the description, which is the ticket's own record); the newest `🔒 FROZEN SPEC` comment
   wins. On Jira via the Atlassian MCP, for example, that's `addOrEditJiraIssueComment`
   (`addCommentToJiraIssue` on a v1 connection).
2. **No tracker** → a `project`-type memory `spec-<kebab-title>.md` in this session's
   memory dir, with its `MEMORY.md` pointer. It's temporary: delete the file and its
   pointer once the work lands, or it becomes cruft.
3. **A repo file or scratch doc** only on the user's explicit ask. Say once that a spec
   committed to the repo goes stale the moment the build diverges from it.

Lookup order for an existing frozen spec (step 1, and `/spec-check`'s lookup by scope): the
ticket's newest `🔒 FROZEN SPEC` comment → a `spec-*` memory matching the scope → none.
`/work` also accepts intent the user already ratified elsewhere (a handoff, the ticket's
criteria) and calls this skill only when there is none.

## The artifact

A distillation, not a document. Use `—` for a field that doesn't apply rather than
padding it.

```
🔒 FROZEN SPEC — <title> · <feature|bugfix|refactor> · <YYYY-MM-DD>
ticket: <KEY or —> · supersedes: <date of prior freeze or —>

Intent: <one line — what changes in the world>
For: <who it's for / who's affected>

Success criteria:
  1. <observable "done looks like"> — check: <test | QA: … | inspect: …>

In scope:
  1. <precise about boundaries: which screen, which entities, the exact rule>
Deferred / out of scope:
  - <what we chose not to do — and why, if it matters>

Look: <mockup frames path (/mockup saves approved frames to a git-ignored local dir) + its
       design calls — approved | pending the caller's front stop> | —
<lens — feature: behavior + states + NFRs | bugfix: repro / cause / radius / guard test
       | refactor: invariant / radius / equivalence check>

Open questions:
  - <unknowns to settle before or while building>
```

## 4. Hand off

- **Standalone:** show the artifact and where it lives, in one glanceable line on top. Then
  end the turn with the question the whole skill exists for: *"Frozen — change anything
  before we build?"* This is the front checkpoint where the user reviews the spec.
- **`nested`** (an orchestrator called this): return one line — `Spec: frozen at
  <KEY comment | memory path> — <N> criteria, <N> open questions` — plus the artifact, and
  **return to the caller**. The caller owns the approval stop and folds it into one it
  already has, so the user isn't asked twice.

Changes after the freeze but before the build are a re-freeze (step 1). Once the build is
running, a changed intent is a new freeze, not an edit to the old one. That way
`/spec-check` always compares the build against a fixed baseline.
