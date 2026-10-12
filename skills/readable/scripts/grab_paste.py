#!/usr/bin/env python3
"""Save a block the user pasted into this Claude Code session to a file, without the model retyping it.

Usage: grab_paste.py --out DIR [--match TEXT] [--name source.txt]
       grab_paste.py --list

Claude Code stores each paste verbatim in the session log, wrapped in
<pasted_content id="X"> … </pasted_content id="X">. This finds the current session's log
($CLAUDE_CODE_SESSION_ID under $CLAUDE_CONFIG_DIR/projects/*/), picks the newest paste (or
the newest one containing --match), writes it to DIR/NAME, and prints JSON:
{"path", "words", "lines", "paste_id", "first_line"}. On failure it prints {"error", "error_code"}
and exits 1; the caller then writes the source itself.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PASTE_RE = re.compile(r'<pasted_content id="([^"]+)">\n?(.*?)\n?</pasted_content id="\1">', re.S)


def session_log() -> Path | None:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        return None
    roots = [Path(os.environ["CLAUDE_CONFIG_DIR"])] if os.environ.get("CLAUDE_CONFIG_DIR") else []
    roots.append(Path.home() / ".claude")
    for root in roots:
        hits = sorted((root / "projects").glob(f"*/{sid}.jsonl"), key=lambda p: p.stat().st_mtime)
        if hits:
            return hits[-1]
    return None


def user_texts(log: Path):
    for line in log.open(encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "user":
            continue
        c = d.get("message", {}).get("content")
        if isinstance(c, str):
            yield c
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    yield b.get("text", "")


def pastes(log: Path) -> list[tuple[str, str]]:
    out = []
    for text in user_texts(log):
        out.extend(PASTE_RE.findall(text))
    return out


def fail(code: str, msg: str) -> int:
    print(json.dumps({"error": msg, "error_code": code}))
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--match")
    ap.add_argument("--name", default="source.txt")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    log = session_log()
    if not log:
        return fail("no_session", "Could not find this session's log (CLAUDE_CODE_SESSION_ID unset or no matching .jsonl).")
    found = pastes(log)
    if a.list:
        print(json.dumps([{"paste_id": pid, "words": len(body.split()), "first_line": body.strip().splitlines()[0][:120] if body.strip() else ""}
                          for pid, body in found], indent=2))
        return 0
    if not a.out:
        return fail("usage", "--out DIR is required unless --list.")
    if a.match:
        found = [p for p in found if a.match in p[1]]
    if not found:
        return fail("no_paste", "No pasted block found in this session" + (f" containing {a.match!r}" if a.match else "") + ". Short pastes arrive untagged; write the source yourself.")

    pid, body = found[-1]
    dest = Path(a.out).expanduser() / a.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body.rstrip("\n") + "\n", encoding="utf-8")
    lines = body.strip().splitlines()
    print(json.dumps({"path": str(dest), "words": len(body.split()), "lines": len(lines),
                      "paste_id": pid, "first_line": lines[0][:120] if lines else ""}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
