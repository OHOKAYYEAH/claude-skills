"""Tests for extract_framework_health.py. Run from the skill dir:
    python3 -m unittest discover -s scripts/tests
"""
import atexit, json, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import extract_framework_health as fh  # noqa: E402

SESS = "11111111-aaaa-bbbb-cccc-000000000001"


def user(uuid, text, ts, sess=SESS, **kw):
    return {"type": "user", "uuid": uuid, "sessionId": sess, "timestamp": ts,
            "message": {"role": "user", "content": text}, **kw}


def asst(uuid, text, ts, sess=SESS, tools=()):
    content = [{"type": "text", "text": text}] if text else []
    content += [{"type": "tool_use", "id": f"tu-{uuid}-{i}", "name": n, "input": inp}
                for i, (n, inp) in enumerate(tools)]
    return {"type": "assistant", "uuid": uuid, "sessionId": sess, "timestamp": ts,
            "message": {"role": "assistant", "content": content}}


def tool_result(uuid, text, ts, sess=SESS, tur=None):
    rec = {"type": "user", "uuid": uuid, "sessionId": sess, "timestamp": ts,
           "message": {"role": "user", "content": [
               {"type": "tool_result", "tool_use_id": "x", "content": text}]}}
    if tur is not None:
        rec["toolUseResult"] = tur
    return rec


def recap(uuid, result, ts, sess=SESS):
    return tool_result(uuid, result, ts, sess,
                       tur={"success": True, "commandName": "spec-check",
                            "status": "forked", "agentId": "a1", "result": result})


class Scope:
    """A throwaway config scope: <root>/projects/<slug>/<file>.jsonl."""

    def __init__(self):
        self.root = tempfile.mkdtemp()
        atexit.register(shutil.rmtree, self.root, True)
        self.proj = os.path.join(self.root, "projects", "-home-x")
        os.makedirs(self.proj)

    def write(self, name, recs, sub=None):
        d = os.path.join(self.proj, sub) if sub else self.proj
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh_:
            for r in recs:
                fh_.write(json.dumps(r) + "\n")

    def extract(self, **kw):
        kw.setdefault("since", "2026-07-01")
        kw.setdefault("until", "2026-10-31")
        return fh.extract([self.root], **kw)


class PairTests(unittest.TestCase):
    def test_replayed_records_pair_once_and_resume_pairs_with_replayed_ai(self):
        s = Scope()
        parent = [user("h0", "start", "2026-08-01T10:00:00Z"),
                  asst("a1", "first answer", "2026-08-01T10:01:00Z"),
                  user("h1", "ok do it", "2026-08-01T10:02:00Z"),
                  asst("a2", "done, shall I continue?", "2026-08-01T10:03:00Z")]
        resume = parent + [user("h2", "yes continue", "2026-08-02T09:00:00Z", sess="s2")]
        s.write(SESS + ".jsonl", parent)
        s.write("s2.jsonl", resume)
        pairs = s.extract()["pairs"]
        self.assertEqual([p["id"] for p in pairs], ["h1", "h2"])
        self.assertEqual(pairs[1]["ai_tail"], "done, shall I continue?")

    def test_pairs_reach_back_past_many_tool_calls(self):
        s = Scope()
        recs = [user("h0", "go", "2026-08-01T10:00:00Z"),
                asst("a0", "Here is the plan.", "2026-08-01T10:00:30Z")]
        for i in range(30):
            recs.append(asst(f"t{i}", "", "2026-08-01T10:01:00Z", tools=[("Bash", {"command": "ls"})]))
            recs.append(tool_result(f"r{i}", "out", "2026-08-01T10:01:01Z"))
        recs.append(user("h1", "no, wrong file", "2026-08-01T10:05:00Z"))
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["ai_tail"]), ("h1", "Here is the plan."))

    def test_noise_turns_skipped_and_slash_command_kept_unlabelled(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Want me to proceed?", "2026-08-01T10:01:00Z"),
                user("m1", "skill body", "2026-08-01T10:01:10Z", isMeta=True),
                user("n1", "<task-notification>done</task-notification>", "2026-08-01T10:01:20Z"),
                user("l1", "<local-command-stdout>x</local-command-stdout>", "2026-08-01T10:01:30Z"),
                user("g1", "<command-message>go</command-message>\n<command-name>/go</command-name>",
                     "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["human"], p["label"]), ("g1", "/go", None))
        self.assertEqual(p["ai_tail"], "Want me to proceed?")

    def test_sidechain_records_neither_pair_nor_replace_the_ai_turn(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "main answer", "2026-08-01T10:01:00Z"),
                {**asst("x1", "subagent answer", "2026-08-01T10:01:10Z"), "isSidechain": True},
                user("x2", "subagent prompt", "2026-08-01T10:01:20Z", isSidechain=True),
                user("h1", "thanks", "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["ai_tail"]), ("h1", "main answer"))

    def test_compact_summary_is_not_a_human_turn(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Want me to proceed?", "2026-08-01T10:01:00Z"),
                user("c1", "This session is being continued from a previous conversation.",
                     "2026-08-01T10:01:10Z", isCompactSummary=True),
                user("h1", "yes", "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["ai_tail"]), ("h1", "Want me to proceed?"))

    def test_reply_led_by_a_system_reminder_keeps_the_typed_text(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Done.", "2026-08-01T10:01:00Z"),
                user("h1", "<system-reminder>file changed</system-reminder>\nno, revert that",
                     "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["human"]), ("h1", "no, revert that"))

    def test_local_cli_commands_do_not_take_the_reply(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Want me to run the migration?", "2026-08-01T10:01:00Z"),
                user("m1", "<command-name>/model</command-name>\n<command-args>sonnet</command-args>",
                     "2026-08-01T10:01:30Z"),
                user("h1", "yes", "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["id"], p["ai_tail"]), ("h1", "Want me to run the migration?"))

    def test_a_forked_copy_does_not_count_a_decision_twice(self):
        s = Scope()
        base = [user("h0", "build", "2026-08-01T10:00:00Z"),
                asst("a1", "Decision: use table X — because y", "2026-08-01T10:01:00Z")]
        s.write(SESS + ".jsonl", base + [user("r1", "no, table Z", "2026-08-01T10:02:00Z")])
        s.write("fork.jsonl", base + [user("r2", "ok", "2026-08-01T10:03:00Z", sess="fork")])
        pairs = s.extract()["pairs"]
        self.assertEqual(sum(p["decision_count"] for p in pairs), 1)

    def test_slash_command_reply_keeps_its_args(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Ready to ship?", "2026-08-01T10:01:00Z"),
                user("g1", "<command-name>/ship</command-name>\n<command-args>PROJ-12 --skip-qa</command-args>",
                     "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual(p["human"], "/ship PROJ-12 --skip-qa")

    def test_pair_state_resets_after_each_reply(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Decision: drop the column — because it is unused", "2026-08-01T10:01:00Z"),
                user("i1", "[Request interrupted by user]", "2026-08-01T10:01:30Z"),
                user("h1", "stop", "2026-08-01T10:02:00Z"),
                asst("a2", "Stopped.", "2026-08-01T10:03:00Z"),
                user("h2", "fine", "2026-08-01T10:04:00Z"),
                user("h3", "and also check the logs", "2026-08-01T10:05:00Z")]
        s.write(SESS + ".jsonl", recs)
        pairs = s.extract()["pairs"]
        self.assertEqual([p["id"] for p in pairs], ["h1", "h2"])
        self.assertEqual((pairs[1]["decision"], pairs[1]["decision_count"], pairs[1]["interrupted"]),
                         (None, 0, False))

    def test_decision_template_placeholder_is_not_a_decision(self):
        s = Scope()
        recs = [user("h0", "what format?", "2026-08-01T10:00:00Z"),
                asst("a1", "Log each call as:\nDecision: <choice> — because <reason>", "2026-08-01T10:01:00Z"),
                user("h1", "got it", "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual((p["decision"], p["decision_count"]), (None, 0))

    def test_interrupt_marker_flags_the_following_reply(self):
        s = Scope()
        recs = [user("h0", "start", "2026-08-01T10:00:00Z"),
                asst("a1", "Editing the schema now", "2026-08-01T10:01:00Z"),
                user("i1", [{"type": "text", "text": "[Request interrupted by user]"}], "2026-08-01T10:01:30Z"),
                user("h1", "stop, not that table", "2026-08-01T10:02:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual(p["id"], "h1")
        self.assertTrue(p["interrupted"])

    def test_decision_line_since_previous_human_turn_is_carried(self):
        s = Scope()
        recs = [user("h0", "build it", "2026-08-01T10:00:00Z"),
                asst("a1", "Decision: use a flag — because the spec has five classes",
                     "2026-08-01T10:01:00Z"),
                asst("a2", "All done.", "2026-08-01T10:09:00Z"),
                user("h1", "great", "2026-08-01T10:10:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertTrue(p["decision"].startswith("Decision: use a flag"))
        self.assertEqual(p["ai_tail"], "All done.")

    def test_every_decision_line_before_one_reply_is_counted(self):
        s = Scope()
        recs = [user("h0", "build it", "2026-08-01T10:00:00Z"),
                asst("a1", "Decision: A — because x", "2026-08-01T10:01:00Z"),
                asst("a2", "Decision: B — because y\nDecision: C — because z", "2026-08-01T10:02:00Z"),
                user("h1", "great", "2026-08-01T10:10:00Z")]
        s.write(SESS + ".jsonl", recs)
        (p,) = s.extract()["pairs"]
        self.assertEqual(p["decision_count"], 3)

    def test_window_and_excluded_sessions(self):
        s = Scope()
        s.write(SESS + ".jsonl", [user("h0", "a", "2026-06-01T10:00:00Z"),
                                  asst("a0", "x", "2026-06-01T10:01:00Z"),
                                  user("h1", "old", "2026-06-01T10:02:00Z"),
                                  asst("a1", "y", "2026-08-01T10:01:00Z"),
                                  user("h2", "in window", "2026-08-01T10:02:00Z")])
        s.write("skip-me.jsonl", [user("k0", "a", "2026-08-01T10:00:00Z", sess="skip-me"),
                                  asst("k1", "x", "2026-08-01T10:01:00Z", sess="skip-me"),
                                  user("k2", "b", "2026-08-01T10:02:00Z", sess="skip-me")])
        ids = [p["id"] for p in s.extract(exclude_sessions=["skip", ""])["pairs"]]
        self.assertEqual(ids, ["h2"])

    def test_subagent_transcripts_are_ignored(self):
        s = Scope()
        s.write("agent-1.jsonl", [user("h0", "a", "2026-08-01T10:00:00Z"),
                                  asst("a0", "x", "2026-08-01T10:01:00Z"),
                                  user("h1", "b", "2026-08-01T10:02:00Z")],
                sub=os.path.join(SESS, "subagents"))
        self.assertEqual(s.extract()["pairs"], [])

    def test_a_half_written_line_skips_only_that_line(self):
        s = Scope()
        s.write(SESS + ".jsonl", [user("h0", "a", "2026-08-01T10:00:00Z"),
                                  asst("a0", "x", "2026-08-01T10:01:00Z"),
                                  user("h1", "b", "2026-08-01T10:02:00Z")])
        with open(os.path.join(s.proj, SESS + ".jsonl"), "a", encoding="utf-8") as f:
            f.write('{"type": "user", "uuid": "trunc')
        data = s.extract()
        self.assertEqual(([p["id"] for p in data["pairs"]], data["meta"]["bad_lines"]), (["h1"], 1))


class SampleTests(unittest.TestCase):
    def test_per_month_cap_is_deterministic_and_keeps_every_decision_pair(self):
        pairs = [{"id": f"h{i:02d}", "month": "2026-08", "ts": f"2026-08-01T10:{i:02d}:00Z",
                  "decision": "Decision: x" if i in (3, 4, 17) else None} for i in range(20)]
        a = fh.sample_pairs(pairs, per_month=5)
        self.assertEqual(a, fh.sample_pairs(pairs, per_month=5))
        self.assertEqual({p["id"] for p in a if p["decision"]}, {"h03", "h04", "h17"})
        # h04 is a stride pick; h03 and h17 ride along outside the signal-3 sample.
        self.assertEqual([p["id"] for p in a if p["in_sample"]], ["h00", "h04", "h08", "h12", "h16"])

    def test_sample_spreads_across_the_month_not_its_first_days(self):
        pairs = [{"id": f"h{i:02d}", "month": "2026-08", "ts": f"2026-08-{i + 1:02d}T10:00:00Z",
                  "decision": None} for i in range(20)]
        ids = [p["id"] for p in fh.sample_pairs(pairs, per_month=5)]
        self.assertEqual(ids, ["h00", "h04", "h08", "h12", "h16"])

    def test_cap_applies_per_month(self):
        pairs = [{"id": f"{m}-{i:02d}", "month": f"2026-{m}", "ts": f"2026-{m}-01T10:{i:02d}:00Z",
                  "decision": None} for m in ("08", "09") for i in range(10)]
        months = [p["month"] for p in fh.sample_pairs(pairs, per_month=3)]
        self.assertEqual(months, ["2026-08"] * 3 + ["2026-09"] * 3)


class RecapTests(unittest.TestCase):
    def test_only_structural_spec_check_results_count(self):
        s = Scope()
        s.write(SESS + ".jsonl", [
            tool_result("g1", "### Spec-check Recap\n**Status:** ✅ built to spec", "2026-09-30T10:00:00Z"),
            recap("r1", "### Spec-check Recap\n**Status:** ⚠️ needs your call.\n**Spec:** PROJ-1 comment 9 · frozen",
                  "2026-09-30T11:00:00Z"),
            recap("r2", "Built to spec. Every item is in.\n**Spec:** PROJ-2 description", "2026-09-30T12:00:00Z")])
        recaps = {r["id"]: r for r in s.extract()["recaps"]}
        self.assertEqual(sorted(recaps), ["r1", "r2"])
        self.assertEqual(recaps["r1"]["label"], "divergences")
        self.assertIsNone(recaps["r2"]["label"])
        self.assertEqual(recaps["r1"]["key"], "proj-1 comment 9")

    def test_status_emoji_maps_to_class(self):
        self.assertEqual(fh.recap_label("**Verdict: ✅ built to spec.** All met"), "built_to_spec")
        self.assertEqual(fh.recap_label("**Status:** 🔧 Built to spec, with one gap"), "gaps")
        self.assertEqual(fh.recap_label("**Status:** 🛑 can't verify — no diff"), "cant_verify")
        self.assertIsNone(fh.recap_label("The build matches the spec."))

    def test_earliest_status_marker_wins(self):
        self.assertEqual(fh.recap_label("**Status:** ⚠️ needs your call. Everything else ✅ built to spec"),
                         "divergences")

    def test_markers_past_the_status_head_are_ignored(self):
        body = "### Spec-check Recap\n**Status:** see below\n" + "x" * 300 + "\n| item 1 | ✅ |"
        self.assertIsNone(fh.recap_label(body))

    def test_key_without_a_frozen_spec_falls_back_to_ticket_then_session(self):
        self.assertEqual(fh.recap_key("**Spec:** none frozen — checked PROJ-7 description", "abcdef1234"),
                         "proj-7")
        self.assertEqual(fh.recap_key("Checked TEAM-12 against the diff", "abcdef1234"), "team-12")
        self.assertEqual(fh.recap_key("No spec, no ticket", "abcdef1234"), "session:abcdef12")

    def test_key_ignores_spec_line_wording_but_keeps_a_freeze_comment(self):
        self.assertEqual(fh.recap_key("**Spec:** the `PROJ-4` acceptance criteria", "s"), "proj-4")
        self.assertEqual(fh.recap_key("**Spec:** Jira PROJ-4 description, amended", "s"), "proj-4")
        self.assertEqual(fh.recap_key("**Spec:** PROJ-4 comment 4189 🔒 frozen spec", "s"), "proj-4 comment 4189")
        self.assertEqual(fh.recap_key("**Spec:** /tmp/x/memory/spec-foo.md (frozen)", "s"), "memory/spec-foo.md")

    def test_spec_file_outranks_a_ticket_in_the_body_and_non_tickets_are_ignored(self):
        self.assertEqual(fh.recap_key("**Spec:** docs/order-grid.md\nsee the PROJ-49 trap", "s"), "docs/order-grid.md")
        self.assertEqual(fh.recap_key("No spec line; UTF-8 bytes, SHA-256, UTC+2 dates, AC-1 met", "abcdef1234"),
                         "session:abcdef12")
        self.assertNotEqual(fh.recap_key("**Spec:** a/x/spec.md", "s"), fh.recap_key("**Spec:** a/y/spec.md", "s"))

    def test_label_reads_the_status_line_not_a_criteria_walk_above_it(self):
        text = "Walked 4 criteria: #1 ✅ met, #2 missing.\n### Spec-check Recap\n**Status:** 🔧 gaps owed"
        self.assertEqual(fh.recap_label(text), "gaps")

    def test_pre_window_check_makes_an_in_window_check_a_rerun(self):
        s = Scope()
        s.write(SESS + ".jsonl", [
            recap("r0", "**Status:** 🔧 gaps\n**Spec:** PROJ-9 description", "2026-06-30T10:00:00Z"),
            recap("r1", "**Status:** 🛑 can't verify\n**Spec:** PROJ-8", "2026-06-30T10:00:00Z"),
            recap("r2", "**Status:** ✅ built to spec\n**Spec:** PROJ-9 description", "2026-07-02T10:00:00Z"),
            recap("r3", "**Status:** ✅ built to spec\n**Spec:** PROJ-8", "2026-07-02T10:00:00Z")])
        os.utime(os.path.join(s.proj, SESS + ".jsonl"), (1751400000, 1751400000))  # 2025: pre-window mtime
        data = s.extract()
        self.assertEqual((data["prior_keys"], [r["id"] for r in data["recaps"]]), (["proj-9"], ["r2", "r3"]))

    def test_replayed_recap_counts_once(self):
        s = Scope()
        r = recap("r1", "**Status:** ✅ built to spec\n**Spec:** PROJ-3 comment 2", "2026-09-30T10:00:00Z")
        s.write(SESS + ".jsonl", [r])
        s.write("resumed.jsonl", [r])
        self.assertEqual([x["id"] for x in s.extract()["recaps"]], ["r1"])


class RefreezeTests(unittest.TestCase):
    def test_refreeze_after_build_line_counts_as_after_build(self):
        s = Scope()
        spec = "🔒 FROZEN SPEC — x · feature · 2026-09-01\nticket: PROJ-1 · supersedes: 2026-08-30"
        s.write(SESS + ".jsonl", [
            asst("a0", "🔒 FROZEN SPEC — x · feature · 2026-08-30\nticket: PROJ-1 · supersedes: —",
                 "2026-08-30T10:00:00Z"),
            asst("a1", "RED: t.py::test_x — assert 1 == 2 — FAILED", "2026-08-31T10:00:00Z"),
            asst("a2", "", "2026-09-01T10:00:00Z",
                 tools=[("mcp__atlassian__addCommentToJiraIssue", {"commentBody": spec})])])
        self.assertEqual(s.extract()["refreezes"], {"2026-09": {"after_build": 1, "before_build": 0}})

    def test_refreeze_then_red_in_one_message_is_before_build(self):
        s = Scope()
        spec = "🔒 FROZEN SPEC — x · feature · 2026-09-01\nticket: PROJ-1 · supersedes: 2026-08-30"
        s.write(SESS + ".jsonl", [asst("a1", spec + "\n\nRED: t.py::test_x — FAILED", "2026-09-01T10:00:00Z")])
        self.assertEqual(s.extract()["refreezes"], {"2026-09": {"after_build": 0, "before_build": 1}})

    def test_refreeze_shown_in_chat_and_written_by_tool_counts_once(self):
        s = Scope()
        spec = "🔒 FROZEN SPEC — x · feature · 2026-09-01\nticket: PROJ-1 · supersedes: 2026-08-30"
        s.write(SESS + ".jsonl", [
            asst("a1", "RED: t.py::test_x — assert 1 == 2 — FAILED", "2026-08-31T10:00:00Z"),
            asst("a2", "", "2026-09-01T10:00:00Z",
                 tools=[("mcp__atlassian__addCommentToJiraIssue", {"commentBody": spec})]),
            asst("a3", spec + "\n\nFrozen — change anything before we build?", "2026-09-01T10:01:00Z")])
        self.assertEqual(s.extract()["refreezes"], {"2026-09": {"after_build": 1, "before_build": 0}})

    def test_a_freeze_echoed_later_counts_once_at_its_first_time(self):
        s = Scope()
        spec = "🔒 FROZEN SPEC — x · feature · 2026-09-01\nticket: PROJ-1 · supersedes: 2026-08-30"
        s.write("a.jsonl", [asst("a1", "RED: t.py::test_x — FAILED", "2026-09-20T10:00:00Z"),
                            asst("a2", "quoting it: " + spec, "2026-09-20T11:00:00Z")])
        s.write("b.jsonl", [asst("b1", spec, "2026-08-31T10:00:00Z", sess="b")])
        self.assertEqual(s.extract(since="2026-09-01")["refreezes"], {})
        self.assertEqual(s.extract()["refreezes"],
                         {"2026-08": {"after_build": 0, "before_build": 1}})

    def test_build_line_template_does_not_mark_the_build_started(self):
        s = Scope()
        spec = "🔒 FROZEN SPEC — x · feature · 2026-09-01\nticket: PROJ-1 · supersedes: 2026-08-30"
        s.write(SESS + ".jsonl", [
            asst("a1", "Report progress as:\nBuild: <one line per slice>", "2026-08-31T10:00:00Z"),
            asst("a2", spec, "2026-09-01T10:00:00Z")])
        self.assertEqual(s.extract()["refreezes"], {"2026-09": {"after_build": 0, "before_build": 1}})


class ScoreTests(unittest.TestCase):
    def _out(self, data, labels):
        d = tempfile.mkdtemp()
        fh.write_extract(d, data)
        with open(os.path.join(d, "labels.json"), "w") as f:
            json.dump(labels, f)
        return d

    def _data(self, n_aug=6, n_sep=2):
        pairs = [{"id": f"a{i}", "month": "2026-08", "session": f"s{i}", "ts": "2026-08-01T00:00:00Z",
                  "human": "x", "ai_tail": "y", "interrupted": False, "decision": None, "label": None}
                 for i in range(n_aug)]
        pairs += [{"id": f"b{i}", "month": "2026-09", "session": f"t{i}", "ts": "2026-09-01T00:00:00Z",
                   "human": "x", "ai_tail": "y", "interrupted": False,
                   "decision": "Decision: z" if i == 0 else None, "label": None}
                  for i in range(n_sep)]
        recaps = [{"id": "r1", "month": "2026-09", "session": "s", "ts": "2026-09-01T01:00:00Z",
                   "key": "proj-1", "label": "divergences", "excerpt": "", "citable": True},
                  {"id": "r2", "month": "2026-09", "session": "s", "ts": "2026-09-02T01:00:00Z",
                   "key": "proj-1", "label": None, "excerpt": ""},
                  {"id": "r3", "month": "2026-09", "session": "q", "ts": "2026-09-03T01:00:00Z",
                   "key": "proj-2", "label": "built_to_spec", "excerpt": ""}]
        return {"pairs": pairs, "recaps": recaps, "refreezes": {},
                "meta": {"since": "2026-07-01", "until": "2026-09-30"}}

    def test_rates_small_n_and_pooled_first_pass(self):
        labels = {f"a{i}": ("accepted" if i < 4 else "corrected_ai") for i in range(6)}
        labels.update({"b0": "corrected_ai", "b1": "accepted", "r2": "built_to_spec"})
        res = fh.score(self._out(self._data(), labels))
        aug, sep = res["realignment"]["by_month"]["2026-08"], res["realignment"]["by_month"]["2026-09"]
        self.assertEqual((aug["n"], aug["counts"]["accepted"], aug["insufficient"]), (6, 4, False))
        self.assertTrue(sep["insufficient"])
        fp = res["decisions_held"]["spec_check_first_pass"]
        self.assertEqual((fp["n"], fp["counts"]["divergences"], fp["counts"]["built_to_spec"], fp["reruns"]),
                         (2, 1, 1, 1))
        dec = res["decisions_held"]["decision_lines"]
        self.assertEqual((dec["n"], dec["held"]), (1, 0))
        self.assertEqual(dec["by_month"], {"2026-09": {"n": 1, "held": 0}})
        self.assertTrue(all(len(c["session"]) <= 8 for c in res["realignment"]["citations"]))

    def test_cant_verify_check_does_not_take_the_first_pass_slot(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = [{"id": "r1", "month": "2026-09", "session": "s", "ts": "2026-09-01T01:00:00Z",
                           "key": "proj-1", "label": "cant_verify", "excerpt": ""},
                          {"id": "r2", "month": "2026-09", "session": "s", "ts": "2026-09-02T01:00:00Z",
                           "key": "proj-1", "label": "gaps", "excerpt": ""}]
        fp = fh.score(self._out(data, {}))["decisions_held"]["spec_check_first_pass"]
        self.assertEqual((fp["n"], fp["counts"]["gaps"], fp["counts"]["cant_verify"], fp["reruns"]),
                         (1, 1, 1, 0))

    def _pair(self, pid, label, decision_count=0, session="s"):
        return {"id": pid, "month": "2026-09", "session": session, "ts": "2026-09-01T00:00:00Z",
                "human": "x", "ai_tail": "y", "interrupted": False, "label": label,
                "decision": "Decision: z" if decision_count else None, "decision_count": decision_count}

    def test_exactly_min_n_is_enough_for_a_rate(self):
        data = self._data(n_aug=0, n_sep=0)
        data["pairs"] = [self._pair(f"p{i}", "accepted", decision_count=1) for i in range(fh.MIN_N)]
        data["recaps"] = [{"id": f"r{i}", "month": "2026-09", "session": "s", "ts": f"2026-09-0{i + 1}T00:00:00Z",
                           "key": f"proj-{i}", "label": "built_to_spec", "excerpt": ""} for i in range(fh.MIN_N)]
        res = fh.score(self._out(data, {}))
        sep = res["realignment"]["by_month"]["2026-09"]
        self.assertEqual((sep["insufficient"], sep["rates"]["accepted"]), (False, 1.0))
        self.assertFalse(res["decisions_held"]["spec_check_first_pass"]["insufficient"])
        self.assertFalse(res["decisions_held"]["decision_lines"]["insufficient"])

    def test_only_a_correction_breaks_a_decision(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = []
        data["pairs"] = [self._pair("p1", "changed_ask", 1), self._pair("p2", "rubber_stamp", 1),
                         self._pair("p3", "corrected_ai", 1)]
        dec = fh.score(self._out(data, {}))["decisions_held"]["decision_lines"]
        self.assertEqual((dec["n"], dec["held"]), (3, 2))

    def test_decision_lines_weight_by_count_per_reply(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = []
        data["pairs"] = [self._pair("p1", "accepted", 3), self._pair("p2", "corrected_ai", 2)]
        dec = fh.score(self._out(data, {}))["decisions_held"]["decision_lines"]
        self.assertEqual((dec["n"], dec["held"]), (5, 3))

    def test_citation_cites_session_prefix_only(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = []
        data["pairs"] = [self._pair("p1", "corrected_ai", session=SESS)]
        (cite,) = fh.score(self._out(data, {}))["realignment"]["citations"]
        self.assertEqual(cite["session"], "11111111")

    def test_deterministic_recap_label_beats_a_model_label(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = data["recaps"][2:]
        fp = fh.score(self._out(data, {"r3": "gaps"}))["decisions_held"]["spec_check_first_pass"]
        self.assertEqual((fp["counts"]["built_to_spec"], fp["counts"]["gaps"]), (1, 0))

    def test_null_label_fails_loudly(self):
        labels = {f"a{i}": "accepted" for i in range(6)}
        labels.update({"b0": "accepted", "b1": None, "r2": "built_to_spec"})
        with self.assertRaises(ValueError):
            fh.score(self._out(self._data(), labels))

    def test_ride_along_decision_pairs_stay_out_of_realignment(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = []
        data["meta"].update({"since": "2026-09-06", "until": "2026-09-30",
                             "pairs_total_by_month": {"2026-09": 40}})
        data["pairs"] = [{**self._pair(f"p{i}", "accepted"), "in_sample": True} for i in range(5)]
        data["pairs"].append({**self._pair("d1", "corrected_ai", 1), "in_sample": False})
        res = fh.score(self._out(data, {}))
        sep = res["realignment"]["by_month"]["2026-09"]
        self.assertEqual((sep["n"], sep["total"], sep["counts"]["corrected_ai"], sep["partial"]),
                         (5, 40, 0, True))
        self.assertEqual(res["decisions_held"]["decision_lines"]["held"], 0)

    def test_first_pass_skips_keys_checked_before_the_window(self):
        data = self._data(n_aug=0, n_sep=0)
        data["prior_keys"] = ["proj-2"]
        fp = fh.score(self._out(data, {"r2": "gaps"}))["decisions_held"]["spec_check_first_pass"]
        self.assertEqual((fp["n"], fp["reruns"], [c["ref"] for c in fp["citations"]]), (1, 2, ["PROJ-1"]))

    def test_spec_file_key_cites_the_session_not_a_fake_ticket(self):
        self.assertEqual(fh._ref({"key": "phase-2.md", "session": SESS, "citable": False}), "11111111")
        self.assertEqual(fh._ref({"key": "proj-4 comment 9", "session": SESS, "citable": True}), "PROJ-4")
        self.assertEqual(fh._ref({"key": "acct-12345", "session": SESS, "citable": False}), "11111111")

    def test_a_ticket_only_check_reruns_a_freeze_but_a_new_freeze_is_a_first_pass(self):
        data = self._data(n_aug=0, n_sep=0)
        data["recaps"] = [{"id": f"r{i}", "month": "2026-09", "session": "s", "ts": f"2026-09-0{i + 1}T00:00:00Z",
                           "key": k, "label": "gaps", "excerpt": ""}
                          for i, k in enumerate(["proj-4 comment 10", "proj-4", "proj-4 comment 11"])]
        fp = fh.score(self._out(data, {}))["decisions_held"]["spec_check_first_pass"]
        self.assertEqual((fp["n"], fp["reruns"]), (2, 1))

    def test_missing_or_invalid_label_fails_loudly(self):
        with self.assertRaises(ValueError):
            fh.score(self._out(self._data(), {"a0": "accepted"}))
        labels = {f"a{i}": "accepted" for i in range(6)}
        labels.update({"b0": "accepted", "b1": "shrug", "r2": "built_to_spec"})
        with self.assertRaises(ValueError):
            fh.score(self._out(self._data(), labels))


if __name__ == "__main__":
    unittest.main()
