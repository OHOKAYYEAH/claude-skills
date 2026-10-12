---
name: steps
description: >-
  End a response with an ordered, copy-pasteable who-does-what checklist,
  rationale dropped. FIRE PROACTIVELY whenever a response leaves the user work the
  CLI cannot or will not do (dashboard-only setting, OAuth login, DNS record,
  secret paste, starting the local dev stack, destructive git they must confirm). Also after
  /recommend or before /handoff. NOT /recommend (that picks the move; this lists steps already decided).
disable-model-invocation: false
argument-hint: "[optional focus or scope]"
---

Pull the steps that move the work forward out of the prior response and lay them out as a clean checklist: what the user does, what Claude does, in what order. Assume the prior response interleaved instructions with explanation, rationale, and aside-commentary — strip all of that and surface just the do-this list.

The list covers both actors, not just the user's half: in a mixed sequence (you, you, me, you) the order *across* actors is exactly what gets lost on a context switch.

## When to fire this WITHOUT being asked

The user should not have to type `/steps` to get the to-do list out of a wall of prose. Fire it yourself whenever a response ends with work on their side, specifically:

- **The CLI genuinely cannot do it** — a vendor dashboard that refuses API writes (probe first; the refusal is the evidence), an interactive OAuth login, a registrar DNS record, entering a payment card, a real-browser check headless can't fake.
- **The CLI will not do it, by a rule the user set** — a secret only they can paste (through a no-echo entry flow, never into chat), starting a dev server they run themselves, a destructive or irreversible git operation needing their confirmation, an outward-facing push they haven't cleared.

Two judgment calls that keep this from becoming noise:

- **One step is not a checklist.** A single obvious action ("click Create token") stays inline prose. Reach for the list at roughly two or more steps, or one step with real gotchas.
- **Don't split the response.** The steps go at the END of the substantive answer, not instead of it. The user still wants the reasoning; they just shouldn't have to mine it for the to-do.

The trigger is still work on *the user's* side. A sequence that is entirely Claude's and needs nothing from them is not a reason to stop and print a list — do the work.

## Whose step

- **Unlabelled means all the user's.** Most lists are entirely theirs; leave them bare.
- **The moment any step is Claude's, label every step** — `**You** — …` for the user, `**Me** — …` for Claude. Same convention as `/report`'s Next section.
- **One actor per step.** A "together" action splits into its two halves, in order: `**You** — trigger the login` then `**Me** — read the server log for that request`.
- **A Me step belongs in the list only if it has to wait** — on a You step, on their confirmation, or on their go-ahead. Work Claude can do right now with nothing from them isn't a step: do it first, then fold the result into the You step that depends on it (see *Inline dependency context*).
- **Say what a waiting Me step waits for.** That is the hand-back point — it tells the user what to say to get Claude moving again.

## Output shape

Plain numbered list, imperative voice. One sub-line of context allowed per step, only when it aids execution.

All the user's:

```
1. Open Vercel → Project X → Settings → Env Vars and add `STRIPE_SECRET_KEY`
   - Copy the value from local `.env` — don't paste it into chat
2. Trigger a redeploy from the Deployments tab
   - Vercel only picks up the new env var on next build
3. Confirm the build by checking the `Environment` panel for `STRIPE_SECRET_KEY`
4. Run `supabase db push` locally to sync the migration to the hosted DB
```

Mixed:

```
1. **You** — Mint a Railway token (Account → Tokens) and store it as `RAILWAY_TOKEN` in `.env`
   - Don't paste the value into chat
2. **Me** — Deploy the staging service and read its health check back, once you say the token is in
3. **You** — Open the staging URL in a real browser and confirm Google login completes
   - Headless can't pass Google's bot check
4. **Me** — Promote staging to prod after you confirm step 3
```

Rules for each step:
- Imperative voice ("Open X", "Run Y", "Paste Z"). Lead with the verb.
- Inline the exact value, path, command, URL, or name the step needs — the user shouldn't have to scroll back up to find it.
- Preserve code formatting: shell commands, file paths, env var names, and identifiers stay in backticks or fenced code blocks. `npm install` reads very differently from npm install when scanning to copy-paste.
- Add a context sub-line when it changes how the user executes — a gotcha, a "why this matters," a "watch out for" hint, a dependency on a prior step. Skip it when the action speaks for itself; not every step needs one.
- Don't nest deeper than one level.

## Rules

- **Only what's still to do.** Drop anything Claude already did — it appears only as context on the step that depends on it. Which of Claude's pending actions qualify, and how they're labelled: see *Whose step*.
- **Inline dependency context.** When a user step depends on something Claude completed (e.g. "I pushed `feature-x` — you open the PR"), fold that context into the step itself: `Open the PR for \`feature-x\` at <URL>`. Otherwise the checklist reads as instructions floating in a vacuum.
- **No fabrication.** If the prior response laid out no pending steps for either actor (it was pure explanation, code, or analysis), say so plainly: `No steps in the prior response — it was [explanation / code / analysis].` Don't invent steps to fill the format.
- **Trim the rationale, keep the load-bearing bits.** Drop verbose asides, alternative paths the user isn't taking, and post-hoc commentary. *Keep* the anchoring context that makes a step actually executable — the gotcha, the constraint, the thing that explains why this step is shaped this way. Lean, but not stripped to the bone.
- **Preserve execution order.** If the prior response laid the steps out in a specific order (dependencies, prerequisites), keep that order. If the order was incidental, use whatever order makes the work flow naturally.
- **No preamble, no signoff.** Skip "Here are your steps..." / "Let me know if...". Just the list.
- **Don't fire after `/report`.** `/report`'s Next section already emits this shape inline; running `/steps` on it just duplicates the list.

If the user added a focus below, narrow to just that slice (e.g. `/steps deployment` → only the deploy-related steps): $ARGUMENTS
