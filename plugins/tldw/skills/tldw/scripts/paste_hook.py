#!/usr/bin/env python3
"""UserPromptSubmit hook: a prompt that is essentially just YouTube video URL(s) runs /tldw.

Silent (no output, exit 0) for every other prompt. The gate: strip the URLs, and what's
left may only be filler/intent words ("summarize this please"). Any real content word
means the user is saying something else, so the hook stands down and the /tldw skill's
own description handles the natural-language case.
"""

import json
import re
import sys

URL_TOKEN_RE = re.compile(r"https?://\S+", re.IGNORECASE)
YT_VIDEO_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?\S*\bv=|shorts/|embed/|live/|v/)|youtu\.be/)[\w-]{11}",
    re.IGNORECASE,
)
ALLOWED = {
    "summarize", "summarise", "summary", "tldr", "tldw", "tl", "dr", "dw", "digest",
    "gist", "recap", "breakdown", "overview", "please", "pls", "plz", "thanks", "thx",
    "this", "that", "these", "those", "the", "a", "an", "video", "videos", "vid", "vids",
    "youtube", "yt", "watch", "can", "could", "would", "you", "u", "me", "my", "for",
    "give", "get", "gimme", "of", "what", "whats", "about", "on", "here", "hey", "hi",
    "hello", "do", "it", "go", "quick", "quickly", "key", "points", "main", "takeaways",
    "takeaway", "and", "to", "im", "curious", "pull", "up", "both", "all",
    "ratio", "as", "in",
}
MODES = {"themes", "argument", "timeline", "raw", "shorter", "deep", "deeper", "full"}  # passed through to the skill as args


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # never block a prompt on a parse failure
    prompt = (data.get("prompt") or "").strip()
    urls = [t.rstrip(".,);]>\"'") for t in URL_TOKEN_RE.findall(prompt) if YT_VIDEO_RE.search(t)]
    if not urls:
        return 0
    leftover = URL_TOKEN_RE.sub(" ", prompt)
    words = re.findall(r"[a-z]+|\d+:\d+|\d+", leftover.lower())
    modes = [w for w in words if w in MODES or re.fullmatch(r"\d+(:\d+)?", w)]
    if any(w not in ALLOWED and w not in modes for w in words):
        return 0

    args = " ".join(urls + modes)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": (
            "The user's message is essentially just YouTube video URL(s). Run the tldw skill "
            f"on them now without asking: Skill tool, skill \"tldw\", args \"{args}\" "
            "(if \"tldw\" doesn't resolve, use \"tldw:tldw\")."
        ),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
