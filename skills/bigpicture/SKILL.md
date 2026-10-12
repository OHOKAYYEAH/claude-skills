---
name: bigpicture
description: >-
  Zoom out on in-flight work as one page: bottom line, a map of every moving
  part ("you are here", GO gates), what each piece fixes, the one mechanism the
  risk turns on, and why the next go is safe. Fire on "give me
  the big picture", "zoom out", "where are we across all of it", "before I /go
  on X". NOT /report (quick status table), /contextualize (one finding, in
  depth), or /tldr.
disable-model-invocation: false
argument-hint: "[optional: the decision or scope to center on, e.g. before I /go on #123]"
---

The user asks for this mid-flow, usually right before a go-ahead on work that has grown
opaque: several tickets, several sessions, several environments, and a risk they can feel
but can't see. They need two things at once, and a page that gives only one has failed:

- **Where are we:** state and sequence. What's done, what's waiting on them, what's held
  and why, and what each of their go-aheads unlocks.
- **How does the risky part work:** the one mechanism the decision turns on, grounded
  enough that "it's safe" is something they can derive rather than take on faith.

This zooms *out* across many parts. `/contextualize` zooms *in* on one finding; if the ask
is really "what even is X", that's the better skill. Don't self-trigger. When you're about
to ask the user for a go on multi-part work, you may offer this in one line.

## 1. Re-read the state; don't recall it

A big picture built from session memory is a confident map of last hour's world. Before
writing, re-read every status the page will assert:

- `git fetch` in each repo involved, then branch and merge state.
- PR state (open, reviewed, merged) from the PR host, CI status, and what's deployed
  from the deploy platform itself (its revision or release list, not the merge log).
- Peer sessions, when several are coordinating: read each one's latest turns, so the
  "who's doing what" row matches what that session is actually doing, not what it said
  an hour ago.

The page opens with an as-of line naming what was re-read. Anything you couldn't re-read
is labelled "from session memory" where it appears.

## 2. Find the decision and the one mechanism

- **The decision:** what is the user about to approve, and what are all the go-aheads
  still ahead of them? Count them. If the arguments name a decision, center on it. If none
  is pending, center the page on "where are we" and say so.
- **The mechanism:** the single "how it works" the risk turns on (a connection pool
  running out, a timestamp stored without a time zone, a migration that locks writes).
  Ground it the way `/contextualize` does: one anchor fact in bold, real numbers, and the
  mechanism explained step by step so the conclusion is derived, not asserted.
  One mechanism, not a tour; if three things are risky, the map shows all three and the
  mechanism section takes the one their next go depends on.

## 3. Draw the map

The map is the reason this is a page and not a message. Pick the picture that fits:

- **Moving parts across environments or time** (a release chain, a multi-session plan):
  a hand-written SVG saved beside the doc. Columns are stages (`main → preview → prod`) or time; lanes are releases, tickets or sessions.
  - Status colors, used consistently: done green, waiting on the user amber, held or
    blocked purple, not started grey.
  - Each of the user's go-aheads is a diamond labelled GO. Mark the current one "you are here".
  - Dashed arrows for cross-lane dependencies, labelled with the trigger ("staging PR
    merged → hold lifts").
  - A one-line legend. White background so it reads in light and dark. Text at least
    12px, about 1100px wide.
- **A change a user will see**: real before/after screenshots via `/devtools`, cropped to
  the field that changes, captioned with the concrete values (`$12.00` → `$12.50`).
- Both, when both apply. A subject with no stages and no screen gets a small table
  instead, and the page says why there's no diagram.

Draw only what you re-read in step 1. A box whose state you guessed is worse than no box.

## 4. Write the doc

Write it as markdown with the map embedded where the text refers to it. About one to two
screens. Order:

1. **Title + as-of line.** `# <what this is>: <tickets>`, then *As of <date>, re-read
   from <sources>.*
2. **Bottom line** (a blockquote): how many parts, what ships when, how many go-aheads
   they'll give, and what the next one is with its risk in one clause.
3. **The map.**
4. **What each piece fixes:** a table, `Item | Problem | Fix | Where it is`, with a
   status emoji in the last column. Problems in the user's terms ("payments failed when
   two people saved at once"), not the code's. When the fix's shape is the opaque part,
   add a small before/after diagram of which components change and how they connect.
5. **How the risky part works:** the lean mechanism from step 2.
6. **Who's doing what:** only when more than one session is involved. Session, role,
   holding until.
7. **Your go-aheads:** numbered, the current one marked, plus what runs without the user
   between them.
8. **Why the next go is safe:** evidence with base rates (how often, out of how many,
   over what window), what fails safe, and the rollback. A concern/answer table works well.
9. **What it brings:** the expected outcome once it's all live, in what users and the
   system will do differently, and how we'll know it worked.
10. **What's left:** short, labelled yours vs mine.

Gloss every term of art on first use. Label inferences as inferences. Keep real numbers
exact. A section with nothing to say is dropped, not padded.

## 5. Save and present

Save it outside version control (a gitignored local notes folder in the repo, or a scratch
dir) as `<ticket-or-slug>/big-picture.md`, with the SVG and any frames beside it. Asked
again later on the same work, overwrite it: it's a snapshot, and the as-of line carries
the date. Then hand it to `/present doc <abs path>`.

The terminal gets the bottom line and the absolute path of the page, nothing more. If the
"big picture" turns out to be one item with no gates, there's no map to draw: answer in
the terminal and offer `/contextualize` if the gap is understanding, not state.

## Register

A bright colleague who hasn't been in these sessions, not a beginner. Never condescend or
announce that you're simplifying.
