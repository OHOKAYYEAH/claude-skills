---
name: notes
description: Drop-in scratchpad. Renders the text you pass after `/notes` into a clean bulleted list under a timestamped "Your Notes" header. No editing, no reordering, no commentary — pure verbatim formatting so future-you can re-orient or discard at a glance, and know when you left it.
disable-model-invocation: false
---

A self-contained notes pad. You invoke `/notes <text>` to leave yourself a reference drop — usually right before stepping away — so when you return, the first thing you see is your own pre-written context, untouched.

## Output shape

A long literal divider line on its own line — at least 60 dashes (e.g. `------------------------------------------------------------`) — followed by a blank line, then the header line, then the parsed bullets. Nothing else. No preamble, no signoff, no meta. The long dash string is intentional: a short markdown `---` renders too short to read as a real separator.

The header line is **Your Notes** followed by an em-dash and the timestamp of this drop, e.g.:

```
**Your Notes** — Thu Jul 2, 2026 · 3:45 PM
```

Since a note often sits parked for days, the stamp is the "when did I write this" anchor — it's why the timestamp lives right on the header where the eye lands first.

## Timestamping

- Get the real wall-clock time with a single `date` call — do **not** guess it or reuse "today's date" from context (that has no time-of-day, and may be stale). Exact command: `date '+%a %b %-d, %Y · %-I:%M %p'` → e.g. `Thu Jul 2, 2026 · 3:45 PM`.
- This one `date` call is the *only* tool call the skill makes. If it somehow fails, fall back to the date from context with no time (`Thu Jul 2, 2026`) rather than inventing a time.

## Parsing the notes

- Accept any reasonable delimiter you use. Likely shapes include: numbered (`1) ... 2) ...`, `1. ... 2. ...`), hyphen/bullet (`- ...`, `* ...`), pipe-separated (`note one | note two`), slash-separated (`note one / note two`), double-dash (`note one -- note two`), semicolons, or just a single sentence with no delimiters.
- Be generous — if you clearly intended multiple items separated by some character, split on it. Use judgment: a `/` inside `path/to/file` is not a delimiter; a `/` surrounded by spaces between two clauses probably is. Same logic for `-` (avoid splitting hyphenated words or flags like `--no-verify`).
- If there are no clear delimiters, render the whole thing as a single bullet.
- Render each parsed item as its own bullet, in the order you provided. Preserve the wording **verbatim** — no paraphrasing, no editorializing, no reordering, no added commentary, no helpful expansions. Preserve inline backticks, slash commands, filenames exactly as written.
- If `/notes` was invoked with no arguments at all, output a single line: `(no notes)` — and stop. Do not invent content, and skip the `date` call (nothing to stamp).

## Hard rules

- **No editing.** Don't fix typos, don't expand abbreviations, don't rephrase for clarity. If you wrote `chk login thing`, the bullet is `chk login thing`.
- **No reordering.** Order is whatever you typed.
- **No opinions.** Do not add a recommendation, a "first I'd suggest…", or a synthesis bullet. This is not `/recommend` — that exists separately if you want it.
- **No file writes, no investigation, and exactly one tool call — the `date` stamp.** Beyond that single `date` call, it's a pure read of the argument string → formatted output. No searching, no reading files, no acting on the notes' content.
- **No trailing commentary.** Don't say "let me know if you want me to act on these." End at the last bullet.
