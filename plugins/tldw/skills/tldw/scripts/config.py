#!/usr/bin/env python3
"""Per-user /tldw defaults: shape and compression ratio.

Usage: config.py show              print the resolved defaults as JSON
       config.py set shape themes  save a default (shape: themes|argument|timeline)
       config.py set ratio 15      save a default ratio (15 means 15:1)
       config.py reset             delete the config file

Resolution: built-in (themes, 10) < config file < $TLDW_SHAPE / $TLDW_RATIO.
The config file is $TLDW_CONFIG, else ~/.config/tldw/config.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SHAPES = ("themes", "argument", "timeline")
BUILTIN = {"shape": "themes", "ratio": 10}


def config_path() -> Path:
    return Path(os.environ.get("TLDW_CONFIG") or Path.home() / ".config" / "tldw" / "config.json")


def _validate(key: str, value) -> object:
    if key == "shape":
        v = str(value).lower()
        if v not in SHAPES:
            raise ValueError(f"shape must be one of {', '.join(SHAPES)}")
        return v
    if key == "ratio":
        r = float(str(value).split(":")[0])
        if not 2 <= r <= 50:
            raise ValueError("ratio must be between 2 and 50 (e.g. 5, 10, 15)")
        return int(r) if r.is_integer() else r
    raise ValueError("key must be shape or ratio")


def resolve() -> dict:
    out, source = dict(BUILTIN), {"shape": "built-in", "ratio": "built-in"}
    p = config_path()
    try:
        saved = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    for key, env in (("shape", "TLDW_SHAPE"), ("ratio", "TLDW_RATIO")):
        for label, value in ((str(p), saved.get(key)), (f"${env}", os.environ.get(env))):
            if value is None:
                continue
            try:
                out[key], source[key] = _validate(key, value), label
            except ValueError:
                pass  # a bad value falls back to the level below instead of breaking the run
    return {**out, "source": source}


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "show"
    p = config_path()
    if cmd == "set" and len(argv) == 3:
        try:
            value = _validate(argv[1], argv[2])
        except ValueError as e:
            print(f"config.py: {e}", file=sys.stderr)
            return 2
        try:
            saved = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        saved[argv[1]] = value
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    elif cmd == "reset":
        p.unlink(missing_ok=True)
    elif cmd != "show":
        print(__doc__, file=sys.stderr)
        return 2
    print(json.dumps({**resolve(), "config_file": str(p)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
