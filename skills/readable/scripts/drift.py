#!/usr/bin/env python3
"""Word-level drift between a source transcript and its readable edition.

Usage: drift.py SOURCE EDITION [--from 14:30] [--to 14:40] [--context 6] [--show-soft]

--from/--to limit the SOURCE to words whose time marker falls in that span, for a range edition.

Why: every aggregate check (ratio, anchors) passes an edition that quietly co-writes — a
broken clause smoothed into fluent English, a supplied preposition, a false start collapsed
backwards. Only a word diff sees those. This never fails; it prints a closed review list, and
every site on it must be accounted for by the edition's own editorial note or fixed.

Reported:
  ADDED        words in the edition that the source never said here. Listed in full.
  CHANGED      a short substitution (≤3 words → ≤3 words): a repair. Must be disclosed.
  CONTENT      a removal that isn't filler, soft discourse, a duplicate, or a move. Listed.
               NEGATION marks one containing not/no/never/…n't — dropping it reverses a claim.
               NEAR-TWIN marks one resembling the text beside it — a false start whose halves
               differ. Confirm the half kept is the corrected one.
  MOVED        a span removed in one place and added verbatim in another (crosstalk reordered).
  SOFT         discourse markers (like, you know, I mean, okay…) removed: tallied by phrase.
  FILLER / DUPLICATE   um/uh, and exact repeats of the neighbouring span: counted only.

Normalization (captions, labels, anchors) comes from count.py beside this file, so this and
the word counts can never disagree about what a word is.

After changing this file, run it on fixtures/source.txt + fixtures/edition.md: it must flag the
dropped "not" (NEGATION NEAR-TWIN), "can't" → "can" (CHANGED, NEGATION), and two ADDED words.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count import marked_tokens  # noqa: E402

FILLER = {"uh", "um", "er", "erm", "ah", "hmm", "mm", "mhm", "mmhm", "huh"}
SOFT = {"like", "you", "know", "i", "mean", "okay", "ok", "so", "well", "oh", "right", "yeah",
        "yep", "just", "kind", "of", "sort", "actually", "basically", "literally", "really",
        "anyway", "cool", "and", "but", "alright", "thank", "thanks"}
MOVE_WINDOW = 80  # source words
NEG = {"not", "no", "never", "without", "nothing", "none", "neither", "nor", "cannot", "nobody"}


def secs(t: str) -> float:
    """'14:30' or '14:30:05' → seconds. A two-part marker is H:MM when --from/--to use it and
    MM:SS in a lecture; both compare consistently as long as the range uses the source's form."""
    parts = [int(p) for p in t.split(":")]
    return sum(p * 60 ** (len(parts) - 1 - i) for i, p in enumerate(parts))


def is_neg(span) -> bool:
    return any(w in NEG or w.endswith("n't") for w in span)


def near_twin(src, i1, i2) -> bool:
    span = src[i1:i2]
    n = len(span)
    if n < 2:
        return False
    for other in (src[max(0, i1 - n):i1], src[i2:i2 + n]):
        if other and difflib.SequenceMatcher(None, span, other).ratio() >= 0.6:
            return True
    return False


def is_dup(src, i1, i2) -> bool:
    span, n = src[i1:i2], i2 - i1
    return src[max(0, i1 - n):i1] == span or src[i2:i2 + n] == span


def ctx(toks, a, b, k, marks=None, label="") -> str:
    left = " ".join(toks[max(0, a - k):a])
    right = " ".join(toks[b:b + k])
    mid = " ".join(toks[a:b])
    where = f"({marks[a]}) " if marks and a < len(marks) and marks[a] else ""
    return f"{where}…{left} [{label}{mid}] {right}…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("edition")
    ap.add_argument("--context", type=int, default=6)
    ap.add_argument("--show-soft", action="store_true")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    a = ap.parse_args()

    sm_ = marked_tokens(Path(a.source).expanduser().read_text(encoding="utf-8"), "source")
    em_ = marked_tokens(Path(a.edition).expanduser().read_text(encoding="utf-8"), "edition")
    if a.start or a.end:
        lo = secs(a.start) if a.start else 0
        hi = secs(a.end) if a.end else float("inf")
        sm_ = [(w, m) for w, m in sm_ if m and lo <= secs(m) < hi]
    src, smark = [w for w, _ in sm_], [m for _, m in sm_]
    ed, emark = [w for w, _ in em_], [m for _, m in em_]
    ops = difflib.SequenceMatcher(None, src, ed, autojunk=False).get_opcodes()

    removals, additions, changed = [], [], []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "replace" and i2 - i1 <= 3 and j2 - j1 <= 3:
            changed.append((i1, i2, j1, j2))
            continue
        if tag in ("delete", "replace"):
            removals.append((i1, i2))
        if tag in ("insert", "replace"):
            additions.append((j1, j2, i1))

    # A move is the same words removed in one place and added in another. Long spans pair
    # anywhere; short ones (a one-word "No." moved after the question it answers) only nearby,
    # so a common word removed here and supplied there isn't mistaken for a move.
    moved_rem, moved_add = set(), set()
    for ai, (j1, j2, at) in enumerate(additions):
        for ri, (i1, i2) in enumerate(removals):
            if ri in moved_rem or [w for w in src[i1:i2] if w not in FILLER] != ed[j1:j2]:
                continue
            if i2 - i1 >= 3 or abs(i1 - at) <= MOVE_WINDOW:
                moved_rem.add(ri)
                moved_add.add(ai)
                break

    k = a.context
    counts = Counter()
    soft = Counter()
    content_lines, moved_lines = [], []
    for ri, (i1, i2) in enumerate(removals):
        span = src[i1:i2]
        if ri in moved_rem:
            counts["moved"] += 1
            moved_lines.append("  ↔ " + ctx(src, i1, i2, k, smark))
        elif all(w in FILLER for w in span):
            counts["filler"] += len(span)
        elif is_dup(src, i1, i2):
            counts["duplicate"] += 1
        elif (core := [w for w in span if w not in FILLER]) and len(core) <= 4 and all(w in SOFT for w in core):
            counts["soft"] += 1
            counts["filler"] += len(span) - len(core)
            soft[" ".join(core)] += 1
        else:
            counts["content"] += 1
            tags = [t for t, hit in (("NEGATION", is_neg(span)), ("NEAR-TWIN", near_twin(src, i1, i2))) if hit]
            flag = f"  {' '.join(tags)}" if tags else ""
            content_lines.append(f"  -{counts['content']:<3} " + ctx(src, i1, i2, k, smark, "−") + flag)

    add_lines = []
    for ai, (j1, j2, _) in enumerate(additions):
        if ai in moved_add:
            continue
        add_lines.append(f"  +{len(add_lines) + 1:<3} " + ctx(ed, j1, j2, k, emark, "+"))
    chg_lines = []
    for n, (i1, i2, j1, j2) in enumerate(changed, 1):
        where = smark[i1] if i1 < len(smark) and smark[i1] else (emark[j1] if j1 < len(emark) else None)
        flag = "  NEGATION" if is_neg(src[i1:i2]) != is_neg(ed[j1:j2]) else ""
        chg_lines.append(f"  ~{n:<3} ({where or '?'}) \"{' '.join(src[i1:i2])}\" → \"{' '.join(ed[j1:j2])}\"   "
                         f"…{' '.join(ed[max(0, j1 - k):j1])} _ {' '.join(ed[j2:j2 + k])}…{flag}")

    ratio = len(ed) / len(src) if src else 0
    print(f"source_words: {len(src)}   edition_words: {len(ed)}   ratio: {ratio:.2f}")
    print(f"added: {len(add_lines)}   changed: {len(changed)}   content removals: {counts['content']}   "
          f"moved: {counts['moved']}   soft: {counts['soft']}   filler words: {counts['filler']}   duplicates: {counts['duplicate']}")
    if len(ed) > len(src):
        print("WARNING: the edition is longer than the source — something was added.")
    if src and ratio < 0.6:
        print("WARNING: under 60% of the source — this reads like compression, not cleanup.")
    for title, lines in (("ADDED — reconcile each against the editorial note", add_lines),
                         ("CHANGED — each is a repair the note must disclose", chg_lines),
                         ("CONTENT REMOVALS — each needs a reason", content_lines),
                         ("MOVED", moved_lines)):
        if lines:
            print(f"\n{title}")
            print("\n".join(lines))
    if soft:
        print("\nSOFT (tally): " + ", ".join(f"{p} ×{n}" for p, n in soft.most_common(25 if not a.show_soft else None)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
