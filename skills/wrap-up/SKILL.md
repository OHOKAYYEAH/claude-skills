---
name: wrap-up
description: "The terminal closeout driver: take a finished chunk of work to a tidied, codified, safe-to-close state. Chains /done-check (gate) → triage → /compound (codify) → the project's own worktree-teardown skill if it has one (LAST, since it removes the current worktree). Clears reversible loose ends itself; holds only on an item that needs you (outward-facing, destructive, or a judgment call). Fire ONLY on an explicit closeout signal (\"wrap up\", \"run the full closeout\", or \"…then wrap up\" in a prompt). Do NOT self-trigger because work looks finished: the skills it chains commit lessons and delete the current worktree. NOT /done-check (only detects loose ends), NOT /done (it ends by telling you when to type it; it never fires it), NOT /handoff (continue elsewhere)."
disable-model-invocation: false
argument-hint: "(no arg = full closeout, then a short report; you close the window yourself)"
---

Run the full closeout on this session's work: **gate → triage → codify → cleanup → one report.** This skill is deliberately **thin** — single-job skills ("atoms") do the work (`/done-check` decides if it's safe to close, `/compound` codifies the lessons, and a project-provided teardown skill removes the worktree) — and `/wrap-up` is the **gate + the triage between them + the single final report.** Glue, by design.

**Run only on an explicit closeout ask** ("wrap up", "…then wrap up"). If you reached for it only because the work looks finished, stop: `/compound` commits lessons and the teardown deletes the worktree.

This is the terminal-closeout mirror of a forward "ship" driver. Same skeleton — chain shared reusable atoms, and delegate the environment-specific teardown to whatever atom the current project provides.

**Hard contract: this skill always ends with a Wrap-up Report (step 5), or it stops at the gate / holds at triage and says exactly why.** The common failure mode is an inner atom returning its verdict and you writing a turn-ending wrap-up on the spot. Don't. An inner block is **mid-pipeline input** — your next move is the next step, not a yield. This is the only place that warning appears; it applies to every step below.

**Why this lives at user level (and how it reaches a project-local teardown skill).** Its core atoms — `/done-check` and `/compound` — are user-level skills available in every session, so the composite belongs there too; the only project-scoped piece (the teardown step) is **optional**, resolved at runtime. `/wrap-up` does **not** hard-depend on any project skill. Step 4 is a *presence check*: if this session's available skills include a project worktree-teardown skill, it runs it last; if none is present, it skips that step and says so. That's why each project keeps its **own** teardown skill — parallel-worktree setup differs per repo (services, ports, env), so the teardown logic must be project-scoped. `/wrap-up` supplies the closeout *pipeline*; the project supplies the *teardown*.

**If a chained skill isn't installed:** no `/done-check` → run the gate yourself (is the main work actually done; is anything unpushed, unfiled, untold, or still running?) and tag each loose end as below. No `/compound` → skip step 3 and say "no codify step" in the report. No `/triage` → apply the same bar yourself: only a decided follow-up that can't be done now earns a ticket.

## The workflow

### 1. Gate — /done-check

Call the Skill tool with `done-check`, args `nested`, and read its verdict — never pre-check the skill listing for it. A long session's listing arrives in partial blocks, so the latest block isn't the full set; only a not-found error from the Skill tool means it's absent. This is the whole reason the pipeline is gated: you don't tidy up work that isn't safe to close. `/done-check` tags every loose end it surfaces `[P]` (**P**ipeline: a step here can resolve it) or `[M]` (**M**e: needs you — outward-facing, destructive, or a judgment call) — those tags drive step 2, so don't re-derive them.

- **🛑 not yet** → **STOP. Tidy nothing.** The main work isn't done — surface what `/done-check` flagged as incomplete and hand back, ending on `🛑 Don't close — <what's unfinished>`. Cleaning up now would codify a half-finished session and remove a worktree you still need.
- **✅ done**, or **✅ grab-N-first where every item is `[P]`** → proceed straight through. This is the common case and it must stay frictionless: step 3 and step 4 *are* the resolution for those items.
- **✅ grab-N-first with any `[M]` item** → go to step 2, which holds on the live ones and sets the stable ones aside as left open.

If `/done-check` returns items without tags, tag them yourself using its `[P]`/`[M]` definitions.

### 2. Clear `[P]`, hold only on live `[M]`

Invoking `/wrap-up` is the go-ahead for every `[P]` item. Do the ones no later step owns now — commit and push this session's work to its own branch, switch a parked checkout, move out-of-home files, make an earned ticket transition, stop processes this session started — and list each in the report. Memory is step 3's; the worktree is step 4's (no teardown atom → a stale worktree becomes `[M]`).

**Sort each `[M]` item by whether it gets worse while you're away.** When unsure, it's live.

- **Live → hold.** Someone is waiting (an untold requester, a triage ASK naming a person), something runs that this session can't stop (a long-running process it didn't start), or a standing instruction sits with another session.
- **Stable → leave open, don't hold.** It keeps unchanged until you get to it: a never-pushed branch, a file with no obvious home, a promotion push, a judgment call nobody is waiting on. Continue the pipeline; step 5 lists these as the session's open items.

**Any live `[M]` item → STOP HERE and surface it, before codifying and before teardown.** This is the pause the pipeline exists to make: past this point `/compound` commits and the teardown atom deletes the directory you're standing in, so an obligation surfaced *after* those steps has already been stranded. The canonical case is an **unfiled follow-up ticket** — decided in the session, invisible to every board, and gone with the transcript.

Clear the `[P]` items first, so the hold carries only what truly needs you. Emit the live items as a short numbered list, each one line: what it is, why it can't wait, your recommended action. Then hand back ending on the step-5 stop line: **`🛑 Don't close yet — /go and I'll do these, then finish the closeout`** (or "skip, proceed", which leaves them open with the stable ones).

On `/go`: do the clearing actions, then continue into step 3 in the same turn. Never auto-fire the outward-facing ones — an email or Slack message is drafted for you to send, never sent; a follow-up ticket gets filed only with content the session actually decided, never invented. A branch that was never pushed and has no PR is a ship/PR flow, not closeout — surface it and leave it; pushing new commits to a branch already on the remote is a `[P]` clear.

**On what earns a ticket**, `/done-check` has already sent the session's candidates through `/triage`, which owns that bar — don't re-judge them here. Closeout does not mint tickets for every nit the session noticed in flight.

### 3. Codify — /compound

Invoke `/compound nested` — the token tells it a composite owns the terminus, so its verdict line comes back as mid-pipeline input. It mines this session for durable lessons and **self-applies the reversible ones** (memory writes, single-skill edits, project-scoped CLAUDE.md lines — each as its own pushed commit); genuinely high-risk changes it records as proposals in a findings inbox for `/curate`, so they outlive the session. Read its verdict line and continue.

Codify runs **before** cleanup deliberately — the teardown step is the rug-pull and must be last.

### 4. Act — project teardown (LAST — the rug-pull), IF PRESENT AND STILL NEEDED

Check for a project teardown skill — a worktree/temporary-env teardown skill the current project provides. Confirm by calling it through the Skill tool under the name the project gives it (a not-found error = absent; the listing's latest block is partial, so don't judge from it).

**First: is there anything left to tear down?** Teardown increasingly happens *earlier*, on the ship path — a land-leg skill (e.g. the `/merge-and-verify` example) removes the session's worktree the moment a merge lands its branch, because that's the first point it's provably disposable. So by the time closeout runs, the tree is often already gone.

- **Left-open ending** (step 2 set stable `[M]` items aside) → **SKIP.** The leftovers may need the tree (a never-pushed branch lives there), and it's where the work resumes.
- **Already torn down** (the ship leg removed it, or this is a main-checkout session with no worktree) → **SKIP, and say so in one clause** ("worktree already removed by the land leg" / "main checkout — nothing to tear down"). Don't re-invoke the atom to watch it no-op. This is now the *common* case, not the exception.
- **Still present** → invoke it now (no arg = this session's tree). This is the backstop for work that never reached a land leg: an abandoned spike, a branch parked without merging, a session that stopped at PR-opened. It verifies the tree is clean + pushed, then removes it through its own safety helper (never `--force`, never touches HOLD/KEEP trees). If it comes back **HOLD** (uncommitted/unpushed) → it removes nothing and tells you what's unsafe; surface that, don't fix it. Note that leftover build artifacts (`logs/`, regenerated codegen, an installed sub-package) read as uncommitted and will HOLD a tree that is otherwise done — report that plainly rather than clearing files to force a removal.
- **Absent** (project has no teardown atom, or a plain non-worktree session) → **SKIP.** Note it in the report ("no project teardown step"). Do not invent teardown logic; if the project needs it, that logic belongs in a new project-scoped teardown skill, not here.

This runs **last** because removing the current worktree **deletes the directory the shell is sitting in** — everything that needs the tree (`/compound`'s commits, any file reads) must complete first.

### 5. Wrap-up Report (terminus) — you close the window

Never fire `/done` yourself; a green ending leaves the session for you to archive or close. The report is the hand-back: you skim it or skip straight to closing. Keep it short enough to read in five seconds:

```
**Done:** <the session's headline outcome, one line> (<how verified: merged, deployed, read back>)
- <what changed, at system level: 1-4 bullets, one line each>
Closeout: <tree removed / no teardown step> · <N memories, N skill lines> · <[P] items cleared, or "nothing to clear">
Lives elsewhere: <item → where it lives (calendar date, ticket key)>   ← omit if none

🟢 All done — clear to close. /done when you're ready.
```

The last line is the signal: its own paragraph, nothing after it. Pick it by these rules, never a paraphrase of them:

| Line | When |
|---|---|
| `🟢 All done — clear to close. /done when you're ready.` | **The default green.** Everything left lives somewhere durable (calendar, ticket, `FINDINGS.md`, another session) and nothing running needs watching from here. |
| `🟢 All done — clear to archive. /done, but keep the window: <reason>` | Safe to archive, but the window still earns its place: a background watch this session started is still reporting. |
| `🅿️ Left open — <N> open: <one clause each>` | Stable `[M]` items from step 2, or live ones you said "skip, proceed" on. |
| `🛑 Don't close — <why>` | Gate stopped (step 1), hold at step 2, or teardown came back HOLD. |
| `↪ Don't close — /handoff, work continues` | The work continues in another session rather than ending. |

A dated follow-up that's already on the calendar or a ticket, or a proposal `/compound` put in the findings inbox, **does not block the green line**. Say where it lives in the "Lives elsewhere" line, so the green line isn't hedged. Keep the signal lines verbatim, so anything that watches session output can match them.

## Guardrails

- **The gate is absolute.** 🛑 from `/done-check` → stop before codifying or cleaning. You never tidy a session that isn't safe to close.
- **A live `[M]` holds the pipeline; `[P]` never does.** The hold is at step 2 — *before* `/compound` and teardown — because both are one-way enough that a post-hoc mention is too late. A `[P]` item is done and reported, never asked about: committing and pushing a finished session's work is what closeout is for.
- **The teardown step runs LAST — it's the rug-pull.** It deletes the cwd. Any step that reads the tree or commits from it (`/compound`) must finish first. Inverting this order can orphan `/compound`'s commits.
- **The teardown step is optional and resolved at runtime.** Never hard-assume a teardown skill exists — presence-check the session's available skills. Absent → skip and note it. This is what lets `/wrap-up` live at user level and still do the right thing in a project that has a teardown skill and one that doesn't (yet).
- **Never auto-fire the outward / judgment bucket.** Emails and Slack are draft-only and the user sends them; follow-up tickets get surfaced, not invented; a never-pushed branch goes through a ship/PR flow, not closeout. `/wrap-up` auto-runs only reversible actions: the `[P]` clears, `/compound`, and a teardown atom with its own safety rails.
- **You close a finished session yourself.** A green ending stops on its signal line and never fires `/done`: a session with surfaced judgment items still open shouldn't be archived out from under you. A 🟢 line only appears when nothing live is left: a live `[M]` item never gets one unless you said "skip, proceed" on it.
- **Stay thin.** `/wrap-up` adds the gate, the triage, and the one report — nothing else. Detection lives in `/done-check`, codification in `/compound`, teardown in the project atom's helper. If you're tempted to reimplement any of it, it belongs in the atom.
