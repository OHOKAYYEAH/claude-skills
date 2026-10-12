# Setup — the substrate the skills assume

Most of these skills are drop-in (Tier 1 in the [README](README.md#the-catalog--tiered-by-portability)). The higher tiers lean on four pieces of ambient context that *don't* travel inside a `SKILL.md`. This doc is what to put in place to unlock them. Set up only what you need for the skills you want.

---

## Install the plugin

To take a single skill, copy its folder into `~/.claude/skills/` (see the README). To take the whole suite, install it as a Claude Code plugin, `skills-suite`. It installs turned off.

**From GitHub:**

```
claude plugin marketplace add OHOKAYYEAH/claude-skills
claude plugin install skills-suite@ohokayyeah
claude plugin enable skills-suite@ohokayyeah   # only if you want the skills live
```

**From a clone or a downloaded copy:** the same, with `claude plugin marketplace add /path/to/claude-skills` as the first line.

Enabled, it adds about 11K tokens of skill descriptions to every session (`claude plugin details skills-suite@ohokayyeah` shows the breakdown). Disabled, it costs nothing, and you can still read any skill in the folder.

**Standalone plugins:** a skill meant to be used on its own ships separately, e.g. `claude plugin install tldw@ohokayyeah` then `claude plugin enable tldw@ohokayyeah` for `/tldw`. See the README's *Shipped as its own plugin* table.

Tier 3 skills install too, but won't behave correctly until their substrate (below) exists. Tier 4 is read-only example material — browse it, don't install it.

---

## 1. MCP: Chrome DevTools

**Unlocks:** `/devtools`, and the execute path of `/qa run` (which chains it). `/tdd` and `/debug` *prefer* it for browser repro but degrade to logs/tests without it.

`/devtools` drives a real Chromium over the Chrome DevTools MCP. You need:
- The **Chrome DevTools MCP server** connected in your Claude Code session.
- A Chromium reachable on a debug port (the skill attaches to `:9222` by default, or launches `chromium-browser --remote-debugging-port=9222` if nothing's there).

Without the MCP, `/devtools` detects the gap and stops cleanly with `DevTools unavailable — MCP not loaded` — it fails honestly rather than pretending.

## 2. CLAUDE.md content the skills read

A few skills **read** their connection target out of your project's `CLAUDE.md` (this is different from the many skills that merely *write* a line to it). Give your `CLAUDE.md` a block like this and `/devtools`, `/qa run`, and `/postmortem` will find what they need:

```markdown
## Local dev / environments
- Local dev server: http://localhost:3000   (the port /devtools connects to by default)
- Dev:     https://dev.example.com
- Staging: https://staging.example.com
- Prod:    https://app.example.com
- Test credentials: <where login creds live, e.g. cypress.env.json> (never paste secrets here)

## Deploy (for /postmortem)
- How a change reaches prod: <e.g. merge to main → CI deploys to your host>
- Issue tracker: <Jira project key / GitHub issues>
```

`/devtools` resolves a named env (`local`/`dev`/`stage`/`prod`) to a URL from this block; if an env has no documented URL it asks once. `/postmortem` reads the deploy mechanism + tracker so it stays generic instead of hardcoding any one project.

## 3. Hooks (settings.json)

**Unlocks:** `/done` and `/wait`.

Both commands' real behavior is a `UserPromptSubmit` hook that retitles the session (`[DONE] …` / `[WAIT] …`) and stops the turn instantly — no LLM round-trip. The `SKILL.md` bodies are just the fallback for when the hook isn't installed. To get the fast path, register the hook in your `settings.json`:

```jsonc
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "~/.claude/hooks/done-rename.sh" } ] }
    ]
  }
}
```

The script runs on every prompt and decides for itself whether it's `/done` or `/wait`. It needs `jq`. The script, install steps, and an optional tmux window-naming mode ship under [`substrate/hooks/`](substrate/hooks/README.md).

## 4. The file-based memory system

**Unlocks:** `/compound`, `/tend-memory`, `/retire` (hard), and improves `/handoff`. This is the most involved piece — adopt it only if you want the self-improving-suite loop.

These skills assume a small, hierarchical memory store:
- **`MEMORY.md`** — a lean, always-loaded index (one line per fact, hard size budget).
- **`domain-*.md`** / topic files — loaded on demand, not counted against the index budget.
- **`ARCHIVE.md`** — a cold store for retired entries (never loaded).

The division of labor:
- `/compound` mines a finished session for durable lessons and appends them (append-only).
- `/tend-memory` losslessly compresses the index when it's over budget (the GC that `/compound` lacks).
- `/retire` moves a stale index line to `ARCHIVE.md` without destroying the topic file.

*(A starter `MEMORY.md` skeleton + the directory layout ship under `substrate/memory/`.)*

---

## What each tier needs, at a glance

| Tier | Substrate required |
|---|---|
| **1 — Drop-in** | Nothing. Install and use. |
| **2 — MCP / tracker / CLAUDE.md** | The Chrome DevTools MCP, a tracker the agent can reach, and/or the CLAUDE.md env block (§1–2). |
| **3 — Harness** | The `/done` + `/wait` hook (§3) and/or the memory system (§4). |
| **4 — Project examples** | Not installable — read-only illustrations of composition. |
