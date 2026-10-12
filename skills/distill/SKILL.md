---
name: distill
description: >-
  Distill any text: a pasted transcript, meeting captions, an article URL, or a
  file. Returns a TL;DR plus the substance at a set compression ratio in one of
  four shapes (themes, argument, timeline, meeting), each point anchored to the
  source. Fire on "summarize this transcript / article /
  meeting", "distill this", "what did they decide". NOT a YouTube link (/tldw,
  if installed),
  NOT Claude's own last reply (/tldr), NOT a near-verbatim cleanup
  (/readable).
disable-model-invocation: false
argument-hint: "[file path or URL] [themes | argument | timeline | meeting] [10:1] [focus] — optional"
---

Distill a long text so the reader gets its substance without reading all of it: real compression, not an annotated copy, with every point anchored to where it came from. The top block (TL;DR, or Thesis in the argument shape) is the one-glance version; everything below it is the depth. The source stays in context afterwards, so follow-ups are answered from what it actually says.

## 1. Parse the call

- **Source**, first match wins: a file path in the arguments; a URL in the arguments; the text the user pasted in this conversation (the newest paste, unless they point at another); otherwise ask for it and stop.
  - A YouTube link belongs to the `/tldw` skill, if you have it, which fetches the transcript; say so and stop. Without it, ask for the transcript text.
  - Claude's own previous reply belongs to `/tldr`.
- **Shape:** `themes`, `argument`, `timeline`, or `meeting` in the words overrides the default for this call. With no shape named, a speaker-labelled transcript with three or more voices takes the configured `meeting_shape`. Say which shape you picked in one line, so a re-shape is one word away.
- **Ratio:** `5:1` or `ratio 5` overrides the default. "Shorter" roughly doubles it; "more detail", "deep", or "deeper" roughly halves it.
- **Changing a default** ("make meeting my default", "use 15:1 from now on"): run `python3 "${CLAUDE_SKILL_DIR}/scripts/config.py" set shape meeting` (or `set ratio 15`, or `set meeting_shape themes`), confirm what it prints, and carry on if there's also a source to do.
- **Anything else is focus** ("just the part about pricing", "what did the CTO say about the roadmap"). Lead with it.

**Already distilled this source in this session** (a re-shape, a new ratio, a follow-up)? Skip to step 4; reading it again costs thousands of tokens for nothing.

## 2. Get the source on disk

Pick the output folder: `${DISTILL_DIR:-$HOME/distill}/SLUG/`, where SLUG is a short kebab-case name for the source plus its date when one is known (`pricing-talk-2025-03-14`). A source distilled before reuses its folder, so check `ls` first and reuse a matching one.

- **Pasted:** never retype a paste. Claude Code keeps it verbatim in the session log, and this copies it out:
  ```bash
  python3 "${CLAUDE_SKILL_DIR}/scripts/grab_paste.py" \
    --out "$DIR" --match "A PHRASE FROM THE PASTE"
  ```
  It prints `{"path", "words", ...}`. On `no_paste` (short pastes arrive untagged), write the text to `$DIR/source.txt` yourself; on `no_session`, do the same and mention it.
- **File:** use it where it is; don't copy it. A PDF gets converted first, so it can be counted and read in parts: `pdftotext "$F" "$DIR/source.txt"`, then work from `source.txt`.
- **URL:** fetch it with WebFetch, asking for the article's full text verbatim with headings, and save that as `$DIR/source.txt`. WebFetch runs the page through a model, so name the route in the header's Note line. A paywall, login wall, or empty result: ask the user to paste the text.

Then count the words a reader reads. Caption timing lines and speaker labels don't count:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/count.py" SOURCE_FILE
```

## 3. Read the source

Read all of it, in parts if one Read won't hold it. A summary of the first half is not a summary. Caption files interleave people who talk over each other, so track who said what by the labels, not by position.

## 4. Write it

**Read the shape's layout first:** `${CLAUDE_SKILL_DIR}/references/SHAPE.md` (`themes.md`, `argument.md`, `timeline.md`, or `meeting.md`). Then apply these rules in every shape:

- **Length follows the ratio.** The target is the source's counted words ÷ ratio (with a focus, the words of the part in focus). Density moves it by about a quarter either way: a repetitive pep talk compresses harder, a dense report runs longer. Never pad, and never drop a distinct claim to fit. When cutting, cut support before claims, and cut names, numbers, citations, and attributions last. There's no upper cap. A very short source may fall below what the shape needs; then write the top block and the few points that exist, and skip empty sections.
- **Anchor every point with the source's own markers, never computed ones.** Captions → the clock time the point starts (`(14:04)`); a timestamped lecture → `(12:34)`; an article or report → its section heading (`(§ Pricing)`) or page (`(p. 12)`); a source with no markers gets no anchors.
- **Faithful to the source.** No outside knowledge anywhere except the Reader's note (or the argument shape's "How strong is the case"). If the source is too garbled or empty, say so in one line and stop.
- **Compress, don't transcribe.** Keep an anecdote only when it *is* the point. Cut setup, repetition, jokes, crowd work, tangents, sponsor reads, and plugs.
- **Speakers.** Name someone only when a label or the text makes it clear; otherwise "the host", "the author", "someone in the room". A label shared by several people (a conference-room mic, a dial-in line) gets named in the Reader's note, not silently split into guesses.
- **Mangled names and jargon.** Captions and speech-to-text garble proper nouns. When one looks wrong, flag it once ("likely *Kalshi*, captions say *Kosci*") instead of silently guessing.
- **Reader's note** (last section, all shapes but argument): the one place outside knowledge is allowed, labelled as yours: claims made without evidence, facts that look wrong, what the source leaves out, speaker-label caveats. Skip it when there's nothing worth flagging.

## 5. Save and check

Write `$DIR/summary.SHAPE-RATIO.md` (e.g. `summary.meeting-10.md`). A focused run saves as `summary.SHAPE-RATIO.focus-SLUG.md`, so it never replaces the whole-source summary:

```markdown
# TITLE

- **Source:** FILE PATH or URL, or "pasted in session" (saved copy: $DIR/source.txt)
- **Made:** DATE · SHAPE at RATIO:1 · SOURCE_WORDS → SUMMARY_WORDS words · by YOUR_MODEL_ID
- **Note:** caption transcript · fetched via WebFetch · shared-mic speaker labels

---

SUMMARY
```

Keep only the Note items that apply, and drop the line when none do. Then count the body mechanically, because models under-count their own output by about a quarter:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/count.py" SUMMARY_FILE --kind summary
```

More than about a quarter off target: revise and count again before showing it. Put the final count in the Made line.

## 6. Present

Show it in the chat; that's the point. End with one line: the saved path, and the three follow-ups: questions ("what did the host say about liability?"), a re-shape ("as meeting"), or a new depth ("5:1"). When the source is a transcript, add that `/readable` makes a cleaned near-verbatim edition from the same saved copy.
