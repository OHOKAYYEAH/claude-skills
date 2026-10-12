---
name: explain
description: >-
  Unpack the assistant's most recent action: what it did, why that approach, and
  one concept worth learning. Fire when the user signals they lost the thread
  ("explain that", "wait, what did you just do?", "I'm not following"),
  including mid-prompt. The skill itself only explains; if the surrounding
  prompt asks for more, do that after. Do not self-trigger. NOT /contextualize
  (re-grounds the subject, not the action).
disable-model-invocation: false
argument-hint: "[optional — the specific part that was unclear]"
---

The user didn't follow the last thing you did. Unpack it — and explain what you **actually**
did, not a tidied-up version of it.

If an argument was passed, narrow to that specific part rather than re-explaining
everything.

## Output shape

Three sections, these headings, in this order:

```
## What I did
## Why that way
## Worth learning: <the named concept>
```

- **What I did** — the actual sequence, in order, in plain language. Name the real files,
  commands, and tools. If you took a wrong turn, backtracked, or something failed and you
  retried, say so — the detour is usually the part that was confusing.
- **Why that way** — the reasoning, and at least one alternative you rejected and what
  made you reject it. "Why not the obvious thing" is often the whole answer.
- **Worth learning** — one specific, nameable, searchable concept (a named pattern, a
  protocol, a tool's actual mechanism), plus one line on how it applied here. Not a broad
  field. "React hydration mismatches" — yes. "Learn more about React" — no.

## Rules

- **Calibrate to a junior-to-mid engineer.** Assume solid general programming knowledge,
  don't assume familiarity with this codebase's conventions or the specific library.
- **This skill does not continue the work.** No edits, no new commands, no "and while I
  was here" — within the explanation itself. It is a read-only account of what already
  happened; the one exception is a cheap read (open a file, show a diff) purely to
  illustrate it. **Scope that to the skill, not the turn:** when `/explain` was sequenced
  inside a larger prompt ("explain that, then fix it"), finish the explanation, then carry
  on with the rest of the prompt as normal. It's a read-only *pass*, not a stop sign.
- **Be honest about uncertainty.** If you did something because it's the convention here
  rather than because you reasoned it out, say that. If a step was a guess that happened
  to work, say that too — a confident-sounding explanation of a guess is worse than no
  explanation.
- **Skip the preamble.** Start at `## What I did`.
- Keep it tight. Three short sections beat one long one; the user asked because they want to
  understand it, not to read an essay.
