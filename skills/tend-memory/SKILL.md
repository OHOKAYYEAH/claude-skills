---
name: tend-memory
description: Losslessly tighten the auto-memory index (MEMORY.md) when it's over its per-session load budget — shorten fat index hooks while the detail stays in the topic files. Never deletes entries; the GC half that /compound (append-only) lacks. Pass a path to target a specific MEMORY.md, and/or "apply" to write after proposing.
disable-model-invocation: true
argument-hint: "[optional path to a MEMORY.md, and/or \"apply\"]"
---

# Tend-memory — auto-memory index hygiene

`MEMORY.md` is the **table-of-contents loaded into context every session**; the real detail lives in the per-topic `memory/*.md` files. When `MEMORY.md` exceeds its load budget (~24.4KB), the index gets **truncated at load** and some memories silently stop surfacing. This skill brings it back under budget **losslessly** — by tightening over-long index hooks, **never** by deleting memories.

It is the **GC half** of the memory loop: `/compound` only *appends* memory and nothing collects, so the index creeps over budget silently until recall degrades.

**Store shape:** the budget machinery here (~24.4KB / 200-line core, `domain-*.md` hierarchy) describes the hand-rolled **hierarchical** store. A flat **harness-native** store (one frontmattered file per fact + one-line `MEMORY.md` pointers) is platform-managed: the lossless tighten-the-hook move still applies to its `MEMORY.md`, but run it only on explicit ask, not on budget alarms.

**NOT** `/compound` (capture session lessons), **NOT** `/curate` (skill-suite health).

## North star
The index is a set of one-line **recall hooks**; the topic file is the **durable store**. Bloat = detail crammed into a hook that belongs in the file. So the move is always: **make sure the detail is in the topic file, then shorten the hook.** No fact ever disappears.

## 1. Resolve the store — and verify it's the populated one
Default target: the active project's memory `MEMORY.md` (typically under `~/.claude/`). **Sanity check:** confirm the `MEMORY.md` you open actually has entries; if a system-reminder path points at an empty location but the populated store lives elsewhere, target the one that actually holds the entries. An explicit path in `$ARGUMENTS` overrides.

## 2. Back up first
The memory store may not be git-revertable. `cp MEMORY.md MEMORY.md.prebloat-bak` before any edit.

## 3. Measure
- size: `wc -c < MEMORY.md` vs ~24.4KB **and** lines: `wc -l < MEMORY.md` vs 200 (platform hard limit is 200 lines OR 25KB, whichever comes first — the line ceiling can bite before the byte one)
- NOTE — the index is now **hierarchical**: `MEMORY.md` is the lean always-loaded core; the bulk lives in on-demand `domain-*.md` files (uncapped, since topic/domain files load on demand). The core is the priority; tend a `domain-*.md` only if it has genuinely bloated
- entries: `grep -c '^- \[' MEMORY.md` — this number is an **INVARIANT**; it must not change
- fattest hooks: `grep -n '^- \[' MEMORY.md | awk '{print length"\t"$0}' | sort -rn | head -20`

If it's already under budget with no >300-char lines, say so and stop — don't tighten for its own sake.

## 4. Tighten the fat hooks — lossless, verify-before-cut
For each index line over ~250–300 chars (tighten the fattest first; do enough to land comfortably under budget, ~21–23KB):
1. **Open the linked topic file.** Confirm every specific detail you're about to drop (date, ID, SHA, $ figure, finding, sub-clause) is already in the topic body.
2. If a detail lives **only** in the hook → **append it to the topic file first**, then trim.
3. Rewrite the hook to a faithful ~150–180-char one-liner: keep `- [title](file.md) — ` **exactly** (never change title or filename), keep the key identifier (ticket/PR #, SHA, file, core fact) + enough to trigger recall; drop the granular detail now living in the file.

For a large index (many fat lines), delegate the per-entry read-verify-tighten to a subagent so the caller's context stays clean — give it the invariants below, have it apply or return the rewritten lines, then spot-check its result.

## Invariants (never violate)
- **Never delete an entry.** Entry count after == entry count before.
- **Never change a `[title](file.md)` link or filename** — only the hook text after `— `.
- **Never touch** header lines, section headings, or non-entry lines.
- **Never drop a fact** that isn't already in the topic file.

## 5. Optional conservative staleness pass (propose, don't delete)
While in there, you MAY flag — for the user to confirm, never auto-act:
- an entry whose topic file no longer exists (broken link), or
- a dated/"temporary" note whose obligation is clearly discharged.

List these as REMOVE-CANDIDATES with a reason. When unsure, keep it.

## 6. Apply & report
The operation is lossless (backup taken, detail preserved in files), so applying directly is fine — but show the result. Report:
- before/after byte size (confirm under budget),
- entry count before/after (**must match**),
- # hooks tightened,
- any detail moved into topic files,
- broken-link check: `for f in $(grep -oE '\]\([^)]+\.md\)' MEMORY.md | sed -E 's/^\]\(//;s/\)$//'); do [ -f "$f" ] || echo "MISSING $f"; done` → expect none.

## Guardrails
- **Lossless or it doesn't ship.** If you can't confirm a dropped detail is in the topic file, move it down first or keep it in the hook.
- **Tighten, don't amputate.** A hook so terse it loses recall value is a regression — keep the trigger.
- **Back up before write. Always.**
- **One store per run** unless given a path; mention sibling `MEMORY.md` stores rather than silently editing them.
