#!/usr/bin/env python3
"""Fetch YouTube transcripts for /tldw and save them to disk.

Usage: fetch.py URL_OR_ID [URL_OR_ID ...] [--out DIR] [--lang en,de] [--refresh]

Prints one JSON object on stdout: {"videos": [...]}, one entry per input, each with
"status" ("ok" or "error"), the saved "dir", metadata, and on failure an "error_code":
  blocked        YouTube refused the request (common from cloud/VPN IPs)
  no_captions    the video has no transcript in any language
  age_restricted YouTube requires a signed-in session for this video
  unavailable    private, deleted, members-only, or not a valid video id
  setup          the Python dependency could not be installed
  network        anything else (timeouts, DNS, unexpected responses)

Needs only python3: on first run it installs youtube-transcript-api into its own
venv (~/.cache/tldw/venv, or $TLDW_VENV) and re-runs itself there. If yt-dlp is on
PATH, it is tried as a fallback when the primary fetch is blocked or finds nothing.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

DEP_SPEC = "youtube-transcript-api==1.2.4"  # exact pin: installed unprompted on first run
BLOCK_SECONDS = 45  # timestamped transcript is grouped into ~45s paragraphs
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _err(*a):
    print(*a, file=sys.stderr)


# ---------------------------------------------------------------- dependency bootstrap

def _ensure_dependency(argv):
    """Import the transcript library, installing it into a private venv if missing."""
    try:
        import youtube_transcript_api  # noqa: F401
        return None
    except ImportError:
        pass
    if os.environ.get("TLDW_BOOTSTRAPPED"):
        return "the venv exists but youtube-transcript-api still won't import"

    venv = Path(os.environ.get("TLDW_VENV") or Path.home() / ".cache" / "tldw" / "venv")
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        _err(f"tldw: first run, installing {DEP_SPEC} into {venv} ...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", DEP_SPEC], check=True)
        except (subprocess.CalledProcessError, OSError) as e:
            shutil.rmtree(venv, ignore_errors=True)  # a half-built venv would mask the retry
            return (f"could not build the venv ({e}). Install python3-venv, or run: "
                    f"python3 -m pip install --user '{DEP_SPEC}'")
    os.environ["TLDW_BOOTSTRAPPED"] = "1"
    os.execv(str(py), [str(py), os.path.abspath(__file__), *argv])


# ---------------------------------------------------------------- ids, names, metadata

def extract_video_id(s: str) -> str | None:
    s = s.strip().rstrip(".,);]>\"'")
    if _ID_RE.match(s):
        return s
    p = urllib.parse.urlparse(s)
    host = (p.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        cand = p.path.lstrip("/").split("/")[0]
        return cand if _ID_RE.match(cand) else None
    if host in {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}:
        v = urllib.parse.parse_qs(p.query).get("v", [""])[0]
        if _ID_RE.match(v):
            return v
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live", "v"} and _ID_RE.match(parts[1]):
            return parts[1]
    return None


def parse_start_seconds(s: str) -> int | None:
    """The t= offset a pasted link carries (t=754, t=12m34s, t=1h2m3s), if any."""
    t = urllib.parse.parse_qs(urllib.parse.urlparse(s.strip()).query).get("t", [""])[0]
    if t.isdigit():
        return int(t)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?", t)
    if t and m and any(m.groups()):
        h, mi, se = (int(x or 0) for x in m.groups())
        return h * 3600 + mi * 60 + se
    return None


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len].rstrip("-") or "video"


def fetch_metadata(video_id: str) -> dict:
    """Title + channel from YouTube's public oembed endpoint; degrades to the id."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    meta = {"video_id": video_id, "url": url, "title": video_id, "author": None}
    try:
        q = urllib.parse.urlencode({"url": url, "format": "json"})
        req = urllib.request.Request(f"https://www.youtube.com/oembed?{q}",
                                     headers={"User-Agent": "tldw"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        meta["title"] = data.get("title") or video_id
        meta["author"] = data.get("author_name")
    except Exception:
        pass
    return meta


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def render(snippets: list[dict]) -> tuple[str, str]:
    """(plain text, timestamped text grouped into ~BLOCK_SECONDS paragraphs)."""
    plain = textwrap.fill(_clean(" ".join(s["text"] for s in snippets)), width=100)  # Read pages by line
    blocks, cur, cur_start = [], [], None
    for s in snippets:
        if cur_start is None:
            cur_start = s["start"]
        cur.append(s["text"])
        if s["start"] - cur_start >= BLOCK_SECONDS:
            blocks.append(f"[{fmt_ts(cur_start)} t={int(cur_start)}] {_clean(' '.join(cur))}")
            cur, cur_start = [], None
    if cur:
        blocks.append(f"[{fmt_ts(cur_start)} t={int(cur_start)}] {_clean(' '.join(cur))}")
    return plain, "\n\n".join(blocks)


# ---------------------------------------------------------------- transcript sources

class FetchError(Exception):
    def __init__(self, code: str, message: str, ip_blocked: bool = False):
        super().__init__(message)
        self.code = code
        self.ip_blocked = ip_blocked


FALLBACK_CODES = {"blocked", "no_captions", "network"}


def fetch_primary(video_id: str, langs: list[str]) -> dict:
    import youtube_transcript_api as yta

    try:
        tlist = yta.YouTubeTranscriptApi().list(video_id)
        translated = False
        try:
            t = tlist.find_transcript(langs)
        except yta.NoTranscriptFound:
            t = None
            for cand in tlist:
                if cand.is_translatable:
                    try:
                        t, translated = cand.translate(langs[0]), True
                        break
                    except Exception:
                        continue
            t = t or next(iter(tlist), None)
        if t is None:
            raise FetchError("no_captions", "the video has no transcript in any language")
        raw = t.fetch().to_raw_data()
    except FetchError:
        raise
    except yta.RequestBlocked as e:  # includes IpBlocked
        raise FetchError("blocked", f"YouTube blocked the transcript request ({type(e).__name__})",
                         ip_blocked=True)
    except yta.PoTokenRequired as e:
        raise FetchError("blocked", f"YouTube blocked the transcript request ({type(e).__name__})")
    except (yta.TranscriptsDisabled, yta.NoTranscriptFound):
        raise FetchError("no_captions", "captions are disabled or missing for this video")
    except yta.AgeRestricted:
        raise FetchError("age_restricted", "age-restricted: YouTube requires a signed-in session")
    except (yta.VideoUnavailable, yta.VideoUnplayable, yta.InvalidVideoId) as e:
        raise FetchError("unavailable", f"video unavailable ({type(e).__name__})")
    except Exception as e:
        raise FetchError("network", f"{type(e).__name__}: {e}")

    snippets = [{"text": s.get("text") or "", "start": float(s.get("start") or 0)} for s in raw]
    return {
        "snippets": snippets,
        "source": "youtube-transcript-api",
        "language": getattr(t, "language", "") or "",
        "language_code": getattr(t, "language_code", "") or "",
        "auto_generated": bool(getattr(t, "is_generated", False)),
        "translated": translated,
    }


def fetch_ytdlp(video_id: str, langs: list[str]) -> dict:
    exe = shutil.which("yt-dlp")
    if not exe:
        raise FetchError("unavailable", "yt-dlp is not installed")
    sub_langs = f"{langs[0]}.*"  # each extra language is another request toward a 429
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [exe, "--skip-download", "--write-subs", "--write-auto-subs",
             "--sub-langs", sub_langs, "--sub-format", "json3", "--no-warnings",
             "-o", f"{tmp}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=180,
        )
        files = sorted(glob.glob(f"{tmp}/*.json3"))
        if not files:
            out = (proc.stderr or proc.stdout).strip()
            detail = out.splitlines()[-1] if out else "no subtitles"
            code = "blocked" if re.search(r"429|Sign in to confirm|bot", out) else "no_captions"
            raise FetchError(code, f"yt-dlp found no subtitles ({detail})")
        data = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    snippets = []
    for ev in data.get("events", []):
        text = "".join(seg.get("utf8", "") for seg in ev.get("segs", []) or [])
        if text.strip():
            snippets.append({"text": text, "start": ev.get("tStartMs", 0) / 1000})
    if not snippets:
        raise FetchError("no_captions", "yt-dlp subtitles were empty")
    code = Path(files[0]).suffixes[-2].lstrip(".") if len(Path(files[0]).suffixes) > 1 else ""
    return {"snippets": snippets, "source": "yt-dlp", "language": code, "language_code": code,
            "auto_generated": None, "translated": False}


# ---------------------------------------------------------------- per-video flow

def lang_suffix(langs: list[str]) -> str:
    """English digests keep the plain folder name; others get their own, e.g. __ID.de."""
    return "" if langs[0] == "en" else f".{langs[0]}"


def find_existing(out_root: Path, video_id: str, langs: list[str]) -> Path | None:
    hits = sorted(out_root.glob(f"*__{video_id}{lang_suffix(langs)}/transcript.timestamped.txt"))
    return hits[-1].parent if hits else None


def process(arg: str, out_root: Path, langs: list[str], refresh: bool) -> dict:
    video_id = extract_video_id(arg)
    if not video_id:
        return {"input": arg, "status": "error", "error_code": "unavailable",
                "error": "not a YouTube video URL or 11-character video id"}
    start = parse_start_seconds(arg)

    existing = None if refresh else find_existing(out_root, video_id, langs)
    if existing:
        meta = json.loads((existing / "metadata.json").read_text(encoding="utf-8"))
        return {"input": arg, "status": "ok", "reused": True, "dir": str(existing),
                "saved": sorted(p.name for p in existing.glob("summary.*.md")),
                "start_seconds": start, **meta}

    meta = fetch_metadata(video_id)
    fallback_note = None
    try:
        got = fetch_primary(video_id, langs)
    except FetchError as e:
        # Retrying a flagged IP through yt-dlp only adds hits and can extend the block.
        if e.code not in FALLBACK_CODES or e.ip_blocked or not shutil.which("yt-dlp"):
            return {"input": arg, "status": "error", "error_code": e.code, "error": str(e),
                    "ip_blocked": e.ip_blocked, **meta}
        try:
            got = fetch_ytdlp(video_id, langs)
            fallback_note = f"primary fetch failed ({e.code}); used yt-dlp"
        except FetchError as e2:
            return {"input": arg, "status": "error", "error_code": e.code,
                    "error": f"{e}; yt-dlp fallback also failed: {e2}", **meta}
        except Exception as e2:
            return {"input": arg, "status": "error", "error_code": e.code,
                    "error": f"{e}; yt-dlp fallback crashed: {type(e2).__name__}: {e2}", **meta}

    plain, stamped = render(got.pop("snippets"))
    meta.update(got, fetched=date.today().isoformat(), fallback=fallback_note,
                requested_lang=langs[0], words=len(plain.split()))
    dest = out_root / f"{date.today().isoformat()}_{slugify(meta['title'])}__{video_id}{lang_suffix(langs)}"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "transcript.txt").write_text(plain + "\n", encoding="utf-8")
    (dest / "transcript.timestamped.txt").write_text(stamped + "\n", encoding="utf-8")
    (dest / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8")
    return {"input": arg, "status": "ok", "reused": False, "dir": str(dest),
            "saved": [], "start_seconds": start, **meta}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="fetch.py", description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="+", help="YouTube URLs or 11-char video ids")
    ap.add_argument("--out", default=os.environ.get("TLDW_DIR") or str(Path.home() / "tldw"))
    ap.add_argument("--lang", default="en", help="preferred language codes, comma-separated")
    ap.add_argument("--refresh", action="store_true", help="re-fetch even if already saved")
    a = ap.parse_args(argv)

    setup_error = _ensure_dependency(argv)
    if setup_error:
        print(json.dumps({"videos": [{"input": i, "status": "error", "error_code": "setup",
                                      "error": setup_error} for i in a.inputs]}, indent=2))
        return 1

    langs = [l.strip() for l in a.lang.split(",") if l.strip()] or ["en"]
    if "en" in langs:
        langs += [v for v in ("en-US", "en-GB") if v not in langs]
    out_root = Path(os.path.expanduser(a.out))
    videos = []
    for i in a.inputs:
        if videos and videos[-1].get("ip_blocked"):
            videos.append({"input": i, "status": "error", "error_code": "blocked", "ip_blocked": True,
                           "error": "skipped: an earlier video in this run hit an IP block"})
            continue
        if videos and not videos[-1].get("reused"):
            time.sleep(3)  # back-to-back transcript requests are what trip YouTube's IP block
        videos.append(process(i, out_root, langs, a.refresh))
    from config import resolve  # sibling script; stdlib only
    print(json.dumps({"defaults": resolve(), "videos": videos}, indent=2, ensure_ascii=False))
    return 0 if any(v["status"] == "ok" for v in videos) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
