---
name: tldw
description: >-
  Too long; didn't watch. Distill a YouTube video from its transcript: a TL;DR
  on top, then the substance at a set compression in one of three shapes
  (themes, argument, timeline), with timestamp links. Saved to disk;
  transcript stays loaded for follow-ups. Fire on a YouTube link plus
  "summarize", "tldr", "what's this about", or "give me the gist". "raw"
  returns the transcript only. NOT for text already in the conversation.
disable-model-invocation: false
argument-hint: "[YouTube URL or video id …] [themes | argument | timeline] [5:1] [raw] [focus] — optional"
---

Distill a YouTube video so the reader gets its substance without spending the hour: real compression, not an annotated transcript, with every point linked to the moment it was said. The top block (TL;DR, or Thesis in the argument shape) is the one-glance version; everything below it is the depth. The transcript stays in context afterwards, so follow-up questions are answered from what was actually said, not from memory.

## 1. Parse the call

- **Videos:** every YouTube URL or 11-character video id in the arguments. If there are none, use the one the user just pasted in the conversation. If there's still none, ask for it and stop.
- **Shape:** `themes`, `argument`, or `timeline` in the words overrides the user's default for this call.
- **Ratio:** `5:1` or `ratio 5` overrides the default compression for this call. "Shorter" roughly doubles it and "more detail", "deep", or "deeper" roughly halves it, when no number is given.
- **`raw`:** the transcript only, no summary (step 4).
- **Changing a default** ("make argument my default", "use 15:1 from now on"): run `python3 "${CLAUDE_SKILL_DIR}/scripts/config.py" set shape argument` (or `set ratio 15`), confirm the new defaults it prints, and carry on if there's also a video to do.
- **Anything else is focus** ("just the part about pricing", "what does she say about hiring"). Lead with it.
- **Not YouTube** (x.com, Vimeo, TikTok…): say only YouTube is supported, because other sites don't publish transcripts, and stop.
- **No shell** (claude.ai chat, or a sandbox without network): say it needs Claude Code on the user's own machine, since YouTube blocks transcript requests from cloud servers.

**Already read this video's transcript in this session** (a re-shape, a different ratio, a follow-up)? Skip straight to step 6. Fetching and reading it again costs thousands of tokens for nothing.

## 2. Fetch

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/fetch.py" URL_1 URL_2 --out "${TLDW_DIR:-$HOME/tldw}"
```

It needs only `python3`. On first run it installs its one dependency (`youtube-transcript-api`) into its own venv, which takes a few seconds; mention it if stderr says so. It prints `{"defaults": {...}, "videos": [...]}`. `defaults` holds the user's resolved shape and ratio (built-in: themes, 10). `videos` has one entry per input. Add `--refresh` if the user asks to re-fetch, or `--lang de` for a non-English preference.

Handle each entry on its own, and summarize the ones that worked even if others failed. On `status: "error"`, tell the user what the `error_code` means:

| `error_code` | Tell the user |
|---|---|
| `blocked` | YouTube refused this machine's request (VPN, a cloud IP, or too many requests). Try again later or off the VPN; installing `yt-dlp` adds an automatic fallback. |
| `no_captions` | The video has no transcript, and this skill doesn't transcribe audio. |
| `age_restricted` | YouTube only serves this video to signed-in users. |
| `unavailable` | Private, deleted, members-only, or not a valid video link. |
| `setup` | The dependency didn't install; relay the `error` text, which names the fix. |
| `network` | Relay the `error` text as-is. |

## 3. Reuse what's saved

`reused: true` means this video was fetched before, and its folder is reused instead of downloading again. `saved` lists the summaries already written (`summary.SHAPE-RATIO.md`). If the one for this call's shape and ratio exists and there's no focus, show it and say it's from the `fetched` date. Skip step 5 for now and read the transcript on the first follow-up, since re-opening a saved summary is usually a quick look and a long transcript costs tens of thousands of tokens. Otherwise write a new one.

## 4. `raw`: transcript only

Read `transcript.txt` from the entry's `dir` so it's in context, then give the path, the word count, and the first few lines. Don't paste a long transcript into the chat. Offer what to do with it next.

## 5. Read the transcript

Read `transcript.timestamped.txt` from the entry's `dir`. Each paragraph starts with `[12:34 t=754]`: the display time, and the seconds for the link. A long talk can run past what one Read returns, so read it in parts until you've seen all of it. A summary of the first hour is not a summary of the video.

## 6. Write it

**Read the shape's layout first:** `${CLAUDE_SKILL_DIR}/references/SHAPE.md` (`themes.md`, `argument.md`, or `timeline.md`). Then apply these rules in every shape:

- **Length follows the ratio.** The target is the transcript's `words` ÷ ratio (with a focus, the words of the part that's in focus). It's a target, not a limit: density moves it by about a quarter either way. A repetitive pep talk compresses harder; a dense lecture runs longer. Never pad to reach it, and never drop a distinct argument to stay under it. There is no upper cap, so a three-hour podcast gets its full share. A very short video may fall below what the shape needs; then write the top block and the few points that exist, and skip empty sections.
- **Every point carries its timestamp link:** `([12:34](https://www.youtube.com/watch?v=VIDEO_ID&t=754s))`, using the `t=` of the paragraph it came from.
- **Faithful to the transcript.** No outside knowledge anywhere except the Reader's note (or the argument shape's "How strong is the case"). If the transcript is too garbled or empty, say so in one line and stop.
- **Compress, don't transcribe.** Keep an anecdote only when it *is* the point. Cut setup, repetition, jokes, crowd work, tangents, sponsor reads, ads, "like and subscribe", and plugs.
- **Speakers.** Auto-captions don't label speakers, so name someone only when the transcript makes it clear; otherwise say "the host" or "the guest".
- **Auto-captions mangle names and jargon.** When a name or term looks mis-transcribed, flag it once ("likely *Anthropic*, captions say *and tropic*") instead of silently guessing.
- **Reader's note** (themes and timeline, last section): the one place outside knowledge is allowed, labelled as yours and not the video's: claims stated without evidence, facts that look wrong, what the speaker leaves out. Skip it when there's nothing worth flagging.

## 7. Save it

Write `summary.SHAPE-RATIO.md` (e.g. `summary.themes-10.md`) into the entry's `dir`. A focused run saves as `summary.SHAPE-RATIO.focus-SLUG.md` (e.g. `…focus-pricing.md`), so it never replaces the whole-video summary:

```markdown
# TITLE

- **Source:** URL
- **Channel:** AUTHOR
- **Fetched:** FETCHED · SHAPE at RATIO:1 · summarized by YOUR_MODEL_ID
- **Note:** auto-generated captions · translated to English · fetched via yt-dlp

---

SUMMARY
```

Drop the **Channel** line when `author` is null. Keep only the **Note** items that apply (`auto_generated`, `translated`, `fallback`), and drop the line when none do.

Drafts drift long, so check the body's count after saving (`sed '1,/^---$/d' FILE | wc -w`, which skips the header). Revise if it's more than about a quarter off target.

## 8. Present

Show it in the chat; that's the point. With several videos, give one per video. Add a short `## Across these videos` only when the user asks, or when the videos are plainly on the same subject. End with one line that gives the saved path and says they can ask follow-ups ("expand the second theme", "what did they say about X?"), re-shape it ("as an argument"), or change the depth ("5:1").
