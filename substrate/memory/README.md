# The memory system

Several Tier-3 skills (`/compound`, `/tend-memory`, `/retire`, and to a lesser extent `/handoff`) assume a small, file-based memory store. This is the most involved substrate piece — adopt it only if you want the self-improving-suite loop. Here's the model.

## Layout

```
memory/
├── MEMORY.md          # the always-loaded index — one line per fact, hard size budget
├── <topic>.md         # on-demand topic files (loaded only when relevant), NOT counted against the index budget
└── ARCHIVE.md         # cold store for retired entries — never loaded
```

- **`MEMORY.md`** is the lean index that loads into context every session. Keep it tight (a line or two per memory, pointing at a topic file). It has a hard budget — content past it silently doesn't load.
- **Topic files** hold the actual detail. Each is one fact/area; loaded on demand when the work touches that area.
- **`ARCHIVE.md`** is where retired index lines go — out of the loaded index, but never destroyed.

## Who uses it

- **`/compound`** — after a session, mines it for durable lessons and *appends* them (index line + topic file). Append-only by design.
- **`/tend-memory`** — the garbage collector `/compound` lacks: losslessly compresses the index when it's over budget (detail stays in the topic files).
- **`/retire`** — moves a stale index line to `ARCHIVE.md` without deleting its topic file. One move from restored.
- **`/handoff`** — reads memory as one input when composing a continue-prompt (soft dependency).

## Getting started

Copy `MEMORY.md` (the skeleton in this folder) into your config's memory directory and start adding lines as `/compound` surfaces lessons. The skills create topic files and `ARCHIVE.md` as needed.
