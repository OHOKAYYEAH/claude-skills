---
name: curate
description: "Audit your skills repertoire for health, overlap, token economics, and composite opportunities. Single-responsibility is the bar — each skill should do one thing well and chain cleanly. Read-only: produces a report + a ranked refactor backlog; it never edits skills itself. Runs in an isolated fork so the sweep's heavy reads stay out of the caller's context. Pass skill name(s) to deep-check just those; no args = whole-repertoire sweep."
disable-model-invocation: false
argument-hint: "[optional skill name(s) to focus on, e.g. \"super-review work\"]"
context: fork
agent: general-purpose
---

# Curate — skills repertoire health check

Audit the skill repertoire and report on its health, overlap, and composite potential. The goal you're optimizing for: a **tight, high-signal/low-noise** set of **single-responsibility** skills that you chain together (or composes into deliberate composite skills) rather than a sprawl of overlapping ones.

**You are read-only.** Diagnose and recommend; do not edit, create, or delete any skill. The output is a report ending in a ranked refactor backlog you act on at your discretion. You run in an isolated fork — a whole-repertoire sweep reads every SKILL.md, and the fork keeps those reads (and this body) out of the caller's context; only the report returns. For a whole-repertoire sweep, fan the per-skill reads out to a few parallel cluster subagents and synthesize — faster, and no single context carries all 40 files.

## Where skills live

- **Canonical:** `~/.claude/skills/<name>/SKILL.md` — your user-level skills dir (or wherever your config dir points). This is the set to audit.
- **Project-level:** `.claude/skills/<name>/SKILL.md` in the current repo — checked-in, team-facing. Note these but treat them as a separate tier; a project skill that intentionally duplicates a shared one (e.g. a team-facing copy) is a known, accepted pattern, not a defect — flag the drift risk, not the existence.
- **Legacy `commands/` tier:** `<config dir>/commands/*.md` (e.g. `~/.claude/commands/`) — old-format slash commands, no frontmatter. Sweep for strays: they dodge frontmatter rules and this audit unless you look. Default call: migrate to `skills/<name>/SKILL.md` or retire.
- Read each skill's frontmatter (`name`, `description`, `disable-model-invocation`, `context`, `agent`, `argument-hint`) and body.

## Two modes

**Focused** (`$ARGUMENTS` names one or more skills) → deep per-skill health check on just those. Use this for "tighten up super-review" type asks.

**The arguments, if any: `$ARGUMENTS`. Branch on them before you do anything else.** Non-empty → focused mode on exactly the named skills; do not sweep the suite. Empty → full sweep. This sentence is the instruction, not a description of one: a mention of `$ARGUMENTS` that only reads as descriptive prose gets read past, and a focused ask turns into a full sweep.

**Repertoire-wide** (no args) → scan every shared skill, then run the overlap, composite, and chaining-health analyses across the whole set.

**Both modes read the suite inbox:** the `## Proposal:` headings in your suite's `FINDINGS.md` (e.g. `~/.claude/FINDINGS.md`), which `/compound` leaves when a closeout gates a change. Rank each one in the backlog like any other item (focused mode: only the proposals naming the skills in scope), marked `(inbox)`. Applying one on `/go` deletes its heading in the same commit; deciding against one deletes it too, with the why in the commit message.

## Per-skill health check

Audit against the same bar `/create-skill` drafts to (its step 3 standards; the checklist below covers them). A style finding on a freshly created skill also means that bar is missing a rule: say which rule to add.

For each skill in scope, evaluate:

1. **Single responsibility.** Does it do *one* thing, or has it accreted multiple jobs? A skill that "reviews AND fixes AND reports" is three skills wearing a trench coat — flag the seam. (Composites that *orchestrate* other single-purpose skills are fine — that's the intended chaining pattern, not accretion.)
2. **Description quality.** Is the trigger crisp enough for the model to fire it at the right moment? The best descriptions also say *when NOT to* use it and point at the sibling skill that covers that case (the way `/report` and `/recommend` cross-reference). Flag vague or overlapping triggers.
3. **Frontmatter and listing.** `name` matches the folder; values are YAML-safe (quote anything containing `: ` or starting with `[`, `{`, `*`, `&`, `!`, `|`, `>`); `context: fork` + `agent` where it should run isolated; `argument-hint` if it takes args. Then the listing call: `disable-model-invocation: true` only if the model must be unable to run it even on request; otherwise `false`, and **listed** only if it meets a short-list criterion (the model should fire it from the situation, unasked, or the user triggers it in natural language) — else it should be name-only (a `"<name>": "name-only"` entry in `skillOverrides`). A name-only skill with an "only on explicit ask" safeguard in its description has lost that safeguard: it belongs in the body's first lines.
4. **Right-sizing & bloat.** Is the body high-signal, or padded with repetition, restated rules, and defensive scaffolding? Repeated hammering of the same instruction is the #1 bloat smell. (Note: anti-halt scaffolding — "Hard trigger / most common failure mode / nothing else" pressure to stop the model ending its turn after an inner step — is often a band-aid for a chaining problem better solved structurally; see Chaining health.)
5. **Chain-safety as a sub-step.** If this skill is ever invoked *by another skill*, does it end with a terminal instruction or a satisfying block that tempts the model to end the turn? If so, it's a halt risk when chained — note it.
5b. **Autonomy (orchestrators).** Flag any pause that isn't a genuine halt point (an irreversible action, or a judgment only the user can make) — a question it could decide, a chained step that ends on a `/go` prompt, a "confirm before continuing" on a reversible action.
6. **Scaffolding type.** Is the body encoding *standards* (judgment: what good looks like, definition of done, what to verify — this **appreciates** as models improve) or a *capability workaround* (compensating for a model/harness limitation — this **depreciates**)? Workarounds are legitimate but must carry their expiry condition ("delete when X changes"); flag any workaround that doesn't, and flag standards skills carrying workaround scaffolding that newer models/harnesses have made retirable.
7. **Token economics.** ("dmi" below = `disable-model-invocation`.) A listed skill's description is injected into *every session* (tokens ≈ words × 1.3); a name-only or dmi:true one costs its name at most. Bodies load per invocation — and an orchestrator chain loads every inline inner body at once, so body bloat compounds exactly where context is busiest. Flag: listed descriptions over ~70 words or near the 1,536-character listing truncation; listed skills that miss the short-list criteria (→ make them name-only — **never** flip to dmi:true to save listing space, that takes away mid-prompt use); heavy read/report skills that would benefit from `context: fork` (isolation returns just the report, keeping the reads and body out of the caller's context).

## Repertoire-wide analyses

**Overlap matrix.** Cluster skills by function (e.g. "summarize/compress recent output", "pre-ship verification", "browser QA", "decision support", "status/reporting"). Within each cluster, flag pairs with *meaningful functional overlap* as candidates to merge or to give sharper boundaries. **Do not manufacture overlap:** skills that share a theme but have genuinely distinct outputs or trigger conditions are correctly separate — confirm them as deliberately-disjoint rather than nagging. (You may have explicitly confirmed some near-neighbors are all valuable and distinct; respect a stated "these are different" and don't re-raise it.)

**Composite opportunities.** Identify single-purpose skills that are *frequently chained by hand* and would merit a named composite — and propose creative new combinations of existing atoms. State each as: `proposed /name = /a → /b → /c`, what it's for, and why a standing composite beats ad-hoc chaining. (Model to imitate: `/work` = plan → review-plan → recommend → execute → super-review → report.)

**Chaining health.** Flag any orchestrator skill that leans on prompt-pressure ("you MUST continue", "do not end your turn", "the recap absorbs it") to survive a chain. These are usually fighting one of two things: (a) an inner step with a hard terminal instruction (e.g. the native `/security-review`'s "final reply must be the report and nothing else"), or (b) an inner step that emits a satisfying block (verdict/recap/recommendation) the model reads as a stopping point. The structural fix is to run that inner step in an **isolated context** (`context: fork` + `agent` + `background: false`, or a thin forked wrapper) so its output returns as a *result* and the orchestrator keeps control — then the prompt-pressure scaffolding can be deleted as dead weight. Recommend this where it applies; quantify the bloat it would remove.

**Structural issues.** Name conflicts / duplicates across tiers (and which wins by precedence — **personal > project, and SILENTLY**: a same-named skill in `~/.claude/skills/` shadows a repo's `.claude/skills/` copy with no warning. Full order: enterprise > personal > project — the OPPOSITE of MCP precedence), folder/name mismatches, dead skills, stale references to renamed skills or removed tools, and **hook-shadowed skills** — a UserPromptSubmit hook that intercepts a slash command before it reaches the LLM (the /done pattern) must agree with the SKILL.md it shadows; flag drift between hook behavior and skill body.

**Context budget and the short list.** Everything listed shares one budget: your user-level skills plus the current repo's `.claude/skills/`. One pass (dmi is read from the frontmatter only — a body that *mentions* `disable-model-invocation: true` must not count):

```bash
sono=$(jq -r '.skillOverrides // {} | to_entries[] | select(.value=="name-only") | .key' ~/.claude/settings.json)
fm() { awk '/^---$/{c++;next} c==1'; }  # reads stdin: a positional arg here gets replaced at skill load
for f in ~/.claude/skills/*/SKILL.md .claude/skills/*/SKILL.md; do
  [ -f "$f" ] || continue; n=$(basename "$(dirname "$f")")
  d=$(fm < "$f" | awk '/^description:/{f=1} f&&/^[a-z-]+:/&&!/^description:/{f=0} f' | sed 's/^description: *//')
  if fm < "$f" | grep -q '^disable-model-invocation: *true'; then t=dmi-true
  elif grep -qx "$n" <<<"$sono"; then t=NAME-ONLY
  else t=LISTED; fi
  printf "%-18s %-9s desc:%3dw %4dc\n" "$n" "$t" "$(wc -w <<<"$d")" "$(tr -d '\n' <<<"$d" | wc -c)"
done | sort -k2,2 -k3.6rn
```

Report the LISTED count and word total (≈ tokens), the top five offenders, anything over 1,536 characters (already truncated), and a **proposed short list**: each LISTED skill with keep (which short-list criterion it meets) or name-only. No headcount target: flag the total when descriptions start dropping (overflow below) or it grows a lot between audits. The keep/name-only split is the user's call — propose it, don't assume it.

**A description missing from a session's listing, with no name-only entry, is listing overflow** — the harness drops descriptions when the listing's budget runs out, least-used first, so a brand-new skill goes first. Report it as a budget finding; don't attribute it to YAML without a parse error that actually explains it.

## Named anti-patterns (a fast checklist)

The analyses above map onto named rot modes — a compact vocabulary for skill-suite rot. They don't add new work — naming them makes each easier to spot in a sweep and to report crisply. Sweep each skill (and the suite) for:

- **Sprawl** — one skill doing several jobs (the trench-coat; → Single responsibility). Split into atoms.
- **Duplication** — two skills with real functional overlap (→ Overlap matrix). Merge or sharpen the boundary.
- **Sediment** — a skill that accreted but no longer earns its slot: dead skills, stale references to renamed skills/removed tools, a `[workaround]` whose expiry has passed. Retire it losslessly (archive it, so restoring is a move back), and only on evidence — an audit, a contradiction, a missing artifact — never a usage hunch.
- **Unsourced rule** — a rule in a skill or standards file with no why (one clause, so edge cases can be judged) or no source (a ticket, PR, or dated decision). If it also restates practice the model already follows, propose removal; otherwise propose a source. A sourced rule stays: re-testing it against a newer model is not this check's job.
- **No-op** — a skill that fires but does nothing load-bearing: output routinely ignored, or a capability-workaround a newer model has made inert. Prove it still bites, or cut it.
- **Premature completion** — a skill that declares done before the job's finished, or ends on a terminal block that halts a chain it's part of (→ Chaining health). Fix the stop structurally, not with prompt-pressure.
- **Expired rationale** — a guardrail whose *stated reason* has stopped being true. Distinct from sediment's lapsed `[workaround]` tag: nothing is tagged, the rule simply names a mechanism ("don't X, because Y pops a window") that no longer describes the code path it governs, so it keeps suppressing correct behavior. The tell is a **same-file contradiction** — a guardrail forbidding something that another section of that skill records as already fixed. When a rule justifies itself by naming a mechanism, check the mechanism before honoring the rule.

Structural evidence (from the files) is what you have here; **usage evidence** that confirms sediment/no-op — invocation counts, "fires but always overridden" — is `/harness-audit`'s job. When a call hinges on "is this actually used?", say so and defer to that.

## Output format

```
## Curate Report — <scope: "whole repertoire (N skills)" or "skills: a, b">

### Per-skill verdicts
- **/<name>** — <🟢 healthy / 🟡 tighten / 🔴 problem>: <one line — the single most useful observation>
  <optional 1–2 follow-up lines only if there's something concrete to fix>

### Overlap
- <cluster>: <pairs flagged, or "deliberately disjoint — leave as-is">

### Composite opportunities
- `proposed /<name> = /a → /b` — <what it's for; why standing > ad-hoc>

### Chaining health
- <orchestrators relying on prompt-pressure + the structural fix, or "none">

### Structural issues
- <duplicates / precedence / stale refs, or "none">

### Context budget
- Listed: <N> skills, ~<W> words ≈ ~<M> tokens, every session. Top offenders: <name (Nw)>, … · over 1,536 chars: <names | none>
- Proposed short list (sweep only): keep <name (criterion)>, … · name-only <names>
- Projected savings if the backlog lands: ~<tokens>/session always-loaded + ~<words> per chain invocation.

### Refactor backlog (ranked)
1. <highest-leverage concrete change> — <effort: S/M/L>
2. ...

_End with: `/go` to work the backlog top-down (`/go 2` for a single item), or `/matrix <item>` to price one properly before it earns a slot._
```

## Guardrails

- **Read-only.** Never edit/create/delete a skill from within `/curate`. Hand back the backlog; you decide what to apply. A `/go` on it is one authorization for every item it names: work them to the end, deciding details as `Decision:` lines and committing each item, and stop only at genuine halt points (an irreversible action, a judgment only you can make) — never a second round of "say /go if you want X".
- **Single-responsibility is the bar, not an ideal to over-apply.** Don't recommend splitting a skill that's genuinely one job just because it's long. Length ≠ bloat; *repetition* is bloat.
- **Don't manufacture findings.** A clean repertoire gets a short report. If a skill is healthy, say 🟢 and move on — mirror the "no manufactured nits" rule for code review.
- **Respect confirmed-distinct sets.** If you've said two near-neighbor skills are each valuable, treat them as disjoint and don't re-litigate.
- **Be specific.** Cite skills by name, quote the offending line, name the concrete edit. "Could be tightened" with no specifics is noise.
- **Trims must not blunt triggers.** Descriptions are the routing mechanism — keep trigger phrases and NOT-refs, cut elaboration. A description that misroutes costs more than the tokens it saves.
