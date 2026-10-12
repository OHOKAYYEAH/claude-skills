# Harness-audit — report template

Write to `${CLAUDE_CONFIG_DIR:-~/.claude}/audits/harness-audit-<YYYY-MM>.md`. Glance-first: the verdict and the action list are what you read; the tables are for when you're curious. Drop any empty section.

```markdown
# Harness Audit — <YYYY-MM> (last <N> days, <scope>)

**<Verdict line — the glance.>** e.g. "Spine is earning its keep: /mutate (5) and /code-review (4) repeatedly caught real bugs; /work is load-bearing. Sediment to clear: skill-a, skill-b (0 use). One gate underperforming: /tdd (2) — red-first is being skipped inside /work."

_Window: <since> → <now> · <sessions> sessions · <files> transcripts · scope: <dirs>_

## Action list (ranked)
1. <highest-leverage change> → `/curate <skill>` | `/compound` — <why, one line>
2. …
_`/go` to work this top-down, or by number._

## Proven-value ratings
| skill | value | invocations (typed·chain) | work | sessions | last used | note |
|-------|:---:|---|---:|---:|---|------|
| /mutate | 5 | 13 (0·13) | 1048 | 13 | 2026-07-16 | killed real mutants → added tests (S123, S456) |
| … | | | | | | |
_Sorted by value, then leverage. "Insufficient signal" where evidence was too thin._

## Staleness
- **Dead (0 use in window):** <skill — genuine sediment, retire candidate>, …
- **Blind-spot (under-reported, NOT dead):** <done (hook-backed)>, <security-review (behind /sec-review)>, …
- **High-freq / low-value (ceremony tax):** <skill (freq → value)>, …

## Composite decomposition
### /work (<N> runs)
- leg `/mutate` — <contribution + evidence>
- leg `/tdd` — <red-first real? evidence>
- leg `/super-review` — <real findings vs nits>
- **verdict:** <is the spine improving the work, or ceremony?>
### <other composite> (<N> runs)
- …

## Framework health
_Only when Stage 4 ran (`--health` / `--health-only`); otherwise drop this section. Workflow-level, defined over artifacts (`references/framework-health.md`). Window <since> → <until>, UTC months; <partial month> is partial._

**Realignment** (signal 3), sampled pairs per month (total pairs in brackets):
| month | n | accepted | corrected AI | changed ask | rubber-stamp | other | interrupted |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08 | 60 (412) | 61% | 14% | 6% | 9% | 10% | 3 |
_n and the bracketed total come from `by_month[m].n` / `.total`; mark `partial` months. "insufficient signal" in place of percentages where n < 5. Labeller spot-check: <k>/10 agreed._

**Decisions held** (signal 1, raw counts pooled over the window; per month in brackets; never a rate):
- Spec fidelity: <a>/<n> first-pass checks ✅ built to spec; <g> gaps, <d> divergences; <r> reruns; <c> couldn't verify. [2026-09: <a>/<n> · 2026-10: <a>/<n>]
- Autonomous decisions: <h>/<n> `Decision:` lines held through the next human turn. [2026-09: <h>/<n> · …]
- Re-freezes after build: <x> (before build: <y>).

**Reading:** <one or two sentences: what moved, what the numbers can't yet say, and any artifact that is rarely produced>. Cite by session prefix / ticket key only (e.g. `corrected_ai` · 2026-08 · `3f9a1c2e`).

## Notes
- <trend vs last month's audit if one exists>
- <any extraction caveats: unknown_command_names, scopes skipped, etc.>
```

## Rendering rules
- **Verdict names substance** — top-performers, worst sediment, the one gate that isn't earning its keep. Never "audit complete."
- **Every rating in the table traces to a citation** in the eval output; if it doesn't, it's "insufficient signal", not a number.
- **Diff-friendly:** stable skill ordering and column layout so month-over-month `git diff` is legible.
- Keep it tight. A healthy harness is a short report; don't pad the tables with skills that have nothing to say beyond their number.
