---
name: retire
description: Retire stale auto-memory entries from the loaded index (MEMORY.md) LOSSLESSLY — move the index line to a cold ARCHIVE.md (never loaded) and leave the topic file on disk, so nothing is destroyed and any entry is one move from restored. The RETIREMENT half of the memory loop that /compound (append) and /tend-memory (compress) don't cover. Compression has a floor (~⅓ of the index is un-trimmable link overhead); retirement is the real lever against monotonic growth. Use when MEMORY.md is near/over its ~24.4KB load budget and contains discharged/expired/superseded/event-log entries. Pass "apply" to archive after proposing.
disable-model-invocation: true
argument-hint: "[optional path to a MEMORY.md, and/or \"apply\"]"
---

# Retire — auto-memory index GC (the eviction half)

`MEMORY.md` is the table-of-contents **loaded into context every session**, against a hard ~24.4KB budget (over it, the index truncates at load and memories silently stop surfacing). `/compound` only *appends*; `/tend-memory` only *compresses* (and compression has a floor — ~⅓ of the file is the un-trimmable `[file.md](file.md)` link prefix, duplicated per entry). So without eviction the index grows monotonically toward the wall. **This skill is the eviction half: it removes entries that no longer earn a load-every-session slot — losslessly.**

## North star
The loaded index should hold **durable rules that change future behavior**. It should NOT hold **event-logs of completed work** — what shipped/merged/filed lives in the tracker, git, and the code. Retire the latter; keep the former.

**Store shape:** the budget urgency above describes a hand-rolled **hierarchical** store (a lean `MEMORY.md` core + on-demand topic files). On a flat **harness-native** store (one frontmattered file per fact + one-line `MEMORY.md` pointers), the lossless move-to-`ARCHIVE.md` mechanics port unchanged, but run only on explicit ask — the platform owns that store's hygiene. "Lossless" is non-negotiable: retiring = **moving the index line to a cold `ARCHIVE.md`** (same dir, never loaded) and **leaving the topic `*.md` file untouched on disk**. No fact is destroyed; restoring an entry is just moving its line back.

## What to retire vs keep (the judgment, per entry)
**RETIRE** (move to ARCHIVE.md) when the entry is:
- **Expired** — a dated/"temporary" obligation whose date has passed (e.g. "expires 2026-05-01", "this-week-only hack"), or a workaround past its stated expiry or removal condition.
- **Superseded** — a newer entry, or a shipped fix, replaces what it described (the entry's own text often says SUPERSEDED / RESOLVED / dead).
- **Event-log / completed-project history** — narrates what happened ("shipped X", "PR #N merged", "filed TICKET-###", a project's progress notes) and the durable facts now live in git, the tracker, or the code. The memory rules already say *don't store what the repo records* — these were retire-on-completion by that rule; they just never got retired.
- **Time-bound, discharged** — a state note whose window has closed (e.g. "staging is pre-prod right now" once the deploy lands).
- **Cheaply re-derivable** (lean over cruft) — a fresh session gets the same fact from the code, a CLAUDE.md, git or tracker history, or one quick live query (`dig`, SQL, a CLI status). A near-verbatim duplicate of loaded CLAUDE.md content is the clearest case. When unsure between keep and retire, lean.

**KEEP** (leave in MEMORY.md) when the entry is:
- A **durable rule / preference / convention** that changes future behavior (path-alias scheme, "create PRs via the PR-helper script", a wrong-DB gotcha, a branching model). **Keep these even if the originating work shipped** — the rule recurs, the event doesn't.
- A **recurring foot-gun** or hard-won workaround still in force.
- **Live project state** (an open ticket's context, an unshipped follow-up).

When an entry is *part* durable, non-re-derivable rule + *part* event-log or re-derivable detail, don't retire it — KEEP it, and **trim the topic file down to the nugget that isn't re-derivable** (or note it for `/tend-memory`). Retire only whole entries that are wholly stale or wholly re-derivable.

## Procedure

1. **Resolve the store — verify it's the populated one.** Default: the active project's `MEMORY.md` (typically under `~/.claude/`). Sanity check: confirm the `MEMORY.md` you open has entries; if a reminder path names an empty location, target the one that actually holds the store. An explicit path in args overrides.
2. **Back up first.** `cp MEMORY.md MEMORY.md.preretire-bak` before any edit (the store may not be git-revertable).
3. **Measure — both ceiling dimensions.** `wc -c < MEMORY.md` vs ~24.4KB **and** `wc -l < MEMORY.md` vs 200 lines (platform hard limit is 200 lines OR 25KB, whichever first — the line ceiling can bite before the byte one); `grep -c '^- \[' MEMORY.md` (record it). If the index is **hierarchical** — `MEMORY.md` as the lean always-loaded core, the bulk in on-demand `domain-*.md` files — retire from whichever file carries the stale entry; the core is the priority (domain files are uncapped, but eviction still helps).
4. **Find candidates.** Surface lines whose hook carries a staleness marker — `grep -niE 'expire|supersed|SHIPPED|RESOLVED|FIXED|dead|done|time-bound|fast-follow.*fil|merged|deployed' MEMORY.md` — but **the marker is only a flag; the verdict requires reading the topic file** to confirm it's discharged/event-log and not a still-live durable rule. For a large candidate set, delegate the per-entry read-and-classify to a subagent (give it the RETIRE/KEEP rules + the invariants below), then spot-check.
5. **Classify each candidate → RETIRE (with one-line reason) / KEEP (why durable) / BORDERLINE (flag for the user).**
6. **Propose, then archive.** Present the RETIRE list with reasons. Archive the **high-confidence** ones directly (it's reversible); leave **BORDERLINE** ones in place and list them for the user to confirm. (With `apply` in args, archive all proposed high-confidence without a second pause; default is the same — archiving is lossless, so acting on clear-stale is fine. Borderline always waits.)
7. **Archive mechanics (lossless):** for each retired entry, **cut its `- [..](..)` line from `MEMORY.md` and append it to `ARCHIVE.md`** in the same dir (create `ARCHIVE.md` with a one-line header if absent: "Retired memory index — NOT loaded each session; entries live here + their topic files remain in this dir. Restore = move a line back to MEMORY.md."). Append a ` [retired YYYY-MM-DD: <reason>]` tag to the archived line. **Leave the topic `*.md` file in place** (it's not loaded; harmless; keeps the link valid from ARCHIVE.md). Use an atomic single-write (Python/`sed -i`), not the Edit tool, if a background linter or hook may rewrite `MEMORY.md` between your read and write.

## Invariants (never violate)
- **Lossless.** Never delete a topic file or drop a fact. Retiring = moving the index line to `ARCHIVE.md`. Fully reversible.
- **Never retire a durable rule** (changes future behavior / recurs), even if its originating work shipped.
- **Entry conservation across the pair.** `MEMORY.md` count drops by N; `MEMORY.md` + `ARCHIVE.md` count is unchanged. Never lose a line.
- **Never alter** a `[Title](file.md)` link, header, section heading, or non-entry line — only move whole entry lines.
- **Borderline → propose, don't auto-retire.** When unsure it's stale, KEEP it.
- **One store per run** unless given a path.

## Report
- before/after `MEMORY.md` byte size (confirm under budget) and entry count (dropped by N);
- combined MEMORY+ARCHIVE entry count (must equal the pre-count — proves losslessness);
- the retired list (entry + reason), the borderline list (awaiting user), what was kept-despite-marker and why;
- broken-link check on the post-edit `MEMORY.md`: `for f in $(grep -oE '\]\([^)]+\.md\)' MEMORY.md | sed -E 's/^\]\(//;s/\)$//'); do [ -f "$f" ] || echo "MISSING $f"; done` → expect none.

_End with: `/go` to archive the borderline entries too (held back pending your call); high-confidence ones are already archived._

## Relationship to the rest of the loop
- `/compound` = capture (append durable rules; it should reject event-logs at the source — the upstream fix).
- `/tend-memory` = compress (tighten fat hooks, lossless; has a floor).
- `/retire` = evict (move discharged entries to cold archive, lossless; the real lever against growth).
Run `/retire` when `/tend-memory` is tapped or the index carries obvious discharged entries. The two compose: retire the dead weight, then tighten what remains.
