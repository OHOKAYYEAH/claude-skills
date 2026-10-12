---
name: report
description: Emit a status report as a one-line verdict + an icon-keyed status table (✅ done / ⏳ in progress / ⬜ up next), closing with a Next section in /steps shape — a numbered, copy-pasteable checklist, never a prose paragraph. No file changes. Chain with /recommend for opinionated picks, or /notes to drop a verbatim scratchpad.
disable-model-invocation: false
---

Quick status check-in so the user can re-orient fast — whether they're stepping away, context-switching back in, or just taking stock mid-flow.

Answers "where are we now?" at a glance. The table is the report; prose is the frame around it.

## Output shape

Four parts, in this order. No preamble, no signoff, no meta.

**1. Heading** — `### Where <THING> stands`, where THING is the ticket key, branch, or task actually in flight (`### Where PROJ-123 stands`). Skip the heading if the session has no single subject.

**2. Verdict** — one bold sentence, the bottom line. Where things net out and what stands between here and done. This is the line the user reads if they read nothing else.

> **Everything's built and green; one background re-review is the only thing between here and the PR.**

**3. Status table** — two columns, **no column headers** (leave both header cells empty — the labels are self-evident and a header band is wasted rows). Left cell = icon + dimension label. Right cell = the concrete state.

```markdown
|  |  |
|---|---|
| ✅ **Code** | 6 files, in a worktree. Both `/super-review` blockers fixed — the CSV export's quoting of embedded commas and the AA contrast (now 5.13–5.60:1, measured live) |
| ✅ **Tests** | 81 files green. New: an export suite + an explicit embedded-comma/newline round-trip test |
| ⏳ **Re-vet** | running — confirming both fixes and that removing the now-pointless escaping helper didn't un-cover anything |
| ⬜ **Left** | local QA (`/qa run`) + open the PR, then `/before-after` |
```

**4. Next** — a **numbered checklist, never a paragraph.** This is `/steps` inlined: the table says where things stand, the checklist says what to physically do next. Prose here is the failure mode — a Next paragraph that blends "confirm the prompt, then run this check, then branch on the result, then reboot" into one sentence makes the user re-parse a to-do list out of English every time.

Six rules (the same ones the `/steps` skill uses, inlined so this stands alone):

- **One action per line, imperative, in execution order.** Lead with the verb.
- **Inline everything the step needs** — the exact command, path, URL, ticket key, value. The user should never scroll back into the table to execute a step.
- **Commands go in a fenced block under their step**, and any command the *user* pastes uses absolute paths (they may paste into a fresh terminal) and one flag per line with `\` continuations.
- **Conditionals become their own step** (`3. If no ... line appeared, force the build first:`), never a clause inside another step. A branch buried mid-sentence is the exact thing that gets missed.
- **At most one sub-line of context per step**, and only when it changes how they execute — a gotcha, a dependency, a why-this-shape. Everything else belongs in the table or the closing paragraph.
- **Label whose only when mixed.** Most Next lists are entirely the user's — no labels. When some steps are yours, prefix each: `**You** — …` / `**Me** — …`.

Still factual forward ordering, *not* opinionated picks — if the user wants the "if I were you" layer they'll chain `/recommend`.

**Nothing left to do** → don't fabricate a list. End on a closeout line instead, so the "can I close this window?" answer needs no inference. Pick by what the table and the session already show; don't run a separate check:

- **Nothing would be lost by closing** (work landed and pushed, no lesson worth codifying, no worktree, dev server, or background agent still up) → `**Next:** nothing — <the thing> is done. Safe to /done and close out.`
- **Done, but loose ends exist** (unpushed commits, a live worktree or server, an unfiled follow-up, a lesson worth capturing) → `**Next:** nothing left on <the thing>. Run /wrap-up to clear <the loose ends, named>, then /done.` Offer it, never invoke it: `/wrap-up` commits lessons and removes worktrees.
- **Unsure whether something would be lost** → say so and point at `/done-check` rather than claiming "safe".

Shape:

````markdown
**Next:**

1. Type `y` at the still-waiting package-manager prompt to confirm the upgrade
2. When it finishes, verify the GPU driver module built for the new kernel:
   ```
   ls /lib/modules/<new-kernel>/extra/
   ```
3. If the driver module is missing, rebuild it *before* rebooting (your distro's
   driver-rebuild command, targeting the new kernel)
4. Reboot, then confirm the driver reports the new version
5. Run one supervised suspend/resume cycle
   - Suspend is untested on the new driver and this machine's history here is fragile
````

Optionally one closing paragraph for things that don't fit a row: a lesson worth remembering, or a heads-up (a dev server still up on a port, an unstaged file, a background agent still running). Only when it's real — never as filler.

## Icons

Exactly three carry the normal report. The status **is** the icon — don't also write "done" or "in progress" in the cell.

| | |
|---|---|
| ✅ | done / landed / green |
| ⏳ | in progress right now — a running agent, an open edit, a job mid-flight |
| ⬜ | queued, not started |

Two more, used only when earned: **⚠️** blocked or needs a call from the user, **❌** failed or red. A ⚠️ or ❌ row sorts to the top and must be reflected in the verdict.

## Rows

Rows are dimensions of *this* session's work, derived fresh each time — not a fixed checklist. One to two words, bolded. Typical: **Code**, **Tests**, **Browser**, **Tickets**, **Doc**, **Review**, **Deploy**, **Left**.

- Order: ✅ rows first (what's settled), then ⏳, then ⬜. A `⬜ **Left**` catch-all as the final row is the usual landing.
- 4–8 rows. Under 4, the table isn't earning its formatting — use flat bullets. Over 8, collapse related dimensions.
- Right cell: concrete — paths, line numbers, branch names, counts, ticket keys, skill names in backticks. No hand-wavy "made good progress."
- **Hard cell budget: ~320 characters.** The CLI demotes the *whole* table to a borderless stacked fallback the moment any **single** cell wraps past **4 lines**. A half-screen terminal (~130 cols) leaves only ~108 chars of cell width, so ~430 chars is the cliff — one bloated cell that looks fine full-screen takes all the other rows down with it. Overflow goes in the closing paragraph, not the cell.
- Don't pad a dimension that didn't happen this session — omit the row.

## Mid-flight variant — the hold report

Same table, emitted *while blocked* instead of at a finish line. This is the parallel-session primitive: one glance at a session says what's running and what it's gating.

**Precondition (hard — the whole variant hinges on it): fire ONLY when the turn is already over.** You are waiting on a backgrounded agent or poll and there is **no callable next tool** — the next move arrives as a notification, not as a decision you're deferring. If a next step is callable, *calling it* is the report. A hold report written where work could have continued is the exact stall that pipeline skills (`/work`, plus a project's ship skill or land-and-verify leg, if it has one) each spend paragraphs defending against.

**It is not a terminus.** When the notification lands, resume the pipeline in that turn — don't read your own hold report as a finish line and wrap up.

Three deltas from the standard shape:

- **Verdict** names what you're blocked on and what it gates — *"Tree's settled and green; `/super-review`'s verdict is the only thing between here and the PR."*
- The running thing gets its own **⏳** row, described in its own words (`running — confirming the export escaping in csv.ts`). One ⏳ row per live agent.
- **`**Holding for:**`** replaces the Next checklist: what you're waiting on and what each outcome branches into — *"clean → straight into merging; a finding → I stop and show you."* This one stays prose, because there is nothing for the user to execute. If there *is* something they can usefully do while you wait, that goes under it as a normal numbered checklist.

## Rules

- Lean. Every row earns its keep. Nothing landed yet → skip the table, say so in a sentence.
- No code changes, no file writes, no commits. Pure read/report.
- **Never emit a prose Next paragraph.** If the forward move genuinely is a single action, that's one line of prose — but two or more, or one with a branch in it, is a checklist.
- **Don't also fire `/steps` after a report.** The Next section already is one; a second pass just duplicates it.
- Skip "here's your report" / "hope this helps." Verdict first, straight in.
