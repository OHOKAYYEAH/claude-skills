# /spec-check — reconstructing a spec that was never frozen

Only for the fallback path: no `🔒 FROZEN SPEC` exists, so the agreed ask has to be
rebuilt from where it was discussed. The output is the same shape `/spec` writes
(in-scope items, success criteria, a deferred list), which step 3 of the skill then
compares against. Say in the recap that the spec was reconstructed, not frozen.

## Reconciling an ask that evolved

The ask usually changed over time. Capture how it changed, not just the latest message:

- **Issue tracker** — the ticket, all its comments, AND the **changelog**. Titles and
  descriptions drift from the real rule (a rewritten summary, a paraphrase that's subtly
  wrong). Compare the original description with the current one.
- **Email / chat** — often where the decision was actually *settled*, while the tracker
  just says "in progress." A quiet channel doesn't mean no decision; check the others.
  Find the message that settled it: who, when, and the exact wording.
- **Docs the ticket points at** — in-repo spec files, designs, wiki pages. A ticket often
  links the rule rather than restating it, so the ticket alone is only half the spec.

Result: numbered in-scope items that are precise about boundaries, plus an explicit
deferred list. Quote the language that settled each one, with a citation (ticket comment
date, email sender and date, chat channel and date).

## Per-project sources of truth

Keyed by repo: match the `git rev-parse --show-toplevel` basename against the headings
below. Replace the two example entries with your own projects.

Rules:
- Pull **every REQUIRED** source. If a REQUIRED source's MCP isn't connected this
  session, return 🛑 and name the missing source. Never give a verdict from a partial set.
- Pull **OPTIONAL** sources when the feature calls for them (e.g. a design tool
  for a UI ticket, a docs space when the ticket links one).
- **NOT a spec source** = don't use it to establish the ask. It may still be
  useful in step 2 ("what was built") — e.g. a DB/deploy MCP shows the built
  state, not the requirement.
- Project not listed here → discover the connected MCPs, ask which are the spec
  sources, and offer to add an entry.

---

## example-team-app   (team project, stakeholder-driven)

**REQUIRED spec sources**
- **Issue tracker** — e.g. Jira via the Atlassian MCP, project **<KEY>**.
  The primary ask + its evolution live here. Read the **changelog**: the title/
  description drift from the real rule (rewritten summaries, a paraphrase that's
  subtly wrong).
- **Email** — a mail MCP (e.g. Outlook or Gmail). **Decisions often live in email,
  not chat** — the settling call is frequently an email thread. Search mail for the ticket id + domain terms.
- **Chat** — e.g. a Slack or Teams MCP. Threads on the ticket/feature. Don't assume
  the decision is here; a quiet channel ≠ no decision (check email).

**OPTIONAL spec sources** (pull when relevant)
- **Wiki** — e.g. Confluence. Spec/requirement pages a ticket references.
- **Design tool** — e.g. a Figma MCP. For a UI/UX ticket the **design is the spec** — pull it
  to check the build against the intended layout/flow.

**NOT spec sources** (skip for the ask; may inform "what was built")
- Error monitoring, CI/deploy, browser-automation MCPs (runtime QA — that's
  /qa's job).

**Who makes the calls:** <the product owner / stakeholders, by role>. (The person who
*settles* a spec is usually one of these.)

---

## example-solo-app   (solo build)

**REQUIRED spec sources**
- **Jira** — Atlassian MCP (committed project `.mcp.json`), project **<KEY>**.
  Ticket + comments + changelog = what/why/deferrals. In-app user feedback may
  land here as issues with a `user-feedback` label.
- **In-repo spec docs** — local files, *not* an MCP. When a project deliberately
  keeps specs in the checkout, tickets *reference* these rather than restating
  them — so read the linked doc, not just the ticket (e.g. a `SPEC.md`, a
  `reference/*.md` model doc, per-package `CLAUDE.md` constraints).

**OPTIONAL spec sources** (pull when a ticket points at them)
- **Gmail** — claude.ai connector. Only when a decision was settled over email
  (vendor/partner threads). Rarely holds core product decisions on a solo build.
- **Google Drive** — claude.ai connector. Only if a ticket/doc references a Drive
  doc/sheet.
- A second connector that fronts the *same* Jira/Confluence (e.g. Atlassian
  Rovo) is a fallback only if the primary MCP is down; don't double-count it.

**NOT spec sources** (skip for the ask; may inform "what was built")
- The database, deploy/infra tooling, third-party data-vendor MCPs (they
  describe vendor data, not the product), browser automation, calendar.

**Who makes the calls:** the solo developer. User feedback informs, but they own
every product decision.

**Gotchas:**
- Decisions live in **two** places: the Jira ticket (what/why/deferral) AND the
  linked in-repo `.md` (the detailed model). Reading only the ticket misses half.
- claude.ai connectors (Gmail/Drive/Calendar) are interactive-OAuth — they may be
  absent in a headless session until re-auth; degrade gracefully.
