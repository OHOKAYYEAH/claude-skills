#!/usr/bin/env python3
"""
extract_framework_health.py — the framework-health stage of /harness-audit.

Grades the WORKFLOW, not single skills, on two self-inspection signals defined in
references/framework-health.md: decisions held (signal 1) and people<->AI
realignment (signal 3). Stdlib only, no model tokens; the one judgment step (a
small-model labelling pass) happens between the two subcommands.

  extract  walk top-level session transcripts in a date window, write
           <out>/extract.json: every spec-check recap, re-freeze counts, and a
           deterministic per-month sample of AI-output -> next-human-turn pairs.
  score    read <out>/extract.json + <out>/labels.json ({id: class}), validate
           the labels, write <out>/framework_health.json (per-month numbers,
           pooled figures, small-n flags, citations by session-id prefix only).

The out dir defaults to system temp: extract.json holds raw transcript excerpts
and must never be committed (e.g. into a tracked audits dir).

Usage:
  extract_framework_health.py extract [--since D] [--until D | --days N]
        [--all-scopes] [--scope-dir DIR ...] [--exclude-session PREFIX ...]
        [--per-month N] [--out DIR]
  extract_framework_health.py score OUT_DIR
"""
import argparse, glob, json, os, re, sys, tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone

PAIR_CLASSES = ("accepted", "corrected_ai", "changed_ask", "rubber_stamp", "other")
RECAP_CLASSES = ("built_to_spec", "gaps", "divergences", "cant_verify")
MIN_N = 5          # below this a month reports counts, never a rate
EXCERPT = 600

DECISION_RE = re.compile(r"(?m)^Decision: (?!<)(.+)$")
BUILD_RE = re.compile(r"(?m)^(?:RED|Build): (?!<)")
REFREEZE_RE = re.compile(r"FROZEN SPEC — ([^\n]*)\n\s*ticket:([^\n]*)supersedes:\s*([^\n]+)")
SPEC_LINE_RE = re.compile(r"\*\*Spec:\*\*\s*([^\n]+)")
TICKET_RE = re.compile(r"\b(?!(?:UTF|SHA|ISO|HTTP|TLS|SSL|AES|RSA|RFC|CVE|IPV|MD|ES|AC|UTC|GMT|[CEMP][SD]T)-)[A-Z][A-Z0-9]+-\d+\b")
TICKET_KEY_RE = re.compile(r"^[a-z][a-z0-9]+-\d+(?: comment \d+)?$")
COMMENT_RE = re.compile(r"comment\s+#?(\d+)", re.I)
PATH_RE = re.compile(r"[\w./~-]+\.md\b")
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
STATUS_RE = re.compile(r"(?m)^\*\*Status:\*\*.*$")
# CLI-local commands (and the /rename hooks type) aren't replies; the real reply follows them.
LOCAL_COMMANDS = {"/rename", "/model", "/compact", "/clear", "/config", "/status", "/cost", "/context",
                  "/resume", "/login", "/logout", "/output-style", "/permissions", "/hooks", "/mcp",
                  "/memory", "/add-dir", "/statusline", "/vim", "/theme", "/export", "/doctor",
                  "/help", "/exit", "/usage", "/agents", "/ide", "/release-notes", "/effort", "/fast"}
# Earliest marker wins: "⚠️ needs your call. Everything is built to spec" is a ⚠️.
RECAP_MARKERS = (("✅", "built_to_spec"), ("🔧", "gaps"), ("⚠", "divergences"), ("🛑", "cant_verify"))


# ---------- record helpers -------------------------------------------------

def _ts(rec):
    try:
        return datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, ValueError):
        return None


def _content(rec):
    m = rec.get("message")
    return m.get("content") if isinstance(m, dict) else None


def _texts(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _tool_inputs(content):
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                yield from _strings(b.get("input"))


def human_turn(rec):
    """('human', text) | ('interrupt', None) | None for everything that isn't a person typing."""
    if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isCompactSummary") \
            or rec.get("isSidechain") or "toolUseResult" in rec:
        return None
    c = _content(rec)
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return None
    text = REMINDER_RE.sub("", _texts(c)).strip()
    if not text:
        return None
    if text.startswith("[Request interrupted by user"):
        return ("interrupt", None)
    if "<command-name>" in text:
        name = text.split("<command-name>", 1)[1].split("</command-name>", 1)[0].strip()
        if name in LOCAL_COMMANDS:
            return None
        args = ""
        if "<command-args>" in text:
            args = text.split("<command-args>", 1)[1].split("</command-args>", 1)[0].strip()
        return ("human", f"{name} {args}".strip())
    if text.startswith("<"):
        return None  # task notifications, local-command output, bash echoes
    return ("human", text)


def _status_at(text):
    m = STATUS_RE.search(text or "")
    return m.start() if m else 0


def recap_label(text):
    """The /spec-check Status line's emoji; with no Status line, the earliest emoji up top."""
    m = STATUS_RE.search(text or "")
    head = m.group(0) if m else (text or "")[:300]
    hits = [(head.find(m), cls) for m, cls in RECAP_MARKERS if m in head]
    return min(hits)[1] if hits else None


def _spec_ticket(result):
    m = SPEC_LINE_RE.search(result or "")
    return TICKET_RE.search(m.group(1).replace("`", "")) if m else None


def recap_key(result, session):
    """Spec-line ticket (+ comment id), else spec-file path tail, else body ticket, else session.

    Model-written Spec lines vary run to run ("PROJ-4 description" vs "the PROJ-4 AC"), so
    free text would split one spec into several first passes."""
    m = SPEC_LINE_RE.search(result or "")
    line = m.group(1).replace("`", "") if m else ""
    t = TICKET_RE.search(line)
    if t:
        c = COMMENT_RE.search(line)
        return t.group(0).lower() + (f" comment {c.group(1)}" if c else "")
    path = PATH_RE.search(line)
    if path:  # parent dir too: spec.md / plan.md are generic names
        return "/".join(path.group(0).lower().split("/")[-2:])
    t = TICKET_RE.search(result or "")
    return t.group(0).lower() if t else f"session:{session[:8]}"


# ---------- extract --------------------------------------------------------

def _window(since, until):
    lo = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    hi = datetime.fromisoformat(until).replace(tzinfo=timezone.utc) + timedelta(days=1)
    return lo, hi


def _session_files(scope_dirs):
    files = set()
    for d in scope_dirs:
        files.update(glob.glob(os.path.join(d, "projects", "**", "*.jsonl"), recursive=True))
    # Fork transcripts have no human turns, and their recaps reappear as tool results in the parent.
    return sorted(f for f in files if f"{os.sep}subagents{os.sep}" not in f)


def extract(scope_dirs, since, until, exclude_sessions=()):
    lo, hi = _window(since, until)
    exclude_sessions = [p for p in exclude_sessions if p.strip()]  # "" would exclude everything
    pairs, recaps = [], []
    freeze_hits = {}  # header -> (earliest ts, built by then): an echo later never re-counts
    credited = set()  # AI uuids whose Decision lines a reply already consumed (forks replay them)
    seen = set()
    prior_keys = set()
    bad_lines = 0

    def keep(rec, ts):
        sess = rec.get("sessionId") or ""
        return ts and lo <= ts < hi and not any(sess.startswith(p) for p in exclude_sessions)

    for f in _session_files(scope_dirs):
        recs = []
        try:
            old = os.path.getmtime(f) < lo.timestamp()
            with open(f, encoding="utf-8", errors="replace") as fh:
                for l in fh:
                    # A pre-window file only matters for its spec-checks (prior_keys) and freezes.
                    if not l.strip() or (old and '"spec-check"' not in l and "FROZEN SPEC" not in l):
                        continue
                    try:
                        recs.append(json.loads(l))
                    except json.JSONDecodeError:
                        bad_lines += 1  # a live session's half-written last line
        except OSError:
            continue

        # Pair over the file's full sequence, replays included, then dedup by uuid:
        # a resumed session's first new reply answers a replayed AI message.
        last_ai = None
        decisions = []
        interrupted = built = False
        for rec in recs:
            ts, uuid = _ts(rec), rec.get("uuid")
            if rec.get("type") == "assistant" and not rec.get("isSidechain"):
                content = _content(rec)
                text = _texts(content).strip()
                if text:
                    last_ai = text
                    decisions += [(uuid, "Decision: " + d) for d in DECISION_RE.findall(text)]
                sess = rec.get("sessionId") or ""
                for blob in [text, *_tool_inputs(content)]:
                    for header, ticket, sup in REFREEZE_RE.findall(blob):
                        # Keyed on the header, not the uuid: /spec shows the artifact AND writes it by tool.
                        key = (header.strip(), ticket.strip(), sup.strip())
                        if sup.strip()[:1] in ("—", "-", "<") or not ts \
                                or any(sess.startswith(p) for p in exclude_sessions):
                            continue
                        if key not in freeze_hits or ts < freeze_hits[key][0]:
                            freeze_hits[key] = (ts, built)
                if text and BUILD_RE.search(text):
                    built = True
                continue

            tur = rec.get("toolUseResult")
            if isinstance(tur, dict) and tur.get("commandName") == "spec-check":
                sess = rec.get("sessionId") or ""
                if ts and ts < lo and not any(sess.startswith(p) for p in exclude_sessions):
                    result = str(tur.get("result") or _texts(_content(rec)))
                    if recap_label(result) != "cant_verify":
                        prior_keys.add(recap_key(result, sess))
                elif uuid not in seen and keep(rec, ts):
                    seen.add(uuid)
                    result = str(tur.get("result") or _texts(_content(rec)))
                    recaps.append({"id": uuid, "month": f"{ts:%Y-%m}", "session": sess,
                                   "ts": ts.isoformat(), "key": recap_key(result, sess),
                                   "citable": _spec_ticket(result) is not None,
                                   "label": recap_label(result),
                                   "excerpt": result[_status_at(result):][:EXCERPT]})
                continue

            if old:
                continue
            turn = human_turn(rec)
            if turn is None:
                continue
            if turn[0] == "interrupt":
                interrupted = True
                continue
            fresh = [d for u, d in decisions if u not in credited]
            credited.update(u for u, _ in decisions)
            if last_ai is not None and uuid not in seen and keep(rec, ts):
                seen.add(uuid)
                pairs.append({"id": uuid, "month": f"{ts:%Y-%m}", "session": rec.get("sessionId") or "",
                              "ts": ts.isoformat(), "ai_tail": last_ai[-EXCERPT:],
                              "human": turn[1][:EXCERPT], "interrupted": interrupted,
                              "decision": "\n".join(fresh) or None,
                              "decision_count": len(fresh), "label": None})
            last_ai = None
            decisions = []
            interrupted = False

    refreezes = defaultdict(lambda: {"after_build": 0, "before_build": 0})
    for ts, was_built in freeze_hits.values():
        if lo <= ts < hi:
            refreezes[f"{ts:%Y-%m}"]["after_build" if was_built else "before_build"] += 1
    pairs.sort(key=lambda p: (p["ts"], p["id"]))
    recaps.sort(key=lambda r: (r["ts"], r["id"]))
    return {"pairs": pairs, "recaps": recaps, "refreezes": dict(refreezes),
            "prior_keys": sorted(prior_keys),
            "meta": {"since": since, "until": until, "scope_dirs": list(scope_dirs),
                     "exclude_sessions": list(exclude_sessions), "bad_lines": bad_lines}}


def sample_pairs(pairs, per_month):
    """A stride sample of each month (in_sample, the signal-3 population) plus every
    other Decision pair (signal 1b needs all of them; they'd bias signal 3)."""
    by_month = defaultdict(list)
    for p in pairs:
        by_month[p["month"]].append(p)
    out = []
    for month in sorted(by_month):
        ps = sorted(by_month[month], key=lambda p: (p["ts"], p["id"]))
        idx = range(len(ps))
        if len(ps) > per_month:
            stride = len(ps) / per_month
            idx = [int(i * stride) for i in range(per_month)]
        picked = set(idx)
        out += [{**p, "in_sample": i in picked} for i, p in enumerate(ps)
                if i in picked or p.get("decision")]
    return out


def write_extract(out, data):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "extract.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)


# ---------- score ----------------------------------------------------------

def _rates(counts, n):
    return {k: round(v / n, 2) for k, v in counts.items()} if n >= MIN_N else None


def _partial(month, since, until):
    if not (since and until):
        return None
    first = datetime.fromisoformat(month + "-01").date()
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return since > first.isoformat() or until < last.isoformat()


def _ref(recap):
    """Only a Spec-line ticket is cited; a body token may be a customer or account code."""
    key = recap["key"]
    ok = recap.get("citable") and TICKET_KEY_RE.match(key)
    return key.split()[0].upper() if ok else recap["session"][:8]


def _validate(items, labels, classes, kind):
    missing = [i["id"] for i in items if i.get("label") is None and i["id"] not in labels]
    bad = {i["id"]: labels[i["id"]] for i in items
           if i.get("label") is None and i["id"] in labels and labels[i["id"]] not in classes}
    if missing or bad:
        raise ValueError(f"{kind}: {len(missing)} unlabelled ids (e.g. {missing[:3]}), "
                         f"{len(bad)} labels outside {classes} (e.g. {list(bad.items())[:3]})")


def score(out):
    with open(os.path.join(out, "extract.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    with open(os.path.join(out, "labels.json"), encoding="utf-8") as fh:
        labels = json.load(fh)
    pairs, recaps = data["pairs"], data["recaps"]
    _validate(pairs, labels, PAIR_CLASSES, "pairs")
    _validate(recaps, labels, RECAP_CLASSES, "recaps")
    for item in pairs + recaps:
        item["label"] = item.get("label") or labels[item["id"]]

    # Signal 3 — realignment, over the stride sample only.
    meta = data.get("meta", {})
    totals = meta.get("pairs_total_by_month", {})
    sampled = [p for p in pairs if p.get("in_sample", True)]
    by_month = {}
    for month in sorted({p["month"] for p in sampled}):
        ps = [p for p in sampled if p["month"] == month]
        counts = {c: sum(p["label"] == c for p in ps) for c in PAIR_CLASSES}
        by_month[month] = {"n": len(ps), "total": totals.get(month), "counts": counts,
                           "rates": _rates(counts, len(ps)),
                           "interrupted": sum(p["interrupted"] for p in ps),
                           "insufficient": len(ps) < MIN_N,
                           "partial": _partial(month, meta.get("since"), meta.get("until"))}
    pooled = {c: sum(p["label"] == c for p in sampled) for c in PAIR_CLASSES}
    citations = []
    for cls in ("corrected_ai", "rubber_stamp", "changed_ask"):
        hit = next((p for p in sampled if p["label"] == cls), None)
        if hit:
            citations.append({"class": cls, "month": hit["month"], "session": hit["session"][:8]})

    # Signal 1a — first-pass spec-check outcome, keyed on the spec so a rerun after a handoff isn't a new first pass.
    measured = [r for r in recaps if r["label"] != "cant_verify"]
    # A freeze comment is its own spec; a check naming only the ticket reruns any earlier one.
    seen_keys = set(data.get("prior_keys", ()))
    seen_keys |= {k.split()[0] for k in seen_keys}
    first = {}
    for r in sorted(measured, key=lambda r: (r["ts"], r["id"])):
        if r["key"] not in seen_keys:
            first[r["key"]] = r
        seen_keys |= {r["key"], r["key"].split()[0]}
    fp = list(first.values())
    fp_counts = {c: sum(r["label"] == c for r in fp) for c in RECAP_CLASSES}
    fp_counts["cant_verify"] = len(recaps) - len(measured)
    fp_n = len(fp)
    fp_by_month = {}
    for r in fp:
        fp_by_month.setdefault(r["month"], {c: 0 for c in RECAP_CLASSES})[r["label"]] += 1

    # Signal 1b — a Decision line held unless the reply corrected it.
    dec = [p for p in pairs if p.get("decision")]
    dec_by_month = {}
    for p in dec:
        k = p.get("decision_count") or 1
        m = dec_by_month.setdefault(p["month"], {"n": 0, "held": 0})
        m["n"] += k
        m["held"] += k if p["label"] != "corrected_ai" else 0
    dec_n = sum(m["n"] for m in dec_by_month.values())
    held = sum(m["held"] for m in dec_by_month.values())

    result = {
        "meta": {k: v for k, v in meta.items() if k not in ("scope_dirs", "exclude_sessions")},
        "realignment": {"by_month": by_month, "pooled": {"n": len(sampled), "counts": pooled,
                                                         "rates": _rates(pooled, len(sampled))},
                        "citations": citations},
        "decisions_held": {
            "spec_check_first_pass": {"n": fp_n, "counts": fp_counts, "reruns": len(measured) - len(fp),
                                      "by_month": fp_by_month, "pooled": True,
                                      "insufficient": fp_n < MIN_N,
                                      "citations": [{"ref": _ref(r), "month": r["month"],
                                                     "label": r["label"]} for r in fp[:3]]},
            "decision_lines": {"n": dec_n, "held": held, "insufficient": dec_n < MIN_N,
                               "by_month": dec_by_month, "pooled": True},
            "refreezes": data.get("refreezes", {}),
        },
    }
    with open(os.path.join(out, "framework_health.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    return result


# ---------- CLI ------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("--since")
    ex.add_argument("--until")
    ex.add_argument("--days", type=int, default=30)
    ex.add_argument("--all-scopes", action="store_true")
    ex.add_argument("--scope-dir", action="append", default=[])
    ex.add_argument("--exclude-session", action="append", default=[])
    ex.add_argument("--per-month", type=int, default=60)
    ex.add_argument("--out")
    sc = sub.add_parser("score")
    sc.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "extract" and (a.days < 1 or a.per_month < 1):
        ap.error("--days and --per-month must be >= 1")

    if a.cmd == "score":
        print(json.dumps(score(a.out)["decisions_held"], indent=1, ensure_ascii=False))
        print(os.path.join(a.out, "framework_health.json"))
        return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_skill_usage import discover_scope_dirs
    today = datetime.now(timezone.utc).date()
    until = a.until or today.isoformat()
    since = a.since or (datetime.fromisoformat(until).date() - timedelta(days=a.days - 1)).isoformat()
    if since > until:
        ap.error(f"--since {since} is after --until {until}")
    scopes = discover_scope_dirs(a.all_scopes, a.scope_dir)
    data = extract(scopes, since, until, a.exclude_session)
    totals = defaultdict(int)
    for p in data["pairs"]:
        totals[p["month"]] += 1
    data["meta"]["pairs_total_by_month"] = dict(totals)
    data["pairs"] = sample_pairs(data["pairs"], a.per_month)
    out = a.out or tempfile.mkdtemp(prefix=f"harness-health-{since}_{until}-")  # 0700, unguessable
    write_extract(out, data)
    need = sum(p["label"] is None for p in data["pairs"]) + sum(r["label"] is None for r in data["recaps"])
    print(f"[health] {since}..{until}: pairs/month {dict(totals)}; sampled {len(data['pairs'])}; "
          f"recaps {len(data['recaps'])}; refreezes {data['refreezes']}; "
          f"unparseable lines {data['meta']['bad_lines']}; to label: {need}")
    print(out)  # last line = out dir


if __name__ == "__main__":
    main()
