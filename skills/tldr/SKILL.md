---
name: tldr
description: "Compress the assistant's previous response into a high-signal summary — a bottom-line verdict plus icon-keyed bullets (✅ good / ⏳ in flight / ⬜ outstanding / ⚠️ trap / ❌ failed / ❓ unverified / ℹ️ context), each optionally carrying a short bold subject label, so a line's status and topic are both readable at a glance. **Pure compression — it deliberately ends with NO forward actions**: no Do-next, no action plan, no recommendation. Reach for /tldr when you want to understand what was said and decide for yourself what happens next. Can be narrowed with a focus argument. Chain with /recommend if an opinionated pick is also wanted."
disable-model-invocation: false
argument-hint: "[optional focus]"
---

Give me the TL;DR of your last response. High signal, low noise — compress, don't re-explain.
Assume I'm cognitively loaded or short on time.

## Shape

**1. Bottom line** — one sentence, first thing, no icon. The decision, outcome, or key finding.
If I read only this line, I know where things stand.

**2. Icon-keyed bullets** — flat, one line each, no nesting. Anatomy:

```
- <icon> **<label>** — <the line>
      │        │            └─ compressed, one line, no nesting
      │        └─ optional: one or two words naming the subject
      └─ required: exactly one, from the key below
```

The icon is the primary sorting device: scanning the left edge alone tells me which lines are
settled, which are live, which will bite me. The **label** is the second axis — it lets me find
*the lunch thing* or *the timer thing* without reading cells.

Cut reasoning, caveats, educational asides, and restatements of my question. Keep only what I
need to know or remember.

## Icon key

| | |
|---|---|
| ✅ | good / done / verified / works as intended |
| ⏳ | in flight, pending, or waiting on something — a running job, an open question with someone else, a timer that hasn't fired |
| ⬜ | outstanding — stated in the response as not-yet-done |
| ⚠️ | trap, gotcha, or constraint that will bite if ignored |
| ❌ | failed, broken, ruled out, or won't work |
| ❓ | unverified / unknown / assumed but untested |
| ℹ️ | plain context — a fact, a value, a design choice with no status attached |

**ℹ️ is the fallback, not the filler.** Never force a bullet into a status it doesn't have — a
wrong icon is worse than a neutral one. If most bullets land on ℹ️, that's the honest read: the
response was informational.

## Rules

- **Icons classify what was already said. They never add anything.** A ⬜ marks a fact of state
  the response stated ("not yet in the prod config"), not a task I'm being handed. This skill
  still emits **no Do-next block, no action plan, no recommendation** — chain `/recommend` if
  that's what I want.
- **Keep the response's order.** The icons do the sorting; reordering breaks the thread. One
  exception: a ⚠️ or ❌ that changes the bottom line gets pulled to the top and shows up in the
  bottom-line sentence.
- One icon per bullet. Never two, never a bullet without one.
- **Label only when the bullet has an obvious subject.** One or two words, bolded, em-dash after.
  If naming it would produce filler — **Note**, **Thing**, **Update** — or if the sentence *is*
  the point, skip the label and let the line run from the icon. A mix of labelled and bare
  bullets in one list is fine and normal; forcing every line to carry one is not.
- Don't also write the status in words — "✅ Guards work: tested live" not "✅ Done — guards work".
- Trailing bare facts that belong to no bullet (a path, a command) can sit on their own line
  after the list, unadorned.
- No preamble ("Here's the TL;DR…"), no closing wrap-up.

## Worked example

```markdown
**Cache layer shipped behind a flag; only the prod config flip remains.**

- ✅ **Read path** — cache hits verified locally; p95 dropped from ~420ms to ~60ms
- ✅ **Invalidation** — writes evict the key in the same transaction, covered by two new tests
- ⚠️ **Stale reads** — the admin screen bypasses the write path, so its edits stay stale for
  up to the 5-minute TTL
- ⏳ **Staging deploy** — pipeline still running at time of writing
- ℹ️ **TTL** — 5 minutes, chosen to match the upstream data refresh cadence
- ℹ️ Kept the existing client library — adding a second one for one feature wasn't worth it
- ❓ **Memory** — cache size under real traffic is unmeasured; estimate assumes ~10k keys
- ⬜ **Prod flag** — `CACHE_ENABLED` is still off in prod config

src/cache/config.ts
```

Note the client-library line carries no label — a label would just repeat the first words of
the sentence. That's the rule working, not a miss.

## Not a table

Deliberately bullets, not a table. A two- or three-column markdown table scans slightly
better on a wide terminal, and loses on a narrow one:

- The CLI demotes the **whole** table to a borderless stacked fallback as soon as any **single**
  cell wraps past four lines. On a narrow terminal (a phone SSH client, ~40 cols) a TL;DR line —
  compressed prose, not a status fragment — routinely blows that, so the table collapses exactly
  where a quick read matters most.
  `/report` survives it only because its cells are terse and budgeted to ~320 chars.
- `/report` already *is* the icon table. A second one makes two different jobs — where-things-
  stand vs. what-you-just-said — indistinguishable in scrollback.
- The icon already sits at a fixed column in bullet form, so the table's alignment win is nearly
  nil. The label column was the real gain, and the **bold label** above delivers it with no
  width cliff.

If I've added a focus below, narrow to just that slice: $ARGUMENTS
