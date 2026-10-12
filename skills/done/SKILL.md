---
name: done
description: "Tag the session [DONE] — and nothing else; it stays open. The done-rename.sh UserPromptSubmit hook retitles the session \"[DONE] X\" (stripping any existing lifecycle tag such as [WAIT] first) and blocks the turn instantly (no LLM turn, no codify pass, no report). /compound is DECOUPLED — run it separately before closing out. \"/done fast\" behaves identically. Sibling: /wait parks a session as [WAIT] (blocked on external)."
disable-model-invocation: true
---

`/done` tags the session as finished and does nothing else — the session stays open. In normal operation **you will never read this body**: the `done-rename.sh` UserPromptSubmit hook intercepts `/done` (and `/done fast`), prefixes the session title with `[DONE]` (stripping any existing lifecycle tag first — a `[WAIT] X` becomes `[DONE] X`, never `[DONE] [WAIT] X`), and **blocks the turn** — no LLM turn, no codify pass, no report. The tags are a convention: no prefix = active, `[DONE]` = finished, `[WAIT]` = blocked on an outside answer.

**/compound is decoupled.** /done does not chain it. Mining the session for durable lessons is a separate, manual `/compound` run, so /done stays clean and instant.

**Fallback — if you ARE executing this body**, the hook did not block (settings.json not read, hooks disabled, or the prompt leaked through with different args). Then: emit a single clean one-line confirmation that the session is tagged `[DONE]`, **do not** run /compound, and flag the wiring — check the `UserPromptSubmit` entry in `~/.claude/settings.json` and the `done-rename.sh` script it points at (see `substrate/hooks/README.md` in this repo for the install).
