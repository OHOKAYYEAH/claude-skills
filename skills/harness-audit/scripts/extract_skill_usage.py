#!/usr/bin/env python3
"""
extract_skill_usage.py — mechanical stage of /harness-audit.

Walks Claude Code JSONL session transcripts over a time window and produces a
compact, structured usage index of the skill harness. NO model tokens spent here;
this is the cheap deterministic layer the per-skill quality eval reads from.

Key signal: every `assistant` record carries `attributionSkill` = the skill that
was active when that turn was emitted. We attribute *emitted work* to skills via
that field, which cleanly excludes loaded skill-definition text (that lives in
user/system/tool_result records, never in an attributed assistant turn) — so
verdict-anchor phrases in a skill's own SKILL.md don't inflate its counts.

Invocations are counted from two places:
  - <command-name>/foo</command-name>  → user typed the slash command
  - Skill tool_use {"skill":"foo"}     → programmatic / chained invocation

Stdlib only (no third-party deps). Python 3.8+.

Outputs (into --out dir, default: an EPHEMERAL system-temp dir — slices/ hold raw
transcript excerpts and must NOT be committed to a shared/tracked repo):
  summary.json        per-skill aggregates + run metadata + dead/unknown lists
  slices/<skill>.json a bounded, window-spread sample of what each skill emitted,
                      each with the next human turn (friction/override signal),
                      for the quality-eval subagents to read.

Usage:
  extract_skill_usage.py [--days N] [--all-scopes] [--scope-dir DIR ...]
                         [--skills-dir DIR ...] [--out DIR] [--sample N]
                         [--slice-chars N] [--no-slices] [--quiet]

Scope defaults to $CLAUDE_CONFIG_DIR (else ~/.claude); --all-scopes widens to every
~/.claude*/ config dir on the machine.
"""
import argparse, glob, json, os, sys, tempfile
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta

# ---------- native built-ins (NOT user skills — never propose retiring one) ----
# Canonical bundled-skill names, extracted from the CLI binary (v2.1.239):
#   strings "$(readlink -f "$(which claude)")" | grep -A6 -B6 '^artifact-pr-review$'
# A name here is only treated as native when NO SKILL.md defines it — a real user
# skill of the same name always wins.
#
# Without this set, a native skill that emits attributed work (e.g. `/review`, an
# alias of native /code-review) reads as a user skill with a missing SKILL.md and
# gets proposed as retirable sediment.
NATIVE_BUILTIN_SKILLS = {
    "artifact-design", "artifact-diagramming", "artifact-capabilities",
    "workshop", "whiteboard", "dataviz", "code-review", "artifact-pr-review",
    "verify", "simplify", "commit", "commit-push-pr", "cowork-plugin", "loop",
    "security-review",
}
# Aliases the CLI resolves to a canonical native skill. `review` became an alias
# of `code-review` in CLI 2.1.223; aliases never appear in the skills listing.
NATIVE_SKILL_ALIASES = {"review": "code-review"}

# ---------- record helpers -------------------------------------------------

def parse_ts(rec):
    ts = rec.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None

def msg_content(rec):
    m = rec.get("message")
    return m.get("content") if isinstance(m, dict) else None

def text_of(content):
    """Flatten an assistant/user message content to plain text (skip tool blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts)
    return ""

def command_name(content):
    """Return the slash command a user typed, e.g. 'go' for <command-name>/go</command-name>."""
    if not isinstance(content, str) or "<command-name>" not in content:
        return None
    a = content.find("<command-name>") + len("<command-name>")
    b = content.find("</command-name>", a)
    if b == -1:
        return None
    return content[a:b].strip().lstrip("/")

def skill_toolcalls(content):
    """Yield skill names from Skill tool_use blocks in an assistant message."""
    if isinstance(content, list):
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "tool_use" and blk.get("name") == "Skill":
                s = (blk.get("input") or {}).get("skill")
                if s:
                    yield s

def is_human_turn(rec):
    """A real human prompt: not a tool_result echo, a slash-command wrapper, a
    harness injection (isMeta: skill bodies, reminders) or a compaction summary."""
    if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isCompactSummary"):
        return False
    c = msg_content(rec)
    if isinstance(c, str):
        return "<command-name>" not in c and "<local-command-stdout>" not in c
    if isinstance(c, list):
        # tool_result blocks => not a human turn
        return not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
    return False

# ---------- scope + inventory discovery ------------------------------------

def discover_scope_dirs(all_scopes, overrides):
    if overrides:
        return [os.path.expanduser(d) for d in overrides]
    if all_scopes:
        # every config scope on this machine: ~/.claude, ~/.claude-<name>, ...
        dirs = sorted(set(glob.glob(os.path.expanduser("~/.claude*/projects"))))
        return [os.path.dirname(d) for d in dirs]
    # current scope only
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return [cfg]

def user_skill_roots(scope_dirs, extra_dirs=()):
    """User-level skill dirs: <scope>/skills for each scanned scope, plus any
    --skills-dir extras (e.g. a shared skills dir symlinked into several scopes)."""
    roots = {os.path.join(d, "skills") for d in scope_dirs}
    roots |= {os.path.expanduser(d) for d in extra_dirs}
    return roots

def skill_inventory(user_roots, cwds=()):
    """Skill names defined anywhere this audit can see.

    Two sources:
      - user scopes: `user_roots` (see user_skill_roots)
      - PROJECT scopes: <cwd>/.claude/skills for every cwd seen in the transcripts,
        plus each cwd's ancestors up to $HOME (a session's cwd is often a subdir
        of the repo root that owns .claude/skills).

    Without the project scan, a project-scoped skill could never appear in the
    inventory or the dead list.

    Returns (names, origins) where origins maps name -> sorted list of the
    directories that define it (so same-named skills across projects are visible
    rather than silently merged).
    """
    origins = defaultdict(set)
    roots = set(user_roots)

    home = os.path.realpath(os.path.expanduser("~"))
    for cwd in cwds:
        if not cwd:
            continue
        d = os.path.realpath(cwd)
        # A worktree is a checkout of a repo we already inventory, so its
        # .claude/skills is a duplicate; counting it would turn one project into N
        # "project scopes" and make defined_in unreadable. Attribute to the repo.
        marker = f"{os.sep}.worktrees{os.sep}"
        if marker in d:
            d = d[:d.index(marker)]
        # walk up to $HOME looking for a project-scoped skills dir
        while d.startswith(home) and d != home:
            roots.add(os.path.join(d, ".claude", "skills"))
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent

    for root in sorted(roots):
        for skill_md in glob.glob(os.path.join(root, "*", "SKILL.md")):
            origins[os.path.basename(os.path.dirname(skill_md))].add(root)
    return set(origins), {k: sorted(v) for k, v in origins.items()}

# ---------- main extraction ------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--all-scopes", action="store_true")
    ap.add_argument("--scope-dir", action="append", default=[],
                    help="explicit config-scope dir(s); repeatable. Overrides scope discovery "
                         "(default: $CLAUDE_CONFIG_DIR, else ~/.claude).")
    ap.add_argument("--skills-dir", action="append", default=[],
                    help="extra user-level skills dir(s) to inventory; repeatable. <scope>/skills "
                         "is always included for each scanned scope.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--sample", type=int, default=15, help="max emitted episodes sampled per skill")
    ap.add_argument("--slice-chars", type=int, default=1600, help="max chars kept per sampled episode")
    ap.add_argument("--no-slices", action="store_true",
                    help="counters only: skip slices/ entirely. For consumers that want summary.json's "
                         "numbers without materializing raw transcript excerpts on disk (e.g. a skill-listing tool).")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)
    since_epoch = since.timestamp()

    scope_dirs = discover_scope_dirs(args.all_scopes, args.scope_dir)
    # recursive: catches both top-level session files (projects/<slug>/<uuid>.jsonl)
    # AND fork/subagent transcripts (projects/<slug>/<uuid>/subagents/agent-*.jsonl),
    # where the fork-wrapped skills (mutate, super-review, blast-radius, …) actually run.
    project_globs = [os.path.join(d, "projects", "**", "*.jsonl") for d in scope_dirs]
    files = sorted({f for g in project_globs for f in glob.glob(g, recursive=True)})

    cwds = set()                 # every session cwd seen -> project-scope discovery

    # per-skill aggregates
    inv_typed = Counter()        # <command-name> user invocations (real skills only)
    work_inferred = Counter()    # subagent turns attributed by last-Skill-in-file
    work_inferred_chars = Counter()
    inv_toolcall = Counter()     # Skill tool_use invocations
    raw_typed = Counter()        # every <command-name> seen, classified against known set at the end
    typed_sessions = defaultdict(set)
    typed_first, typed_last = {}, {}
    work_records = Counter()     # attributed assistant turns (work volume)
    work_chars = Counter()
    sidechain_records = Counter()
    sessions_of = defaultdict(set)
    first_ts = {}
    last_ts = {}
    unknown_cmds = Counter()     # command-names not in inventory (built-ins etc.)
    # sampling: keep all attributed episodes lightly, then stride-sample at the end
    episodes = defaultdict(list)  # skill -> [ {session, ts, isSidechain, text, next_user} ]

    files_scanned = files_in_window = records_scanned = 0

    # Pre-pass: harvest cwds from EVERY transcript, including ones older than the
    # window. Project-scope discovery must not depend on --days, or a short window
    # would inventory fewer projects and silently shrink the dead list — a skill's
    # membership there would then depend on how long a window you asked for.
    # One line per file is enough; `cwd` is on the first record.
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec0 = json.loads(line)
                    except json.JSONDecodeError:
                        break
                    if rec0.get("cwd"):
                        cwds.add(rec0["cwd"])
                    break
        except OSError:
            continue

    for f in files:
        try:
            if os.path.getmtime(f) < since_epoch:
                continue  # last write predates window => no in-window records
        except OSError:
            continue
        files_scanned += 1
        touched = False
        # first pass: load records of this file we care about, in order
        recs = []
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        recs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue

        # A subagent transcript is ONE dispatched job, so the last Skill invoked in
        # the file is a safe stand-in for attribution on turns the harness left
        # untagged: a composite that dispatches sub-agents to run an atom per item
        # leaves those turns without attributionSkill, so the atom would otherwise
        # show heavy invocation but zero work. Restricted to subagent files on purpose: in a top-level session an untagged turn is the
        # main session working, and the last Skill call may have finished long ago.
        is_subagent = f"{os.sep}subagents{os.sep}" in f
        current_skill = None

        # index human turns by position for "next_user" lookup
        for i, r in enumerate(recs):
            records_scanned += 1
            ts = parse_ts(r)
            if ts and ts < since:
                continue
            rtype = r.get("type")
            sess = r.get("sessionId") or os.path.basename(f)[:-6]
            content = msg_content(r)
            if r.get("cwd"):
                cwds.add(r["cwd"])

            if rtype == "user":
                cmd = command_name(content) if isinstance(content, str) else None
                if cmd:
                    touched = True
                    raw_typed[cmd] += 1
                    typed_sessions[cmd].add(sess)
                    _bump_ts(typed_first, typed_last, cmd, ts)

            elif rtype == "assistant":
                # (a) invocation via Skill tool_use
                for s in skill_toolcalls(content):
                    touched = True
                    inv_toolcall[s] += 1
                    sessions_of[s].add(sess)
                    _bump_ts(first_ts, last_ts, s, ts)
                    current_skill = s
                # (b) attributed emitted work
                skill = r.get("attributionSkill")
                if not skill and is_subagent and current_skill:
                    # (b2) inferred attribution — kept in a SEPARATE counter so the
                    # eval can tell harness-tagged work from inferred work.
                    touched = True
                    work_inferred[current_skill] += 1
                    sessions_of[current_skill].add(sess)
                    _bump_ts(first_ts, last_ts, current_skill, ts)
                    itxt = text_of(content).strip()
                    work_inferred_chars[current_skill] += len(itxt)
                    if itxt and len(episodes[current_skill]) < args.sample * 4:
                        episodes[current_skill].append({
                            "session": sess,
                            "ts": ts.isoformat() if ts else None,
                            "isSidechain": bool(r.get("isSidechain")),
                            "inferred_attribution": True,
                            "text": itxt[:args.slice_chars],
                            "next_user": _next_human(recs, i, args.slice_chars // 2),
                        })
                if skill:
                    touched = True
                    work_records[skill] += 1
                    sessions_of[skill].add(sess)
                    _bump_ts(first_ts, last_ts, skill, ts)
                    if r.get("isSidechain"):
                        sidechain_records[skill] += 1
                    txt = text_of(content).strip()
                    work_chars[skill] += len(txt)
                    if txt:
                        episodes[skill].append({
                            "session": sess,
                            "ts": ts.isoformat() if ts else None,
                            "isSidechain": bool(r.get("isSidechain")),
                            "text": txt[:args.slice_chars],
                            "next_user": _next_human(recs, i, args.slice_chars // 2),
                        })
        if touched:
            files_in_window += 1

    # Inventory is built AFTER the scan: project-scoped skills are discovered from
    # the cwds the transcripts actually reported.
    user_roots = user_skill_roots(scope_dirs, args.skills_dir)
    inventory, skill_origins = skill_inventory(user_roots, cwds)

    # classify typed slash-commands: a real skill (in inventory, or ever attributed /
    # tool-called) counts as an invocation; anything else is a built-in (/copy, /compact…).
    known = set(inventory) | set(work_records) | set(work_inferred) | set(inv_toolcall)
    for cmd, cnt in raw_typed.items():
        if cmd in known:
            inv_typed[cmd] += cnt
            sessions_of[cmd] |= typed_sessions[cmd]
            tf, tl = typed_first.get(cmd), typed_last.get(cmd)
            if tf and (cmd not in first_ts or tf < first_ts[cmd]):
                first_ts[cmd] = tf
            if tl and (cmd not in last_ts or tl > last_ts[cmd]):
                last_ts[cmd] = tl
        else:
            unknown_cmds[cmd] += cnt

    # dead skills: defined but zero invocations AND zero attributed work
    active = set(inv_typed) | set(inv_toolcall) | set(work_records) | set(work_inferred)

    # Natives are anything used but undefined that the CLI ships (or aliases to one).
    # They are NOT user skills: they have no SKILL.md by design, cannot be retired,
    # and must never reach the dead list or the eval's sediment bucket.
    natives = {}
    for s in sorted(active - inventory):
        canon = NATIVE_SKILL_ALIASES.get(s, s)
        if canon in NATIVE_BUILTIN_SKILLS:
            natives[s] = {
                "canonical": canon,
                "is_alias": s != canon,
                "note": (f"native CLI skill; `/{s}` is an alias of `/{canon}`"
                         if s != canon else "native CLI skill (bundled, no SKILL.md by design)"),
            }
    dead = sorted(inventory - active)

    all_skills = sorted(active | inventory)
    per_skill = {}
    for s in all_skills:
        eps = [] if args.no_slices else episodes.get(s, [])
        if args.sample > 0 and len(eps) > args.sample:
            stride = len(eps) / args.sample
            eps = [eps[int(i * stride)] for i in range(args.sample)]
        elif args.sample <= 0:
            eps = []
        per_skill[s] = {
            "in_inventory": s in inventory,
            "defined_in": skill_origins.get(s, []),
            "is_native_builtin": s in natives,
            "native_note": natives.get(s, {}).get("note"),
            "invocations_typed": inv_typed[s],
            "invocations_toolcall": inv_toolcall[s],
            "invocations_total": inv_typed[s] + inv_toolcall[s],
            "work_records": work_records[s],
            "work_records_inferred": work_inferred[s],
            "work_records_total": work_records[s] + work_inferred[s],
            "work_chars": work_chars[s] + work_inferred_chars[s],
            "sidechain_records": sidechain_records[s],
            "sessions": len(sessions_of[s]),
            "first_ts": first_ts.get(s),
            "last_ts": last_ts.get(s),
            "sampled_episodes": len(eps),
        }
        per_skill[s]["_episodes"] = eps  # split out to slices/ on write

    # ---- write outputs ----
    # Default to an EPHEMERAL temp dir: slices/ hold raw transcript excerpts, which
    # must never land in a committed/tracked repo. Only the synthesized report
    # (reference-only citations) belongs in <config dir>/audits/.
    out = args.out or os.path.join(
        tempfile.gettempdir(), f"harness-audit-work-{now:%Y-%m-%d}")
    os.makedirs(os.path.join(out, "slices") if not args.no_slices else out, exist_ok=True)

    summary_skills = {}
    for s, d in per_skill.items():
        eps = d.pop("_episodes")
        summary_skills[s] = d
        if eps:
            with open(os.path.join(out, "slices", f"{s}.json"), "w", encoding="utf-8") as fh:
                json.dump({"skill": s, "episodes": eps}, fh, indent=1)

    summary = {
        "generated": now.isoformat(),
        "window_days": args.days,
        "since": since.isoformat(),
        "scope_dirs": scope_dirs,
        "all_scopes": args.all_scopes,
        "files_total": len(files),
        "files_scanned": files_scanned,
        "files_in_window": files_in_window,
        "records_scanned": records_scanned,
        "inventory_size": len(inventory),
        "user_skill_roots": sorted(user_roots),
        # Any defining root that isn't a user root was discovered from a session cwd.
        "project_scopes_scanned": sorted(
            r for r in {o for v in skill_origins.values() for o in v}
            if r not in user_roots),
        "dead_skills": dead,
        "native_builtins_used": natives,
        "unknown_command_names": dict(unknown_cmds.most_common()),
        "skills": summary_skills,
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)

    if not args.quiet:
        _print_table(summary)
    print(f"\n[extract] wrote {out}/summary.json + slices/  "
          f"({files_in_window} in-window files, {len(active)} skills active, {len(dead)} dead)")
    print(out)  # last line = out dir, for the skill to capture

def _bump_ts(first, last, k, ts):
    if not ts:
        return
    iso = ts.isoformat()  # ISO-8601 UTC strings sort chronologically
    if k not in first or iso < first[k]:
        first[k] = iso
    if k not in last or iso > last[k]:
        last[k] = iso

def _next_human(recs, i, cap):
    for j in range(i + 1, min(i + 12, len(recs))):
        if is_human_turn(recs[j]):
            return text_of(msg_content(recs[j])).strip()[:cap]
    return None

def _print_table(summary):
    rows = sorted(summary["skills"].items(),
                  key=lambda kv: (kv[1]["invocations_total"], kv[1]["work_records_total"]),
                  reverse=True)
    print(f"\nHarness usage — last {summary['window_days']}d "
          f"({summary['files_in_window']} sessions, scopes: {', '.join(summary['scope_dirs'])})\n")
    print(f"{'skill':22} {'inv':>4} {'typed':>6} {'chain':>6} {'work':>5} {'infer':>6} {'sess':>5}  last")
    print("-" * 80)
    for s, d in rows:
        if d["invocations_total"] == 0 and d["work_records_total"] == 0:
            continue
        last = (d["last_ts"] or "")[:10]
        name = s + (" ~native" if d.get("is_native_builtin") else "")
        print(f"{name:22} {d['invocations_total']:>4} {d['invocations_typed']:>6} "
              f"{d['invocations_toolcall']:>6} {d['work_records']:>5} "
              f"{d['work_records_inferred']:>6} {d['sessions']:>5}  {last}")
    print("\n'work' = harness-tagged attributionSkill; 'infer' = inferred from the last "
          "Skill call\n  inside a subagent transcript (separate on purpose — do not merge them).")
    if summary.get("native_builtins_used"):
        print("\nNATIVE CLI SKILLS (no SKILL.md by design — NOT user sediment, cannot be retired):")
        for s, meta in sorted(summary["native_builtins_used"].items()):
            print(f"  {s:22} {meta['note']}")
    if summary["dead_skills"]:
        print(f"\nDEAD (defined, 0 use in window): {', '.join(summary['dead_skills'])}")
    if summary.get("project_scopes_scanned"):
        print(f"\nProject skill scopes inventoried: {len(summary['project_scopes_scanned'])}")

if __name__ == "__main__":
    main()
