#!/usr/bin/env python3
"""Count the words a reader actually reads, skipping transcript and file structure.

Usage: count.py FILE [--kind source|summary|edition]

  source   caption timing lines (VTT/SRT/Zoom "00:01 --> 00:04"), SRT cue numbers, VTT cue
           IDs (the line right above a timing line) and <v Name>/<c> tags, WEBVTT/NOTE headers,
           leading "[12:34 …]" stamps, and leading "Speaker Name:" labels are structure, not
           speech. Labels are stripped only when most lines carry one, so ordinary prose with a
           "Note:" line is untouched.
  summary  the header above the first `---` line is skipped (the /distill save format).
  edition  header skipped, `## Editorial note` onward skipped, `[..]` anchors/cues and
           `**Name:**` turn labels stripped (the /readable save format).

fixtures/teams.vtt is a Teams caption sample that must count 10 words; re-run it after changing
the source rules. Prints {"words": N, "kind": K}. The /readable skill carries an identical copy
(its drift.py imports `marked_tokens()`); keep the two in sync so both normalize text the same way.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CUE_TIME = re.compile(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)(?:[.,]\d+)?\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?.*$")
CUE_NUM = re.compile(r"^\s*\d+\s*$")
LEAD_STAMP = re.compile(r"^\s*\[(\d{1,2}:\d{2}(?::\d{2})?)[^\]\n]*\]\s*")
LABEL = re.compile(r"^\s*(?:\*\*)?[A-Z0-9][\w.'’()-]*(?: [\w.'’()&-]+){0,5}:(?:\*\*)?\s")
BOLD_LABEL = re.compile(r"\*\*[^*\n]{1,60}?:\*\*")
BRACKET = re.compile(r"\[([^\]\n]{0,80})\]")
TIME = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
WORD = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")
VTT_TAG = re.compile(r"</?(?:v|c|i|b|u|lang|ruby|rt)\b[^>]*>|<\d{1,2}:\d{2}(?::\d{2})?[.,]\d+>")


def _words(s: str) -> list[str]:
    return WORD.findall(s.lower().replace("’", "'"))


def _after_header(text: str) -> list[str]:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            return lines[i + 1:]
    return lines


def marked_tokens(text: str, kind: str) -> list[tuple[str, str | None]]:
    """Each reader-visible word with the latest time marker seen before it (or None)."""
    out: list[tuple[str, str | None]] = []
    mark = None
    if kind == "source":
        raw = text.splitlines()
        cue_ids = {i - 1 for i, ln in enumerate(raw)
                   if CUE_TIME.match(ln) and i > 0 and raw[i - 1].strip() and not CUE_TIME.match(raw[i - 1])}
        lines = [VTT_TAG.sub("", ln) for i, ln in enumerate(raw)
                 if i not in cue_ids and not CUE_NUM.match(ln)
                 and not re.match(r"^(WEBVTT|NOTE|STYLE|Kind:|Language:)\b", ln.strip())]
        spoken = [ln for ln in lines if ln.strip() and not CUE_TIME.match(ln)]
        labeled = bool(spoken) and sum(bool(LABEL.match(ln)) for ln in spoken) / len(spoken) > 0.5
        for ln in lines:
            m = CUE_TIME.match(ln)
            if m:
                mark = m.group(1)
                continue
            m = LEAD_STAMP.match(ln)
            if m:
                mark, ln = m.group(1), ln[m.end():]
            if labeled:
                ln = LABEL.sub("", ln, count=1)
            out += [(w, mark) for w in _words(ln)]
        return out
    lines = _after_header(text)
    if kind == "edition":
        body = "\n".join(lines)
        body = re.split(r"(?m)^##\s+Editorial note\b", body)[0]
        lines = body.splitlines()
    for ln in lines:
        if kind == "edition":
            ln = BOLD_LABEL.sub(" ", ln)
            pieces = BRACKET.split(ln)  # odd indexes are bracket contents
            for i, piece in enumerate(pieces):
                if i % 2:
                    if TIME.match(piece.strip()):
                        mark = piece.strip()
                    continue
                out += [(w, mark) for w in _words(piece)]
        else:
            out += [(w, None) for w in _words(ln)]
    return out


def tokens(text: str, kind: str) -> list[str]:
    return [w for w, _ in marked_tokens(text, kind)]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    kind = argv[argv.index("--kind") + 1] if "--kind" in argv else "source"
    if kind not in ("source", "summary", "edition"):
        print("count.py: --kind must be source, summary, or edition", file=sys.stderr)
        return 2
    text = Path(argv[0]).expanduser().read_text(encoding="utf-8")
    print(json.dumps({"words": len(tokens(text, kind)), "kind": kind}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
