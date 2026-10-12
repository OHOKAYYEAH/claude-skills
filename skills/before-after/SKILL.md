---
name: before-after
description: >-
  Show what the current change did: capture the BEFORE and the AFTER (QA
  screenshots, a rendered PDF/report, or a static mock) and hand them to
  /present as one proof sheet. Chained non-blocking at the tail of ship
  composites; fire on "show me", "before and after", "what does it look like
  now". Never gates, never fabricates a frame. NOT /present (delivers any page;
  this gathers the evidence for it), /mockup (pre-build), /qa (behavior).
disable-model-invocation: false
argument-hint: "[optional scope hint] [optional tokens: \"noafterbefore\" skip the baseline · \"publish\" also publish a shareable link]"
---

If you run several sessions in parallel, one ticket each, the fastest possible re-orientation on coming back to any one of them is **seeing** what it changed — not reading a diff, not re-reading a report. `/before-after` is that: it assembles the visual evidence for the current scope and hands back **one page** in a private, never-committed folder for the ticket.

The value is in *capture*. The rendering already exists elsewhere (`/devtools` is sitting on the page, `/mockup` renders static files), and `/present` owns the page and its delivery. This skill's job is to make sure the right pixels get caught, before and after, and handed over.

**Composes:** `/devtools` (live frames), `/mockup` (static render discipline) and `/present` (the page). `/present` not installed → build one small self-contained HTML page yourself with the same content. `/devtools` and `/mockup` not installed → take only the rungs that don't need it (a rendered PDF/report, or the one-line "no visual surface" note), and say which rung was unavailable.

## Hard rule: this skill never blocks

It is chained at the **tail** of pipelines that are explicitly low-touch. So:

- **No gate, no approval pause, no question.** Unlike `/mockup` (which stops and waits for a look-lock), `/before-after` presents and moves on. If the caller was mid-pipeline, control returns immediately.
- **No terminus block.** It emits **one line** (`/present`'s line), never a report block that would stall an orchestrator.
- **Degradation is a line, not a stop.** Can't capture? Can't build the sheet? Say so in one clause and let the pipeline continue. A missing proof sheet never fails a ship.

## The evidence ladder

Take the **first rung that applies** — don't climb past a rung that works, don't fake a rung that doesn't.

1. **Live UI + a running server** → screenshots harvested from the browser pass that just ran. This is the ship-pipeline case (a project's ship or land-and-verify skill, like the `/ship` and `/merge-and-verify` examples): `/devtools` already walked the scenarios with the page rendered and authenticated, so the frames cost one `take_screenshot` each at states already reached. **Never re-drive the browser just to collect frames** — harvest what the pass produced.
2. **UI, but nothing running** (worktree with no server, `/devtools` returned 🛑) → render a static mock the way `/mockup` does (real design tokens, real geometry, realistic data) and shoot that. Borrow `/mockup`'s *rendering* discipline; leave its approval gate behind.
3. **Non-UI but it renders something** — a PDF invoice, a generated report, a print view, an email template, a chart. Render the real output and shoot it; that's genuine evidence, not decoration.
4. **Genuinely nothing visual** (resolver, migration, CI config, pure refactor) → **no sheet, one honest line**: `no visual surface — proof is N tests + super-review`. Do **not** fall back to `/mockup` here: a mock of already-built backend logic answers no question and costs a pipeline its momentum.

## Frames — before/after is the point

The single most useful shape is a **baseline + change pair**, because the eye catches a difference far faster than it reads one screenshot.

- **A pair is the default. Capture the before.** A user who works the product at one remove — through agentic coding, for users who live in it daily — sees the gap in the before frame: what was missing, what was broken, what users were actually complaining about. An after-only sheet asks them to take the gap on faith, and they can't check it. Unlabelled after-only frames read as "screenshots of the current problem," and the sheet gets taken for a proposal rather than a finished build.
- **A caller that names where the before lives uses it.** When the live deployment is exactly the code the change replaces, shooting the same screen there is the true before, and far cheaper than a worktree.
- **A pre-existing baseline is free** — if the session already shot the broken/old state while reproducing a bug, that IS the before frame. Use it before spending anything.
- **Otherwise spend the ten minutes.** For a frontend change, a detached worktree off the integration branch, pointed at the same running backend, renders the true before; shoot the same screens from the same data. **Never** get there by stashing or checking out the base in a shared checkout mid-pipeline — a throwaway worktree avoids that risk.
- **`noafterbefore` token** skips the baseline when the user says the pair isn't worth it, and a genuinely un-capturable before (the surface didn't exist in any runnable form) is a one-line note in the sheet, not a silent omission.
- **Label every frame `BEFORE` or `AFTER` in the frame head, always** — including on an after-only sheet. An unlabelled frame is ambiguous exactly when the reader is least able to resolve it.
- **Number frames in capture order** (`01`, `02`…). The number encodes the order the QA walk reached them, so it means something; don't number decoratively.
- Caption each frame with what it shows and at what viewport. Wide-viewport captures (~1900px) earn their own frame — a layout that holds at 1440 can still strand at wide.

## Hand the frames to /present

This skill gathers the evidence; **`/present` builds the page and delivers it**, from a small JSON manifest written beside the frames (its engine documents the schema). What this skill decides is the content and the delivery tokens. The manifest carries:

- **One section per screen**, its frames in capture order and labelled `BEFORE` / `AFTER`, pairs side by side.
- **Scenarios walked**, each with its verdict (`pass` / `note` / `fail`) and the frames that show it. Service, env, base branch, seed source, PR → a small metadata header. The sheet's absolute path → at the top, so it can be found again.
- **Anything illustrative rather than captured** (a template demo, a scenario list you didn't actually walk) → a visible provenance banner in the page itself. Never let a sheet imply a QA pass that didn't run.

**Delivery:**
- **Default: plain `/present`, local, `noopen`** unless one of the moments below applies. Write frames and manifest into a private, never-committed per-ticket folder in the repo's main checkout (e.g. `docs/local/<ticket>/`, ignored by your *global* git ignore). Not a linked worktree — removing a worktree deletes its ignored files. Not a temp dir either — those get wiped, and these are what you go looking for weeks later when someone asks "what did that look like before?"
- **`publish` token** → `/present publish`, a private shareable page (a Claude Artifact), for when the user wants a link to open elsewhere. Never the default: a local page answers the same question without sending the pixels off-box.

**Opening the sheet is a separate question, and the answer is yes at these moments** (on a headless box, `open` means `/present`'s headless delivery, sending the page as a file):
- **`/before-after` was invoked interactively.** The user asked, so they're looking.
- **A pre-push preview awaiting the user's approval.** The pipeline is stopped on their look, so the page must reach whatever device they're on.
- **A ship composite's terminus** (e.g. the `/ship` example), the end of a build the user is about to read the report of. Their review moment, and they're at the terminal.
- **A land-and-verify leg after a staging deploy** (e.g. the `/merge-and-verify` example). That's the authoritative before/after on prod-like data, and it fires while the user is away, so the page is waiting when they come back.

Path only otherwise — the dev hop is the least interesting of the rungs and the most frequent, and it lands mid-pipeline. Never pop a window from inside a background pipeline; several parallel sessions each opening pages is real noise.

**Never commit the frames.** QA against a DB seeded from staging or prod can carry real customer data: authorization to keep private copies on your machine never extends to a shared repo. Don't write a `.gitignore` into the folder either (that commits your personal tooling into their repo); confirm `git check-ignore -q docs/local/x` passes instead.

## A standing gotcha

**Screenshots from local QA can contain real customer data** (when local is seeded from staging or a prod refresh). The local default keeps them on this machine. With `publish`, they go to the user's own private page only — never a shared link.

## Guardrails

- **Never fabricate a frame.** Capture it or say you didn't. No described-but-unrendered images, no claimed screenshots, no invented scenario verdicts.
- **Never gate, never ask.** No approval pause. That's `/mockup`'s job, and it's why `/mockup` can't be the fallback here.
- **Harvest the AFTER, don't re-drive it.** After frames come from the pass that already ran — re-opening the browser to re-shoot states QA already reached is the slowdown this skill promised not to add. The **before** is the exception: it never exists in that pass, so capturing it is the one thing worth spending on.
- **One line back to the caller.** `/present`'s line, or the one-clause degradation. Nothing report-shaped.
- **The sheet is evidence, not a deliverable.** It records what the change looks like; it isn't the PR, the report, or the QA verdict.
