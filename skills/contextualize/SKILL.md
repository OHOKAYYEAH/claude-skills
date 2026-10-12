---
name: contextualize
description: "Re-pitch something at a lower assumed-context level: rebuild the domain, product and code background it stood on, then deliver the finding, through a business, code, UI or UX lens. Lean by default; `full` for the complete re-pitch. Fire when the user signals the gap (\"I don't have the context you do\", \"what even IS that term\"). Don't self-trigger. NOT /explain (what the assistant did), /bigpicture (zooms out), or /tldr."
disable-model-invocation: false
argument-hint: "[full] [lens: business | code | ui | ux, any mix, in plain words] [the specific thing to re-ground]"
---

The user just told you that you explained something over their head — not because it was
complicated, but because you stood it on context they don't have and you do.

**Why this keeps happening** — worth holding in mind because it's four distinct gaps, not
one:

1. You are holding the code and product context in-window right now. They aren't.
2. You assume engineering and domain knowledge they don't share yet.
3. **They may work at an abstracted level from the product and the code** (directing agents
   rather than using the product themselves) — so they don't even know the
   *product* the way a regular hands-on user would. This is the one that gets
   under-weighted. Don't just de-jargon the engineering and call it done.
4. Ticket history and prior-conversation context you loaded and they didn't.

And the reason it costs so much: assumed context is an understanding black hole. An
unexplained premise doesn't slow the reader down a little — it swallows the whole
explanation after it.

## Step 0: pick the lens

The user steers in plain words, often mid-sentence ("can you /contextualize the code, UI, and
UX for me?"). Read the lens from the arguments **and** the message that invoked you; both
count. No steer means **business**, the default. Several lenses can apply; order them the
way the user named them.

| Lens | "The world" to build first | Ground it in |
|---|---|---|
| **business** | Real people and things: who transacts with whom, what moves, who pays | Real named customer, real dollars |
| **code** | The running system: which pieces exist, who calls whom, what data flows between them, which file owns which job | A traced path through real files, plus a box diagram of the flow |
| **ui** | What's on the screen: which page, which fields, what's editable, what the user sees change | **Real screenshots** (see Visuals) |
| **ux** | What a user *does*, step by step: what they expect, where the app surprises them | **Real screenshots** of each step, in order |

The lens picks the *opening*, not whether you show pictures: under every lens, a subject
that touches a screen gets real screenshots (see Visuals).

A non-business lens swaps the opening, not the method. Give the business world one
sentence, only if the finding depends on it, then build the lens's own world. Every rule
below applies within each lens.

## Lean is the default; `full` asks for the complete re-pitch

Most of the time the user wants the ground under the finding, not the full re-pitch, so lean
runs unless `full` appears in the arguments or the invoking message (`lean` still works and
changes nothing). The method stays; the volume drops:

- **About one screen** of reading: the world (2–3 sentences), the world→system hinge (one small
  table or a few lines), the anchor fact, then the finding and what it asks of them.
- **1–3 frames**, only the ones the finding turns on. Same opt-out rule, same /present page.
- **Cut** base rates, the skeptic's defense, and pre-empted snags unless one of them is what the
  finding hinges on. Keep the established / inferred / unknown labels; they're cheap.
- Rigor still holds. Real numbers stay exact, nothing gets invented, and a lean page that left
  out the one premise they needed has failed the same way a vague one does.

The "expect to roughly double the length" rule and the numbered sections in Shape below
apply only to `full`; a lean page is one flow.

## The one rule that governs the rest

**Lower the assumed context, not the rigor.** You are adding the ground underneath, not
sanding down what's on top. Keep the real numbers at full precision, keep the tables, keep
the caveats, keep the uncomfortable findings. A response that got *shorter* and *vaguer*
has failed — that's `/tldr`, and it's a different skill. In `full`, expect to roughly double the
length. That's correct.

If you're missing a concrete grounding detail — a real example row, an actual count, what a
term means in this business — **go get it.** Read the code, query the data, check the
ticket. Grounding you invented is worse than the abstraction you replaced.

## Method

Work up from the world. The technical finding usually lands around two-thirds of the way in
— if it's in your first paragraph, you've skipped the part they actually needed.

**Build the world first.** Open with what physically happens among real people and things:
who transacts with whom, who pays whom, what moves. No tables, no code, no field names.
Someone who has never seen this software should follow it.

**Then map world → system, once, compactly.** A small "what one row means" table, or a
single sentence per entity. This is the hinge of the whole explanation; make it explicit
rather than letting them infer it.

**Name the jargon at first use, in business terms.** Every acronym, every table name, every
term of art. Inline or in a small table — not a footnote, not "as you know."

**Give them one anchor fact and lean on it.** Pick the single load-bearing fact the rest
depends on, state it once in bold, then refer back to it instead of re-deriving it.
(`order_line` = one shipped item. A refund can land months after the order closes.) One anchor, not four.

**Use a real named instance with real numbers.** A named customer, a real sale, actual
dollars and dates. Concrete beats abstract every time, and it gives them something to hold.

**Explain the mechanism, so the conclusion is derived rather than asserted.** If the bug
turns on what a SQL JOIN does, spend the two sentences saying what a JOIN mechanically does
— then the bug becomes *obvious* instead of something they have to take on faith. This is
the difference between them understanding it and them believing you.

**Pre-empt the snags.** Anything that will look like a typo, a bug, or sloppiness — fractional
quantities, accounts that are never formally closed — flag it *before* they trip on it. A reader
who snags on a detail stops following the argument.

**Give base rates, not one confirming example.** How often, out of how many, over what
window. One example proves a thing can happen; the distribution tells them whether to care.

**Separate what's established from what's inferred from what nobody can know.** Label
confidence where you're inferring. And where a question genuinely isn't yours to answer, say
so and name whose it is — that's the difference between a finding and a decision they owe
someone.

**Defend the conclusion against the fair objection.** Ask what a smart skeptic would say
("maybe it's supposed to work that way") and answer it with independent evidence. They can't
audit your reasoning from the code, so give them the grounds to trust it.

## Shape

Numbered sections with plain-language headings, opening with a line like *"Skip ahead if a
section is already familiar"* — they shouldn't have to read past what they already know to
reach the part they don't.

Order: the world → how it's stored → the specific thing that matters → the finding → what it
means → why you're confident. Lead with a one-line bottom line only if the finding is
genuinely urgent; otherwise let the ground come first, since arriving at the finding already
equipped is the entire point.

If an argument names a specific thing (not just a lens), narrow to grounding that thing
rather than re-pitching everything: $ARGUMENTS

## Visuals — show the app, don't describe it

If the reader maintains or directs the app rather than using it, a paragraph about a screen
rarely lands. **Screenshots are opt-out, not opt-in: under every lens, if the subject touches
anything a user sees or does in the app, capture it.** When no screen is involved (a batch
job, a data fix, an infra path), draw the flow instead: a small diagram of who or what moves
where. Every run gets at least one visual; the user shouldn't have to ask for one. Real app
frames and flow diagrams only; never decorative or stock imagery.

1. **Get real frames with /devtools.** Local is the default; use the project's test creds
   to log in. Capture the exact screen and state the finding is about: the form, the field,
   the before and after of the action. Follow the project's rules on who starts which dev
   server. If you can't reach a real screen, say which frames are missing and why. Never
   describe a frame you didn't take, and never substitute a mock.
2. **Write the contextualization as a markdown doc** with each frame embedded where the
   text discusses it, not in a gallery at the end. Save it wherever the project keeps
   private, uncommitted notes, with the frames alongside it.
3. **Hand it to /present** (`present doc`). This page is the deliverable the user asked
   for, so open it. The terminal gets the bottom line plus the path, not a second copy.

**The page is always the deliverable**, opened via /present, never terminal-only. The
code lens's box diagram of the flow goes inline in that page too, plus the screen the code
path ends at, if it ends at one.

## Register

Write to a bright colleague who has never seen this codebase or this industry — not to a
beginner. Never condescend, never announce that you're simplifying, and don't apologize for
the earlier explanation; just deliver the better one.

If the user's style invites a light touch of humor, it's welcome **at the close, once** — it
lands as a breath after a dense read. Forced mid-explanation it just costs attention they
were spending on the argument.
