---
name: ticket
description: >-
  File (or find) the tracker ticket for a unit of work: dedupe-search first,
  create only if nothing covers it, set sprint and lane, return the key
  ("already tracked as X" is success). Fire when work starts or is decided with
  no known ticket, or on "file a ticket for this". Never speculative or bulk.
  NOT /triage (decides which of several findings deserve a ticket) or closing
  tickets.
disable-model-invocation: false
argument-hint: '<scope / work description, or a known ticket id to verify> [tokens: "file" backlog-only, no In Progress · "check" dedupe search only, create nothing]'
---

A unit of work should exist on the board before it exists in prod. The failure
this prevents is quiet: work that starts ad-hoc — a hotfix, a build off a Slack
ask, a follow-up decided mid-session — never gets a ticket, so it's invisible to
everyone who reads the board, and the close-out step that *would* have tracked it
has nothing to close. The standing rule: a decided follow-up gets FILED in the
session it is decided; a comment on some other ticket is durable but UNTRACKED.

The discipline is **search before create**. Most of the time the right outcome is
"already tracked as X" — that's the skill succeeding, not failing.

## 0. Guard

- **Never file speculatively.** A ticket is for work that is being done or has
  been decided — not for an idea, a maybe, or a caveat.
- **Never bulk-file — route a list through a triage pass first.** If the input is
  several findings rather than one decided unit of work, a batch-triage step
  (`/triage`, if installed) owns the cut (fold / merge / file / drop) and hands
  back only the survivors. Filing the list yourself is the bypass that makes this
  guard unreachable: a composite skill calling `/ticket` once per finding never
  sees a list, so it never trips. Five
  tickets nobody will prioritize is noise that makes the board less trustworthy,
  not more.
- **`check` token** → run steps 1–2 and report the verdict; create nothing.

## 1. Resolve the tracker (by cwd)

Read the cwd repo's `CLAUDE.md`, walking up to the repo root.

| cwd condition | where the ticket goes |
|---|---|
| CLAUDE.md declares a **Jira** project | create via the Atlassian MCP. **Resolve site + cloudId at runtime — never hardcode one:** this skill is shared across projects and Atlassian sites, and a wrong cloudId 400s as "not explicitly granted". Call `getAccessibleAtlassianResources`, or read the cloudId from the project's own CLAUDE.md / memory |
| CLAUDE.md declares an **in-repo `tickets/`** tracker | write `tickets/<PREFIX>-NNN-slug.md` (next seq), commit + push per the repo's convention |
| a **git repo with NO tracker** | surface that; offer to set one up (`/setup-ticketing`, if installed — one confirm), then file. Declined → say so and stop; don't invent a home |
| a **non-repo / homeless** cwd | ask where it belongs (e.g. a personal tickets repo, if you keep one); don't invent a home |

**Pick the right project when a site has several.** A tracker split by area
(e.g. by team or component) routes on what the work *is*: file it in the project
that owns the code or behavior it changes. When it genuinely straddles two, file
in the one whose board you actually work from and note the other in the body.

## 2. Dedupe search — the load-bearing step

Search the tracker for anything already covering this scope **before** drafting
anything. Search on the distinctive nouns (feature name, error string, customer /
order / account number, ticket ids mentioned in the ask), not a paraphrase of the
summary you were about to write.

Keep the payload small — a wide Jira search overflows context fast. Narrow
`fields` to key/summary/status (never `*all`), cap `maxResults`, and search the
likely projects rather than the whole site.

Classify into exactly one:

- **Exists** — a ticket already covers this. Report the key and stop; if its lane
  is wrong for what's about to happen, fix the lane (step 4) and nothing else.
- **Partial overlap → subsume** — an older/narrower ticket is a subset of this
  work. Prefer *widening the existing ticket* over minting a new one. If the new
  scope is genuinely bigger, create it, then link the old one (`createJiraIssueLink`; `createIssueLink` on a v1 connection)
  and close it as superseded with a comment saying by what — never leave a silent
  duplicate.
- **None** — proceed to create.

Say which verdict you reached and on what evidence. "I searched and found
nothing" is a bounded claim; "there's no ticket for this" is an absolute one, and
the absolute one is how duplicates get filed.

## 3. Create

- **Summary** — what the work *is*, readable by someone who wasn't in the
  session. Not the session's name, not a ticket-speak template.
- **Body** — whatever spec already exists is the body: a feature spec block, an
  investigation's findings + proposed fix, or the scope statement that prompted the
  ship. Don't re-derive it and don't pad it. Include acceptance criteria when the
  work has a testable outcome — QA reads acceptance criteria off the ticket, not the PR.
- **Type** — the project's own convention (commonly Story for new capability,
  Bug for a regression or production incident, Task for cleanup).
- **Assignee** — leave it unassigned unless the ask names someone. Assignees
  change, so an auto-assignee goes stale. Tools that answer "what's
  mine" must count unassigned tickets rather than filter on assignee alone.

Omit fields the project rejects rather than fighting them (some projects'
priority field, for instance, refuses both object and string forms on create).

## 4. Make it visible — sprint + lane

A created ticket is not yet a *tracked* ticket. Two things hide one:

- **Sprint.** On a scrum board, issue-create APIs do **not** auto-assign the
  active sprint, so a fresh ticket is absent from the board until the sprint field
  is set explicitly. Resolve the active sprint at runtime — query
  `project = <KEY> AND sprint in openSprints()` and read the sprint field off a
  result, taking the entry whose `state` is `active`. The field holds an issue's
  **full sprint history**, closed ones included, so filter on state rather than
  taking the first element; setting a closed id hides the ticket exactly like
  setting none. Sprint ids are **per-board** — two boards running at once have
  two different ids. Never carry an id over from memory or a previous run.
- **Lane.** Use a status the board actually maps to a visible column. An exotic
  or unmapped status makes the ticket vanish from view while looking correct in
  the API — check the project's own conventions before reaching for one. Read the
  transition id from `listJiraIssueTransitions` (`getTransitionsForJiraIssue` on a
  v1 connection) rather than hardcoding it; ids differ per workflow.

Default lane is **In Progress** when the work starts now (the build-it-now case). With
the **`file`** token — a follow-up, a deferred fix, something decided but not
being built today — leave it in the project's backlog/To-Do lane instead. Filing
tomorrow's work as In Progress lies about what's actually being worked.

## 5. Report (glanceable)

One line, then only what's needed:

    🎫 <TICKET-ID> — <created | already tracked | widened | superseded N> · <lane> · <sprint name>

Then the URL, and — if you subsumed or triaged anything — one line on what you
folded in or deliberately left as a comment. Nothing else.

When chained, that key is the return value: the caller uses it to link the PR,
comment progress, and close the ticket at the end of the flow.
