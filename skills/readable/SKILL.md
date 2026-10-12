---
name: readable
description: >-
  Turn a raw transcript (meeting captions, a lecture, an interview, a podcast)
  into a readable edition: the whole thing, in order, in the speakers' own
  words, with only filler, false starts, and caption stumbles smoothed away.
  Near 1:1, not a summary; a word-level drift check proves nothing was added.
  Fire on "readable edition", "clean up this transcript", "make this
  readable". NOT compression (/distill), NOT prose that is already clean (an
  article, a book).
disable-model-invocation: false
argument-hint: "[file path, or a time range like 14:30-14:40] — optional"
---

Make a readable edition of a transcript: the way a publisher prints a transcribed talk. A reader should be able to read it *instead of* the raw transcript and miss nothing. You are cleaning, not co-writing, and not compressing; `/distill` is the skill for compression.

The one failure this skill exists to prevent is invisible on the page: fluent prose the speaker never said. A broken clause smoothed into good English, a supplied preposition, a false start collapsed the wrong way round, a dropped "not". It reads fine, passes any length check, and misquotes a real person. So the edition is verified word by word against its source before anyone sees it (step 5).

## 1. Parse the call

- **Source**, first match wins: a file path in the arguments; a transcript the user pasted in this conversation; a `/tldw` video folder's `transcript.timestamped.txt` they point at (if you use the `/tldw` skill); otherwise ask for it and stop.
- **Not a transcript** (an article, a book chapter, anything written rather than spoken): say it's already readable and offer `/distill` instead. There's nothing to clean.
- **A time range** ("just 14:30–14:40") limits the edition to that span.

## 2. Get the source on disk

The edition shares a folder with `/distill`, so a source's summary and its edition sit together: `${DISTILL_DIR:-$HOME/distill}/SLUG/`, SLUG a short kebab-case name plus the date when known. Check `ls` first and reuse a matching folder. A `/tldw` source stays in its own video folder, and the edition is written there.

- **Pasted:** never retype a paste; the session log holds it verbatim:
  ```bash
  python3 "${CLAUDE_SKILL_DIR}/scripts/grab_paste.py" \
    --out "$DIR" --match "A PHRASE FROM THE PASTE"
  ```
  On `no_paste` or `no_session`, write the text to `$DIR/source.txt` yourself and mention it.
- **File:** use it where it is.

## 3. Read all of it, in order

In parts if one Read won't hold it. Note the speakers, the source's own time markers, and where captions from people talking over each other interleave.

## 4. Write it

**Remove (noise):**
- Filler and disfluency: *um*, *uh*, and *like*, *you know*, *I mean*, *kind of*, *sort of*, *okay?*, *right?* when they're verbal tics carrying nothing.
- False starts and self-corrections: "the book is — the book is on the table" → "the book is on the table". **Keep the corrected half, drop the abandoned one.** Done backwards, it reads fluently and says the wrong thing.
- Immediate repetition ("very, very, very" → "very"; a sentence said twice → once), unless the repetition is deliberate emphasis. A speaker hammering a point is voice, not noise.
- Caption stumbles: doubled words, a cue split mid-word.
- Backchannel turns that answer nothing: a lone "Yeah." / "Mm-hmm." / "Okay." from a listener. A "Yeah" that answers a question is content and stays.

**Keep (everything else):**
- Every point, aside, joke, and tangent, in the order said. If they spend four minutes on a tangent, so does the edition. **Over-sanding is a defect.** What makes a transcript worth reading is that a person is talking, so keep their phrasing, idiom, and slang ("gonna" stays "gonna").
- Names, numbers, and quotations as spoken, even when they look wrong. Flag them; don't fix them (the repair rules below).

**Layout:**
- **Turns.** Merge a speaker's consecutive caption fragments into one turn: `[TIME] **Speaker:** text`. TIME is the source's own marker for the first fragment, copied as printed (`[14:02:13]`, `[12:34]`), never computed or estimated. Break a long turn into paragraphs at topic shifts, each led by the time of the fragment that starts it.
- **A single-speaker lecture** gets paragraphs with anchors and no labels. A label appears only when another voice speaks (`[Student:]`, or the name if the speaker gives it).
- **Crosstalk.** Captions of overlapping speech interleave. You may move a short interjection to just after the sentence it responds to. That's the only reordering allowed, and the drift check lists every move.
- **Speaker labels stay as the source gives them.** A label several people share (a conference-room mic, a dial-in line) is never split into guessed names. Say in the editorial note who seems to be behind it, and on what evidence.

**The only additions allowed** are speaker labels, time anchors, and `[inaudible]` where the source itself marks a gap. No stage directions (`[laughter]`), no headings, no clarifications, no transitions nobody spoke.

**Repairs: repair what misleads, leave what is visibly broken.**
- *Mechanical* stumbles (doubled words, a split cue) carry no meaning: fix them.
- *Semantic* mangles (a misheard name or term, where the fix changes what the sentence says) get repaired **only when the source itself attests the right form**, e.g. the same speaker says the name correctly elsewhere. Otherwise print it verbatim and flag it in the note with the likely reading. If you can't tell which kind you have, it's semantic.
- The dangerous mangle is the one that reads as ordinary English. Wreckage misleads nobody; a plausible wrong name enters the record.
- **Never half-repair a broken clause.** Fixing the one word you're sure of can turn obvious wreckage into fluent prose that asserts the opposite. Leave the whole clause and flag it.
- **Never repair a negation or an inversion.** When a transcript seems to contradict the speaker's own argument, report it in the note. You can't tell a caption error from a slip of the tongue, and only one of them is yours to touch.

**Length has no target.** Whatever falls out of faithful cleaning is right: a filler-heavy meeting may land near 70%, a fluent lecture near 95%. Under ~60% means you compressed. Over 100% means you added. Never trim to hit a number.

**Save format**, written to `$DIR/readable.md` (a range edition: `readable.RANGE.md`, e.g. `readable.1430-1440.md`):

```markdown
# TITLE — readable edition

- **Source:** FILE PATH, or "pasted in session" (saved copy: $DIR/source.txt)
- **Made:** DATE · SOURCE_WORDS → EDITION_WORDS words (RATIO) · by YOUR_MODEL_ID
- **Speakers:** as labelled in the source; shared-label caveats in the note

---

[14:02:13] **Alex Rivera:** You just have to update the notes. I'm gonna pick the reviewers soon. Don't worry.

[14:02:20] **Sam Chen:** Yeah, get out of there.

## Editorial note

- **Repairs:** each one as `original → printed (TIME): why`, or "None".
- **Flagged, not repaired:** likely mis-transcriptions with their likely reading, and any contradictions or broken clauses left as spoken.
- **Moves:** interjections moved to follow what they answer.
- **Speakers:** shared labels and who seems to be behind them.
- **Dropped stray fragments:** caption noise nobody continued, each with its time.
- **Drift check:** the counts from step 5, and that every listed site is accounted for.
```

A long source won't fit one write. Past ~3,000 words of body, write the header and first part with Write, then append each following part in order (`cat >> "$FILE" <<'EOF'`), reading the source alongside.

## 5. Verify, word by word

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/drift.py" SOURCE_FILE "$DIR/readable.md"
```

A range edition is checked against only its slice of the source: add `--from 14:30 --to 14:40`, written in the source's own time format.

It prints the word counts and ratio, then a closed review list: every **ADDED** word, every **CHANGED** short substitution, every **CONTENT** removal (flagged `NEGATION` or `NEAR-TWIN` where those apply), and every **MOVED** span. Filler, duplicates, and soft discourse markers are tallied rather than listed. Nothing on the list is automatically wrong. Each site must be one of:
- **licensed noise**: a false start (the corrected half kept), a backchannel reply that answers nothing, a stray caption fragment. These are what the edition is for. Check each one, and count them by class in the note rather than listing them, except stray fragments, which are listed so a reader can see what was dropped;
- **licensed and disclosed**: a repair in the note's list, a move, a turn label the normalizer missed; or
- **drift**: restore the source's words in the file.

`NEGATION` and `NEAR-TWIN` sites get checked against the source every time: a dropped "not", or the abandoned half of a false start kept instead of the correction. Re-run until every remaining site is accounted for, then put the final counts in the Made line and the note. Don't report a count from memory. An editor who hasn't run the check is reporting what they intended to change, not what they changed.

## 6. Present

Don't paste the edition into chat; it's as long as the transcript. Hand the file to `/present` (a doc, so it renders as one readable page). Then give one line: the path, source → edition words and ratio, the number of repairs and flags in the note, and that `/distill` summarizes the same saved source.

## Scripts

`scripts/grab_paste.py` and `scripts/count.py` are identical copies of the ones in `/distill`; `drift.py` imports `count.py` so the word counts and the drift check agree on what a word is. Change one copy, change both.
