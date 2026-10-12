---
name: mockup
description: "Preview a not-yet-built UI change as a throwaway static mock BEFORE committing to the real implementation — build a self-contained HTML/CSS/SVG file that reuses the project's real design tokens + any pure geometry/format logic, with realistic mock data, render it headless in Chromium, screenshot it into one HTML proof sheet, and gate on approval. The cheap visual-iteration loop: see how it'll look, lock it, then build for real. Fire on \"show me how it'd look first\", \"mock this up\", \"screenshot a POC before we build/deploy\", \"iterate on the look before writing real code\". Hands the approved look to the real build (e.g. /work). NOT /before-after (captures an already-BUILT change, no gate); NOT /qa (behavioral). Project-agnostic."
disable-model-invocation: false
argument-hint: "[optional: the UI surface / change to mock up]"
---

You want to **see a UI change before it's built** — a disposable static mock you can eyeball and approve, so taste gets locked while it's still cheap to change, not after a real component + tests + review already exist. The whole value is iterating on *look* before paying for *implementation*.

This is the visual counterpart to `/interview`: that locks *intent* in words, this locks *look* in pixels. Both gate before the real build.

## When this fires (and when it doesn't)

- **Fires** when the artifact in question is *visual* and *not yet built* (or being redesigned): a new column, panel, card, chart, layout, component, empty/loading/error state. The point is a picture before the build.
- **Not** `/before-after` — that captures a change that's already **built**, and never gates. `/mockup` is for what doesn't exist yet; its only live capture is the current screen as a BEFORE (step 3).
- **Not** `/qa` — that's behavioral verification, not a look-preview.
- **Skip it** for non-visual work, or a change so trivial the picture adds nothing. Don't mock up a one-word copy edit.

## The move

### 1. Pin the visual intent
What surface, what change, and **which states** must the picture show — the default *and* the hero interaction (a hover popover, an expanded row, an error banner). A screenshot can't hover or click, so any interaction-revealed state must be rendered **frozen in its visible form**. If the surface or the must-show states are ambiguous, ask ONE sharp question (or chain `/interview`); don't mock the wrong thing.

### 2. Ground it in the REAL design system — representative, not generic
A mock in default browser styling teaches nothing about how it'll actually look. Before writing markup, **discover the project's design tokens and reuse them verbatim**:
- Theme tokens / palette (CSS `@theme` / `:root` vars, Tailwind config, `globals.css`), fonts, border/radius/spacing conventions.
- **Reuse pure logic verbatim** — if the real thing renders from a geometry/format function (sparkline points, a number formatter, a date axis), port that exact function into the mock rather than eyeballing the shape. The mock should be wrong only in being disposable, never in being unrepresentative.
- Mirror a sibling component's structure (a real table row, a real card) so density and chrome match.

### 3. Build ONE self-contained static file
Write a single HTML file (inline CSS + JS + SVG) to the **scratchpad** — no dev server, no framework build, no bundler, nothing that touches the repo or prod. Use **realistic mock data** (plausible tickers/prices/dates/copy — never lorem ipsum or `foo`), and a seeded RNG if you generate any, so re-renders are stable. Render every state that matters in one composition where practical (e.g. the table with the new cell + the hover popover shown open beside it).

**When the decision is a CHOICE between options — placement, layout, which-affordance — render ALL of them on one scrollable comparison page, not one per round.** Label each (`S1`/`S2`/`M1`…), give each a one-line tradeoff caption, and include the ones you intend to argue *against*, rendered honestly rather than strawmanned. This collapses an N-round iteration into one look, and it is the only way the weakest option can lose on its own merits in front of the user. It also corrects *you*: seeing options side by side can reverse a written recommendation (e.g. a stacked-bar option dies the moment a per-row column sits beside it, because the two render the same numbers twice). **Render before you finalize a recommendation, not after.**

**Redesigning a screen that exists? Shoot the live current screen as the BEFORE.** The mock alone asks the user to picture the gap; the pair shows it. A true before comes from a baseline already shot this session, the live deployment, or a worktree off the integration branch (`/before-after` § *Frames* covers this in depth, if installed). Label frames `BEFORE (live)` / `AFTER (mock)`, since the sheet mixes a real capture with a mock. A brand-new surface has no before; say so in one line.

### 4. Render headless + screenshot
Drive the **Chrome DevTools MCP** (see `/devtools`): attach to `${CHROME_DEBUG_PORT:-9222}` (if nothing's there, follow `/devtools`' launch ladder, or launch `chromium --remote-debugging-port=9222` yourself), open the `file://` path, size the page sensibly, and screenshot to a file. **Then Read the screenshot yourself first** — catch label collisions, clipping, contrast, off-palette colors — and fix the file before showing the user. Don't ship a sloppy first render.

### 5. Send + gate
Hand the screenshot(s) to **`/present`** as one proof sheet in the scratchpad — one section per state or option, each caption stating the specific design calls you baked in (so feedback is targeted) — and let it open the page (no `/present` installed → build one small self-contained HTML page yourself and hand back its path). Then **stop and gate**: approve, or tell me what to change. Iterate cheaply (edit the file, re-screenshot, rebuild the sheet) until the look is locked. This is a real user-decision pause, like `/interview`'s confirm gate.

### 6. On approval — lock + hand off
State the locked look as a tight **design spec** (the few decisions that matter: window/scope, marks, colors, states, what was deferred). The mock's job is done — it is **not** the real component. Hand the spec to the real build (`/work`, or just proceed), which implements it properly (real framework component, tests, review). Copy the approved frames and sheet to a git-ignored local dir in the main checkout (e.g. `docs/local/<ticket>/`) so a later ship step can set the built screen beside the locked look; the scratchpad is wiped on reboot. Never commit them.

## Guardrails
- **Disposable, always.** The static file never ships, never becomes the production component, never gets committed to the repo. It informs the real build and is thrown away. Conflating the mock with the deliverable is the failure mode.
- **Representative or worthless.** Real tokens, real fonts, real geometry, realistic data. A generic-looking mock answers the wrong question.
- **Cheap by construction.** Static file + headless screenshot. No dev server, no prod deploy, no waiting on a build pipeline. If it's getting expensive, you've over-built the mock.
- **Honest rendering.** Screenshot the *actual* render and look at it before sending. Never describe an imagined image or claim a look you didn't capture.
- **One look-lock, then build.** Don't drip endless variations unprompted — converge on a look, lock it, hand off. (More than ~3 iteration rounds usually means the intent wasn't pinned in step 1 — go back and `/interview`.)
- **Not a fork skill.** Like `/interview`, this needs to talk to the user (the approval gate), so it never runs `context: fork`.
- **Graceful degradation.** No Chrome MCP / no Chromium available? Still write the static file and hand the user the `file://` path to open themselves, and say the auto-screenshot leg was unavailable — don't silently skip the artifact.
