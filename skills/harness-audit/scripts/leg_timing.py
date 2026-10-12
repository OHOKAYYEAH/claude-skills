#!/usr/bin/env python3
"""leg_timing.py — per-leg wall-clock and halt mechanics for the harness audit.

Companion to extract_skill_usage.py (which counts invocations and attributed work).
This one answers the questions the counts can't: how long does each leg take, where
does a /work or /ship session's active time go, what happened right after each
Super-review Recap, and did the native /security-review ever see a diff.

Read-only. Prints to stdout. The output contains session ids, cwd tails and short
lowercased fragments of human turns (for classifying stalls) — keep it in the
ephemeral --out dir of the audit, never commit it.

Usage:
  python3 leg_timing.py [--days 45] [--scope-dir DIR ...] [--focus skill ...]
  (scope defaults to $CLAUDE_CONFIG_DIR, else ~/.claude)

Definitions:
  episode  = contiguous run of one attributionSkill inside one transcript file;
             non-attributed records (tool results) join the current run; a gap
             > IDLE_SPLIT ends it (the human walked away).
  wall     = first -> last record of an episode, minutes.
  active   = sum of inter-record gaps, each capped at GAP_CAP seconds (drops long
             human idle waits, keeps model + tool time).
  Forked skills (context: fork) live in <session>/subagents/agent-*.jsonl, so their
  episode is the whole sub-file. Inline skills are runs inside the main file.
Caveat: attribution spills forward — after an inline skill calls an inner Skill, the
  parent's next turns are tagged with the inner skill until another call. So an
  inline orchestrator's own triage time shows up under its last-called leg.
  Section H is attribution-independent and doesn't have this problem.
"""
import argparse, glob, json, os, re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

GAP_CAP = 300
IDLE_SPLIT = 1800
# Skill names below match this suite; edit them to match your own skills.
LAND = {"qa-and-pr", "merge-and-verify", "report", "wrap-up", "done-check", "handoff", "compound"}
FORKED = ("review-plan", "mutate", "blast-radius", "sec-review", "code-review", "deep-research", "curate", "harness-audit", "super-review")
DEFAULT_FOCUS = ["work", "ship", "super-review", "code-review", "blast-radius", "sec-review", "security-review",
                 "review-plan", "mutate", "test", "tdd", "qa-and-pr", "recommend", "debug"]
LEGS = ["work", "review-plan", "tdd", "test", "mutate", "super-review", "code-review",
        "blast-radius", "sec-review", "recommend", "qa-and-pr", "ship", "report", "go"]

# ---------- record helpers ----------
def parse_ts(r):
    t = r.get("timestamp")
    if not t: return None
    try: return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError: return None
def content(r):
    m = r.get("message"); return m.get("content") if isinstance(m, dict) else None
def blocks(c, kind):
    return [b for b in c if isinstance(b, dict) and b.get("type") == kind] if isinstance(c, list) else []
def atext(r):
    c = content(r)
    if isinstance(c, str): return c
    return "\n".join(b.get("text", "") for b in blocks(c, "text"))
def rtext(r):
    out = []
    for b in blocks(content(r), "tool_result"):
        cc = b.get("content")
        if isinstance(cc, str): out.append(cc)
        elif isinstance(cc, list): out += [x.get("text", "") for x in cc if isinstance(x, dict) and x.get("type") == "text"]
    return "\n".join(out)
def skill_calls(r):
    return [(b.get("input") or {}).get("skill") for b in blocks(content(r), "tool_use") if b.get("name") == "Skill"]
def tool_uses(r):
    return [b.get("name") for b in blocks(content(r), "tool_use")]
def is_human(r):
    if r.get("type") != "user" or r.get("isMeta"): return False
    c = content(r)
    if isinstance(c, str): return "<command-name>" not in c and "<local-command" not in c and not c.startswith("<")
    if isinstance(c, list): return not blocks(c, "tool_result")
    return False
def typed_cmd(r):
    c = content(r)
    if r.get("type") == "user" and isinstance(c, str) and "<command-name>" in c:
        a = c.find("<command-name>") + 14; b = c.find("</command-name>", a); return c[a:b].strip().lstrip("/")
    return None
def is_worktree(cwd): return bool(cwd) and ("-wt/" in cwd or "/.worktrees/" in cwd or "/worktrees/" in cwd)
def q(xs, p):
    if not xs: return 0
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round((len(xs) - 1) * p)))]
def active_minutes(recs, a, b):
    prev = None; tot = 0.0
    for r in recs:
        t = r["_ts"]
        if t < a or t > b: continue
        if prev is not None: tot += min((t - prev).total_seconds(), GAP_CAP)
        prev = t
    return tot / 60

# ---------- load ----------
def load(scope_dirs, since):
    sessions, subfiles = {}, defaultdict(list)
    for d in scope_dirs:
        for f in sorted(glob.glob(os.path.join(d, "projects", "**", "*.jsonl"), recursive=True)):
            try:
                if datetime.fromtimestamp(os.path.getmtime(f), timezone.utc) < since - timedelta(days=2): continue
            except OSError: continue
            recs = []
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try: r = json.loads(line)
                    except json.JSONDecodeError: continue
                    ts = parse_ts(r)
                    if ts is None or ts < since: continue
                    r["_ts"] = ts; recs.append(r)
            if not recs: continue
            if f"{os.sep}subagents{os.sep}" in f:
                subfiles[os.path.basename(os.path.dirname(os.path.dirname(f)))].append((f, recs))
            else:
                sessions[os.path.basename(f)[:-6]] = (f, recs)
    return sessions, subfiles

def episodes(recs):
    eps, cur = [], None
    for r in recs:
        if r.get("type") == "assistant" and r.get("attributionSkill"):
            s = r["attributionSkill"]
            if cur is None or cur["skill"] != s or (r["_ts"] - cur["last"]).total_seconds() > IDLE_SPLIT:
                cur = {"skill": s, "first": r["_ts"], "last": r["_ts"], "active": 0.0, "n": 1}; eps.append(cur)
            else:
                cur["active"] += min((r["_ts"] - cur["last"]).total_seconds(), GAP_CAP); cur["last"] = r["_ts"]; cur["n"] += 1
        elif cur is not None and r.get("type") in ("user", "assistant"):
            gap = (r["_ts"] - cur["last"]).total_seconds()
            if gap > IDLE_SPLIT: cur = None; continue
            cur["active"] += min(gap, GAP_CAP); cur["last"] = r["_ts"]
    return eps

def is_composite_session(recs):
    return any((r.get("type") == "assistant" and any(s in ("work", "ship") for s in skill_calls(r))) or typed_cmd(r) in ("work", "ship") for r in recs)

# ---------- sections ----------
def sec_A(per_skill, focus):
    print("## A. Per-skill wall-clock (minutes): wall = first→last attributed record (split on >30m idle); active = gaps capped at 5m")
    print(f"{'skill':16}{'eps':>5}{'main':>5}{'sub':>5}{'wall p50':>9}{'wall p90':>9}{'act p50':>8}{'act p90':>8}{'act total h':>12}")
    for s in focus:
        eps = per_skill.get(s, [])
        if not eps: print(f"{s:16}    0"); continue
        walls = [(e["last"] - e["first"]).total_seconds() / 60 for e in eps]; acts = [e["active"] / 60 for e in eps]
        nm = sum(1 for e in eps if e["file"] == "main")
        print(f"{s:16}{len(eps):>5}{nm:>5}{len(eps)-nm:>5}{q(walls,.5):>9.1f}{q(walls,.9):>9.1f}{q(acts,.5):>8.1f}{q(acts,.9):>8.1f}{sum(acts)/60:>12.1f}")

def sec_B(sessions, per_skill_by_sess):
    print("\n## B. Composite sessions: per-leg ACTIVE minutes (main-file episodes + that session's subagent files), from the first /work or /ship call")
    for root in ("work", "ship"):
        rows = []
        for sid, (f, recs) in sessions.items():
            starts = [r["_ts"] for r in recs if (r.get("type") == "assistant" and root in skill_calls(r)) or typed_cmd(r) == root]
            if not starts: continue
            t0 = min(starts); legs = Counter(); end = t0
            for e in per_skill_by_sess.get(sid, []):
                if e["last"] < t0: continue
                legs[e["skill"]] += e["active"] / 60; end = max(end, e["last"])
            rows.append((sid, (end - t0).total_seconds() / 60, sum(legs.values()), legs))
        if not rows: continue
        print(f"\n### sessions containing /{root}: n={len(rows)} · session wall p50={q([r[1] for r in rows],.5):.0f}m · summed leg-active p50={q([r[2] for r in rows],.5):.0f}m")
        agg = Counter(); n_with = Counter()
        for _, _, _, legs in rows:
            for k, v in legs.items():
                agg[k] += v; n_with[k] += (v > 0)
        tot = sum(agg.values()) or 1
        print(f"{'leg':16}{'sessions':>9}{'share of active':>17}{'median min when present':>25}")
        for k in LEGS:
            if agg[k] == 0: continue
            print(f"{k:16}{n_with[k]:>9}{100*agg[k]/tot:>16.0f}%{q([l[k] for *_, l in rows if l[k] > 0],.5):>25.1f}")
        print(f"{'(other skills)':16}{'':>9}{100*sum(v for k, v in agg.items() if k not in LEGS)/tot:>16.0f}%")

def sec_H(sessions):
    print("\n## H. End-to-end wall-clock, attribution-independent (minutes): Skill call → terminus")
    def spans(root, terminators):
        out = []
        for sid, (f, recs) in sessions.items():
            for i, r in enumerate(recs):
                if not ((r.get("type") == "assistant" and root in skill_calls(r)) or typed_cmd(r) == root): continue
                t0 = r["_ts"]; t_end = None; how = "session-end"
                for r2 in recs[i + 1:]:
                    if r2.get("type") == "assistant":
                        if any(s in terminators for s in skill_calls(r2)): t_end, how = r2["_ts"], "terminator-skill"; break
                        if root == "super-review" and "Super-review Recap" in atext(r2) and "Status" in atext(r2): t_end, how = r2["_ts"], "recap"; break
                    if is_human(r2): t_end, how = r2["_ts"], "human-turn"; break
                if t_end is None: t_end = recs[-1]["_ts"]
                out.append(((t_end - t0).total_seconds() / 60, active_minutes(recs, t0, t_end), how))
        return out
    for root, terms in (("super-review", LAND), ("work", {"report", "qa-and-pr", "merge-and-verify"})):
        sp = spans(root, terms)
        if not sp: print(f"{root:14} n=0"); continue
        print(f"{root:14} n={len(sp):<3} wall p50={q([s[0] for s in sp],.5):6.1f} p90={q([s[0] for s in sp],.9):6.1f}  active p50={q([s[1] for s in sp],.5):6.1f} p90={q([s[1] for s in sp],.9):6.1f}  ended-by={dict(Counter(s[2] for s in sp))}")

def sec_I(sessions):
    print("\n## I. After the LAST 'Super-review Recap' in each /work|/ship session: next event (HUMAN after ✅ = stall candidate)")
    outcomes = Counter(); detail = []
    for sid, (f, recs) in sessions.items():
        if not is_composite_session(recs): continue
        idx = [i for i, r in enumerate(recs) if r.get("type") == "assistant" and "Super-review Recap" in atext(r)]
        if not idx: outcomes["no-recap-in-session"] += 1; continue
        i = idx[-1]; m = re.search(r"Status:\*?\*?\s*([^\n]{0,40})", atext(recs[i])); st = (m.group(1) if m else "?").strip()[:28]
        nxt = "session-end"
        for r2 in recs[i + 1:]:
            if r2.get("type") == "assistant" and skill_calls(r2): nxt = "skill:" + str(skill_calls(r2)[0]); break
            if r2.get("type") == "assistant" and tool_uses(r2): nxt = "tool:" + str(tool_uses(r2)[0]); break
            if is_human(r2): nxt = "HUMAN"; break
        outcomes[nxt.split(":")[0]] += 1; detail.append((sid[:8], st, nxt))
    print(dict(outcomes))
    for d in sorted(detail): print(f"  {d[0]}  status={d[1]:28}  next={d[2]}")

def sec_J(subfiles):
    print("\n## J. sec-review forks: did the native /security-review prompt carry a diff? (its own FILES MODIFIED / DIFF CONTENT sections)")
    rows = []
    for parent, lst in subfiles.items():
        for f, recs in lst:
            if not any(r.get("type") == "assistant" and r.get("attributionSkill") == "sec-review" for r in recs): continue
            cwd = next((r["cwd"] for r in recs if r.get("cwd")), "")
            native = None
            for r in recs:
                t = atext(r) if r.get("type") == "user" else ""
                if "FILES MODIFIED" in t and "DIFF CONTENT" in t:
                    seg = t[t.find("FILES MODIFIED"):t.find("FILES MODIFIED") + 400]
                    native = "EMPTY" if "no output" in seg or re.search(r"FILES MODIFIED:\s*\n\s*\n?\s*DIFF CONTENT", seg) else "has-diff"
            rows.append((parent[:8], "Y" if is_worktree(cwd) else "n", native or "native-not-called"))
    c = Counter(r[2] for r in rows)
    print(f"sec-review forks: {len(rows)} · native prompt EMPTY: {c['EMPTY']} · has-diff: {c['has-diff']} · native not called: {c['native-not-called']}")
    for r in sorted(rows): print(f"  {r[0]} worktree={r[1]} native-diff={r[2]}")

def sec_K(sessions):
    print("\n## K. blast-radius: forked vs not, in sessions that invoked super-review (skip/inline wording counted any attribution)")
    GATE = re.compile(r"[^.\n]{0,80}blast.radius[^.\n]{0,120}", re.I)
    INL = re.compile(r"(inline|skip|not needed|no shared|no cross-repo|purely internal|internal only|doesn't touch|does not touch|redundant)", re.I)
    ran = skipped = worded = 0; samples = []
    for sid, (f, recs) in sessions.items():
        if not any(r.get("type") == "assistant" and "super-review" in skill_calls(r) for r in recs): continue
        called = any(r.get("type") == "assistant" and "blast-radius" in skill_calls(r) for r in recs)
        phr = [m.group(0).strip() for r in recs if r.get("type") == "assistant" for m in GATE.finditer(atext(r)) if INL.search(m.group(0)) and "SKILL" not in m.group(0)]
        if called: ran += 1
        else:
            skipped += 1
            if phr: worded += 1; samples.append((sid[:8], phr[0][:140]))
    print(f"super-review sessions: {ran+skipped} · blast-radius forked: {ran} · not forked: {skipped} (with skip/inline wording: {worded})")
    for s, p in samples[:12]: print(f"  {s}: {p}")

def sec_M(subfiles):
    print("\n## M. Fork prime cost: prompt chars, seconds to first tool call, tool calls, read-ish calls, suite runs, wall")
    SUITE = re.compile(r"\b(pytest|npm (run )?test|vitest|jest|go test)\b")
    prime = defaultdict(list)
    for parent, lst in subfiles.items():
        for f, recs in lst:
            sk = next((r.get("attributionSkill") for r in recs if r.get("type") == "assistant" and r.get("attributionSkill")), None)
            if sk not in FORKED: continue
            fu = next((r for r in recs if r.get("type") == "user"), None)
            ft = next((r for r in recs if r.get("type") == "assistant" and tool_uses(r)), None)
            if not fu: continue
            chars = len(atext(fu)) if isinstance(content(fu), str) else len(json.dumps(content(fu)))
            suite = sum(1 for r in recs if r.get("type") == "assistant" for b in blocks(content(r), "tool_use") if b.get("name") == "Bash" and SUITE.search(str((b.get("input") or {}).get("command", ""))))
            prime[sk].append((chars, (ft["_ts"] - fu["_ts"]).total_seconds() if ft else None,
                              sum(len(tool_uses(r)) for r in recs if r.get("type") == "assistant"),
                              sum(1 for r in recs if r.get("type") == "assistant" for t in tool_uses(r) if t in ("Read", "Bash", "Grep", "Glob")),
                              suite, (recs[-1]["_ts"] - recs[0]["_ts"]).total_seconds() / 60))
    print(f"{'skill':14}{'n':>4}{'prompt chars p50':>17}{'s→1st tool':>11}{'tools p50':>10}{'read-ish':>9}{'suite runs total':>17}{'wall p50':>9}")
    for sk, rows in sorted(prime.items(), key=lambda kv: -len(kv[1])):
        print(f"{sk:14}{len(rows):>4}{q([r[0] for r in rows],.5):>17.0f}{q([r[1] for r in rows if r[1] is not None],.5):>11.0f}{q([r[2] for r in rows],.5):>10.0f}{q([r[3] for r in rows],.5):>9.0f}{sum(r[4] for r in rows):>17}{q([r[5] for r in rows],.5):>9.1f}")

def sec_N(sessions):
    print("\n## N. Human free-text turns inside composites, by preceding skill (first 70 chars, lowercased — classify, don't quote)")
    by_prev = Counter(); ex = defaultdict(list)
    for sid, (f, recs) in sessions.items():
        if not is_composite_session(recs): continue
        prev = None
        for r in recs:
            if r.get("type") == "assistant" and r.get("attributionSkill"): prev = r["attributionSkill"]
            elif is_human(r) and prev:
                t = re.sub(r"\s+", " ", atext(r)).strip().lower()[:70]
                if not t: continue
                by_prev[prev] += 1
                if prev in ("super-review", "work", "ship", "recommend", "code-review", "test", "mutate", "review-plan", "blast-radius", "sec-review") and len(ex[prev]) < 6:
                    ex[prev].append(f"{sid[:8]} {t}")
    for k, v in by_prev.most_common(16): print(f"  {k:16}{v:>5}")
    for k, lst in ex.items():
        for e in lst: print(f"    after {k:12}: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--scope-dir", action="append", default=[])
    ap.add_argument("--focus", nargs="*", default=None)
    a = ap.parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=a.days)
    scope_dirs = [os.path.expanduser(d) for d in a.scope_dir] or [os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")]
    sessions, subfiles = load(scope_dirs, since)
    print(f"# leg_timing · last {a.days}d since {since.date()} · scope {scope_dirs} · top-level sessions {len(sessions)} · subagent files {sum(len(v) for v in subfiles.values())}\n")
    per_skill = defaultdict(list); per_skill_by_sess = defaultdict(list)
    for sid, (f, recs) in sessions.items():
        for e in episodes(recs): e.update(sess=sid, file="main"); per_skill[e["skill"]].append(e); per_skill_by_sess[sid].append(e)
    for parent, lst in subfiles.items():
        for f, recs in lst:
            for e in episodes(recs): e.update(sess=parent, file="sub"); per_skill[e["skill"]].append(e); per_skill_by_sess[parent].append(e)
    sec_A(per_skill, a.focus or DEFAULT_FOCUS)
    sec_B(sessions, per_skill_by_sess)
    sec_H(sessions)
    sec_I(sessions)
    sec_J(subfiles)
    sec_K(sessions)
    sec_M(subfiles)
    sec_N(sessions)

if __name__ == "__main__":
    main()
