---
name: brainstorm
description: >-
  Think a question through together before committing: restate it with the
  user's leaning, widen the options past their framing, give a tradeoff each and
  a pick with why, then hand it back for their reaction. Fire on "thoughts?",
  "let's think this through", "brainstorm names / options", "I'm leaning X
  but…". NOT a decision offload (/recommend), intent lock-in (/interview), a
  look-lock before a build (/mockup), or pricing one proposal (/matrix).
disable-model-invocation: false
argument-hint: "[optional: the question or the leaning]"
---

The user usually arrives with a rough idea or a leaning and wants a thinking partner, not
a verdict. The value is in what they wouldn't have listed themselves, so the job is to
**widen the space, then narrow it back with a committed pick**. It is a conversation: this
skill never files, builds, or edits anything, and it doesn't gate a pipeline.

The question is `$ARGUMENTS` if given, else the thing they're mulling in the surrounding
conversation.

## Shape

**The question** — one line, plus their leaning if they named one ("leaning: X").

**Options** — 4–6 genuinely different ones, each a single line: what it is, and the
tradeoff that would make them pick it or not.
- Include their own options as written, and add some from outside their framing: a
  different axis, a "neither", or a "drop the premise". Those are the ones that earn
  their keep.
- No strawmen. If an option exists only to lose, cut it.
- Naming questions: vary the angle (what it does, what it shows, what they'd say out
  loud), not synonyms.

**My pick** — one line plus the why. If their leaning wins, say so plainly, and say what
would have flipped it.

**Open thread** — at most one: the fact or taste call that would most change the answer.

End on one short question that invites their reaction ("which way are you leaning now?").
No `/go` line: there's nothing to execute yet.

## When it's visual

A UI control, a layout, a label inside a screen: prose can't settle it. Render the
options side by side as a quick static page on the real design tokens, the way `/mockup`
builds one, and show it with `/present`. Borrow `/mockup`'s rendering discipline only; its
approval gate doesn't apply here: show the sheet, then ask.
