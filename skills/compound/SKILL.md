---
name: compound
description: >-
  The codify step: mine THIS session for durable lessons (the user's corrections,
  repeated friction, findings that exposed a missing standard) and fold them
  into memory, skills, or CLAUDE.md. Self-applies contained, reversible changes
  as commits; gates high-blast-radius ones behind a /go-able proposal. Run
  manually after a session, or on "what did we learn", "what should we codify",
  "compound this session". NOT /curate, /report, /handoff, or /done-check.
disable-model-invocation: false
argument-hint: "[optional focus, e.g. \"just the testing lessons\"] [token: \"nested\" — a composite owns the terminus] — no args = whole session"
---

You are running the **codify step**: each unit of work should make the next one easier, and that only happens if lessons flow back into the system that does the work. Without a deliberate codify pass, corrections evaporate when the session ends — the user gives the same instruction again in three weeks, and the suite never compounds. Mine the session, classify what's durable, **apply what's safe**, and surface only what genuinely needs the user's call.

## Self-apply by default; gate only the risky few

The suite self-improves without a review ritual. Every codification is its **own commit, pushed immediately** — so `git log` is the changelog and any application is one `git revert` away. That reversibility is what makes broad auto-apply safe: don't hand the user a pile to read and approve, just do the safe work and tell them what you did in one line.

The split is by **risk and blast radius**, not by type of change:

- **Auto-apply (the default — almost everything):** any codification that is (a) **easily reversible** — a single pushed commit — *and* (b) **contained** — it lands in one place and can't silently break anything else. That covers nearly every real lesson:
  - memory writes (isolated — only affect recall),
  - edits to **one existing skill** (sharpened description, an added guardrail line, an expiry tag on a workaround, a fixed stale reference),
  - additive lines to a **project-scoped** `CLAUDE.md` (one repo).

  Apply each, one pushed commit each, and list it. Don't ask.

- **Gate for /go (rare — only genuinely high-risk or high-blast-radius):** propose, don't apply, when the change:
  - **rewrites or destroys** an existing skill wholesale (vs. an additive edit) — a lossless move into an archive dir outside the loaded skills dir is *not* this; see the retire-list guardrail below — or
  - **creates a new skill** (route through `/create-skill` — needs deliberate authoring, not a one-shot edit), or
  - **extracts a rule into a shared standards file** (a new file that two or more skills apply, plus edits to every skill that restates the rule), or
  - touches the **control flow of a heavily-chained orchestrator** (`/work`, `/super-review`, `/done`) where a wrong edit silently breaks every downstream chain, or
  - edits **global `~/.claude/CLAUDE.md`** (reshapes every session, every project — permanent context tax), or
  - is one you're **genuinely not confident is correct**.

  These are the exceptions, not a second pile to clear by default. A typical session auto-applies everything and gates nothing.

**When it's unclear which side a change falls on:** lean **auto-apply** if it's reversible and contained; **gate** only if it's broad *or* you're unsure it's right. A wrong contained edit is one revert away; a wrong broad edit taxes every future session.

## What counts as a lesson (and what doesn't)

**The bar:** a lesson earns a slot only if all of these hold:

- **A fresh session wouldn't land on it by itself.** That leaves three kinds: a *local fact* (true here, absent from training data and from a quick look: a branch flow, the timezone the servers run in, a harness quirk known only from observation), a *contested choice* the user made (write the side and why the other lost), or a *correction* this session actually needed. Good practice the model already follows earns nothing.
- **Having it would have prevented the friction, and the situation recurs.** Both must be yes.
- **It carries its why and its source.** The why is one clause, so a later reader can judge the edge cases the rule didn't foresee; the source is a pointer (a ticket, a PR, a dated decision), never the story. A rule with neither is gut feel; the why and source are what let a later cleanup tell a load-bearing rule from sediment.

It's a **durable rule, never an event log**: "repo X's path alias is `@/`" changes future behavior; "shipped TICKET-123" is tracker/git history and does NOT belong in the always-loaded index. Prefer updating an existing entry over adding a new one. A process lesson that keeps getting missed belongs in the skill or CLAUDE.md where it fires, not in memory.

**Err lean.** Every entry is a permanent tax on every future session until someone retires it, and a stale one actively misleads, while a real lesson re-presents itself. "Let it go" is the most common correct verdict.

Mine the session for:
- **Explicit corrections** — the user redirected the approach, rejected output, or restated a preference. The correction *and its why* are the lesson.
- **The same instruction given twice** — once is a request; twice is a missing default.
- **Findings that exposed a missing standard** — a /super-review, /mutate, or /tdd pass caught something a skill *should* have prevented upstream. The lesson lives in the upstream skill, not the catcher.
- **Hard-won workarounds** — a harness quirk, tool limitation, or environment trap that cost real time to discover.
- **Decisions with reusable rationale** — a /recommend call whose *why* will be needed again (these often want a memory or project doc, not a skill).
- **Skill misfires** — a skill that fired when it shouldn't, didn't fire when it should, or was missing entirely.

Not lessons: one-off trivia, anything the repo / git history / CLAUDE.md / memory already records, **event-logs of completed work** (what shipped / merged / filed — that's the tracker & git history, not load-every-session context), facts that only mattered to this conversation. **"Let it go" is a valid and common verdict** — name it and say why it doesn't clear the bar. A session that produced only event-logs codifies *nothing* — and that's a correct outcome, not a failure.

## Classify each lesson → its destination

- **Skill edit** — name the skill and the concrete change (the line or section, quotable). Most lessons land here, and most are auto-applied (single existing skill, additive). **Prefer sharpening the existing line over appending a new one** — if the skill already says it and it wasn't followed, strengthen or relocate that line instead of restating it; appended duplicates are how skills bloat (the #1 smell /curate hunts).
- **New skill candidate** — only if it clears /create-skill's bar: one job, and (for composites) the rule of three. Gated — propose the name and one-line description; authoring goes through `/create-skill`.
- **CLAUDE.md rule** — for cross-skill defaults. Project-scoped → auto-apply; global `~/.claude/CLAUDE.md` → gate. Quote the proposed line either way.
- **Memory** — for facts about the user, projects, or context (not process — process belongs in skills). Auto-applied. **Read the store's actual shape before writing — it differs per machine:**
  - **Hierarchical store** (lean always-loaded `MEMORY.md` core + on-demand `domain-*.md` files): write the entry into the matching `domain-*.md` (read it first) as a short (~150–180 char) recall hook with the detail in the topic file — NOT into `MEMORY.md`. Only a genuinely cross-cutting rule earns a core slot; a fact needing a new domain gets a topic file + a one-line `MEMORY.md` pointer. Keeping entries out of the core is what stops the 200-line/25KB ceiling creeping back; `/tend-memory` + `/retire` are the cure if it does.
  - **Flat harness-native store** (one frontmattered topic file per fact + one-line `MEMORY.md` pointers, no `domain-*.md`): follow the harness's native memory format — write/update the topic file, add its one-line pointer, update-don't-duplicate. Skip the domain routing; the platform owns that store's hygiene.
- **Test or check** — when the lesson is "we keep breaking X", the durable fix is a test, a hook, or an eval, not prose.

**Tag every codification** (applied or proposed) as one of:
- **[standards]** — encodes judgment (what good looks like, definition of done, what to verify). Appreciates as models improve.
- **[workaround]** — compensates for a model/harness limitation. Legitimate, but depreciates — include the expiry condition ("delete when X is fixed/changed") so future curation can retire it.

## Output format

**Glance-first, verdict last.** The deliverable is a single bold verdict line at the very bottom — the thing your eye lands on when you stop scrolling, and a **TLDR of what actually happened**, not boilerplate. Everything above it is skippable context for when you're curious. You context-switch constantly; the job here is "what got better, and is there one thing that needs me?", not a report.

Emit top-to-bottom, dropping any section that's empty:

```
## Compound — <session scope, one line>

**Applied** (each its own pushed commit):
- <lesson, one line> → <file> — <sha>

**Needs your call** (high-risk / broad — ranked by leverage):
1. <what the change IS, one line> → <destination> — <why it's gated (broad / unsure)>
2. …

Let go: <N>.   ← one line, count only; omit if 0

**<verdict line>**
```

**Under `nested`** (a composite like `/wrap-up` is driving and owns the final report): produce the same verdict line, but hand it back as mid-pipeline input rather than ending the turn — the caller has a next step and the verdict is not it.

Nested runs usually end with the session closing, so a gated item can't wait for a `/go` here. Append each one to a suite inbox file (e.g. `~/.claude/FINDINGS.md`) as a `## Proposal: <the change>` heading with the exact change, its destination, why it's gated, and `Found: <date>, /compound in "<session title>"` — enough to apply it cold. `/curate` drains those headings. The verdict then reads **Applied \<N\> (\<gist\>); \<M\> gated → FINDINGS.md (\<top one\>).**

### The verdict line — name WHAT, never boilerplate

The final line is bold, standalone, and a **one-line TLDR of the codify state** — it must name the actual substance. **Never** emit a generic "improvement recommended" / "Recommend improvement, respond /go" placeholder: that tells the user nothing about what's being suggested, which was the whole complaint. Pick the matching shape and fill in the real content:

- **Something gated** → name it + key off `/go`:
  **Applied \<N\> (\<one-line gist\>); 1 needs your call — \<what the gated change is\>. /go to apply it, or ask to see it.**
  e.g. *Applied 2 (register-TZ note → memory, /tdd red-first guardrail); 1 needs your call — rewrite /work's harden phase to run mutate isolated. /go to apply it, or ask to see it.*
- **Everything applied, nothing gated** → name what got better:
  **Applied \<N\>: \<one-line gist of what\>. Nothing pending.**
- **Nothing at all** → **Nothing worth codifying. All clean.**

If more than one item is gated, the verdict names the top-ranked one and says "+N more — /go for all, or by number."

**Three deliberate tiers of detail:** the verdict line is the *glance* (what changed / is there a /go); the numbered "Needs your call" one-liners are the *fuller context* you read only if curious; the *deep* per-item detail (the exact quotable change, [standards|workaround] tag + expiry, effort S/M/L) is **derived but held back** — surface it only when the user asks to see an item, or when `/go` fires and you apply it. `/go` acts on the gated list top-down (or cherry-pick by number).

## Guardrails

- **Risk discipline, not type discipline.** Auto-apply is gated on *reversible + contained*, not on whether it's "a skill edit" vs "a CLAUDE.md edit". A contained, reversible change auto-applies even if it's a CLAUDE.md line; a broad or low-confidence change gates even if it's "just" a skill edit. The genuinely high-risk set (new skills, orchestrator control flow, global CLAUDE.md, wholesale rewrites/deletions) always gates.
- **No silent broad changes.** Everything auto-applied is its own pushed commit so the ledger + `git log` keep the receipt and revert is one command. If you can't cleanly revert it, it doesn't qualify for auto-apply.
- **Verdict last, always — and it names what.** Every run ends with exactly one bold verdict line, content-bearing, nothing after it. Never the old boilerplate. A clean session collapses to scope + verdict.
- **Hold the deep detail.** Tags, expiry, effort, and the exact quotable change are worked out internally but kept off the glance. `/go` (or "show me #1") is when they surface.
- **Don't manufacture lessons.** A clean session gets a short ledger. Mirror the no-manufactured-nits rule — three real lessons beat ten padded ones.
- **The bar above is the filter; when in doubt, let it go.** An unneeded rule is permanent context tax and a stale one is worse than absent, while a real lesson re-presents itself. (Distinct from the apply/gate call above, which is about *how* to land a lesson you've already decided to keep.)
- **Respect declined proposals.** If the user previously rejected a codification, don't re-raise it from new evidence of the same flavor — and don't auto-apply a variant of it either.
- **Work the audit's retire list — archiving auto-applies.** The add path here is automatic; if the delete path stays manual, the suite only grows and flagged skills sit unmoved across audits. When the latest `~/.claude/audits/harness-audit-*.md` names retire candidates still under `skills/`, retire them in this run: `git mv skills/<x> <archive-dir>/<x>` verbatim, repoint every cross-reference (`grep -rn '/<x>\b' skills/`), one pushed commit. Lossless (restore = `git mv` back), so it clears the auto-apply bar. Gate only what the audit marked borderline. The audit's evidence is the trigger — never retire on a usage hunch.
- **Suite-rot routes to /curate, not an inline patch.** If a lesson reveals *structural* rot rather than a missing standard — a skill has sprawled into several jobs, duplicated another, gone to sediment (unused/stale), or become a no-op (fires but adds nothing) — the fix is a `/curate` pass, not a one-line patch here. Don't repair structural rot one session-lesson at a time; name the anti-pattern and route it. (`/curate` owns the named anti-patterns and the refactor backlog; `/harness-audit` confirms sediment/no-op from usage.)
- **This session only.** /compound mines the current session, not history — run it after a working session, not as an archaeology tool.
- **Lean and fast is part of the contract.** /compound is a codify pass, not an audit — it reads the session it already has, writes a handful of commits, and gets out. If a step is fanning out across files or the whole memory store to decide something, that step belongs in `/curate`, `/tend-memory`, or `/harness-audit`, and you should route it there instead of running it inline.
- **Close with a memory-health pass — act, don't just nudge.** Two halves. **Truth (every store shape) — BOUNDED, this is not a store-wide sweep.** Check only the memories this session actually *leaned on* (used to make a decision, or wrote/updated) **and** that name a concrete artifact — a file, flag, path, script, command. Cap at 5; if more qualify, take the 5 most load-bearing and say so. Verify the named artifact still exists and nothing this session learned contradicts it. Stale → update or archive it as an Applied item; unsure → flag it under Needs your call; never delete on vibes. Auditing memories the session merely had in context, or the store at large, is `/tend-memory`'s job — doing it here is what turns a two-minute codify into a ten-minute one. **Size (hierarchical stores only — a flat harness-native store has no manual budget to police):** check the lean core on BOTH dimensions — `wc -l <MEMORY.md>` vs 200 lines AND `wc -c <MEMORY.md>` vs ~24.4KB (platform limit is 200 lines OR 25KB, whichever bites first). If over, don't reimplement GC here — `/retire` (eviction) and `/tend-memory` (lossless compression) own that logic; chain them as an auto-applied sub-step (both are lossless + reversible, so they clear the auto-apply bar). Spawn a **fresh subagent** (not a fork — the GC procedure needs none of the session context): *"run the `retire` skill's procedure with `apply` against `<MEMORY.md path>`; if still over budget, run the `tend-memory` skill's the same way; return a one-line summary + any BORDERLINE entries."* Report it under **Applied** (e.g. `ran /retire+/tend-memory: archived N, tightened M, 24.6→22.1KB`). **Borderline retirements still gate** under 'Needs your call' — never auto-evict an entry that isn't wholly stale. This is the only side effect /compound triggers beyond its own commits. (A healthy index often has no dead weight, so the retire→tend-memory fallthrough is the common path.)
