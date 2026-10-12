---
name: smoke-prod
description: >-
  Read-only, non-mutational smoke test against PRODUCTION of a feature you just shipped:
  confirms the deploy didn't break prod and, for read-only features, that the feature renders
  and behaves on prod. The LAST, lightest layer; real testing already happened via /qa on
  local, dev and staging. It NEVER mutates prod and NEVER logs in: you log into prod in the
  debug browser, and the skill attaches to that session for read-only checks. Fire after a
  prod deploy (the tail of /rollout, or /merge-and-verify on a prod-branch merge), or on
  "smoke-test prod", "sanity-check prod", "/smoke-prod FEATURE". NOT a substitute for /qa
  (where behavior is proven, pre-prod) and NOT for write paths on prod. PRODUCTION-ONLY:
  "smoke-test staging" or "read-only checks against dev/staging" is a /qa run, not this skill.
  Project-scoped example (genericized).
disable-model-invocation: true
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate one idea: **the post-deploy prod check is a separate, deliberately weak skill — attach to a session the human logged into, look but never touch, and treat partial coverage as a complete result** — so that "test prod" can never quietly become mutational QA on customer data. The real version names one org's prod hosts; everything identifying here has been genericized. Don't install it — adapt the pattern.

# /smoke-prod — read-only production sanity check

You just shipped something to prod. The real QA already happened before it got there (`/qa` local → dev → staging, plus review + tests). **This skill is the thin safety layer on the other side of the deploy:** attach to a browser the user has *already logged into prod with*, drive **read-only** navigation, and confirm the newly-deployed feature is live, renders correctly, and hasn't visibly broken prod. Then report a smoke verdict and stop.

The whole reason this is a separate, tightly-scoped skill: **prod is real customer data and real side effects.** The discipline is non-negotiable — you look, you never touch.

## Environment scope — PROD ONLY (do not use on dev/staging)

This skill exists **only** because prod is untouchable. **Dev and staging are not** — they take real, mutational QA via `/qa` (drive the actual flows, submit forms, exercise write paths). Staging in particular is the valuable QA target because it has **prod-like data**. All behavioral QA happens pre-prod on dev/staging; there is intentionally **no "QA-prod" skill**. So: never reach for `/smoke-prod` — or a "read-only checks against staging/dev" framing — as a stand-in for QA on a non-prod env. If the env is dev or staging, the answer is `/qa` (targeted at that env), full stop. `/smoke-prod` fires *only* after code is live on **production**.

## The safety model (read this first — it's the point)

Three hard invariants. If you can't honor all three, stop and say so.

1. **You never log into prod.** The user logs into prod in the browser themselves (the skill has no prod creds and must never use, request, or echo any). You *attach* to that already-authenticated session via the Chrome DevTools MCP. If the browser isn't on an authenticated prod session when you look, **stop and ask the user to log in** — don't try to drive the login.
2. **You never mutate prod.** No request that creates, updates or deletes anything (no GraphQL `mutation`, no POST/PUT/PATCH/DELETE to a REST write route). Reads are fine, including a report or search form you fill in and submit, **once you've proven what it fires is a read** (the test is below). Entry and edit forms stay untouched, even ones you mean to abandon: they can autosave, fire a lookup or submit on a stray Enter. When you can't prove an interaction only reads, treat it as a write and **don't do it**.
3. **You never use a prod write credential or the DB write path.** If a check genuinely needs data-shape confirmation, that's a separate SELECT-only prod DB query (if your project has one) — not this skill clicking around.

### Read-only interactions — ALLOWED
- Navigate to prod **view** URLs (GET pages), reload, back/forward.
- `take_snapshot`, `take_screenshot`.
- Read `console` messages and `network` requests (inspect for errors/failed calls). **Status codes via `list_network_requests` only — never `get_network_request` on an authenticated prod call:** it prints request headers inline even when bodies go to files, so the user's prod bearer token lands in the transcript. For errors an API returns inside a 200 (GraphQL servers commonly do), reload with an `initScript` that wraps `fetch`, clones each API response and `console.error`s any error payload — it observes the app's own calls, issues none. `[workaround]` — drop when the MCP can redact headers.
- `evaluate_script` for **read-only** DOM / state inspection (reading text, computed styles, element presence) — never a script that calls an app mutation or a REST write route.
- **A hand-written same-origin API read** via `evaluate_script` `fetch` (e.g. a pre-deploy "before" baseline the UI can't capture once the deploy lands), **non-mutational only**. It must pass the same read-only test as a UI-run query (below): declared a read, handler proven read-only. Never a write operation, never `get_network_request` to read it (the script returns the body). Keep it narrow (one record, one date), since the result is real customer data in the transcript.
- Clicking that only **reads/reveals**: switching a tab, expanding a section, opening a *view* (a record detail page), pagination, a client-side filter/sort that doesn't persist.
- **Running a read-only query or download**: a report modal's Download/Run, a search box, a report's date or filter fields. You may type into those fields (`fill`, `type_text`, `press_key`, a native-setter `evaluate_script`) and submit, after the read-only test passes:
  - **Client:** the call is one of the API's read operations (a query, or a GET), not a mutation or write call.
  - **Server:** the operation is declared a read in the API's schema or routes, **and** its handler only reads. Grep it for create/update/upsert/delete calls, the ORM's raw-SQL calls, and email or job calls, since a "read" can still have side effects.
  - Name the operation and the evidence in the smoke verdict (e.g. "`OrderSummary`: declared a read, handler only selects").
  - A download lands in `~/Downloads` with real prod data. Leave it there for the user, and never attach, upload or send it anywhere.

### Mutational — FORBIDDEN
- Clicking **save / approve / decline / create / update / delete / send** or any submit that writes (a GraphQL `mutation`, or a POST/PUT/PATCH/DELETE to a REST write route).
- **Input into any entry or edit form** (a new record, a new order, an edit screen), submitted or not. `upload_file` and `drag` are never called on prod, and `handle_dialog` only ever **dismisses**.
- Opening an entry form to "try" the change (a new record, a new order, an edit screen). A form-behavior fix is proven on staging; on prod you view the list or a read-only detail page, nothing more.
- Triggering an email, a job, a batch run, a document generation that writes.
- Anything that changes a real customer's records or account state.
- **Logging in.** That's the user's.

**The line:** interact only in ways that *read*. The moment a step would *change* something, stop — that path was already proven pre-prod; note it as "verified pre-prod, not re-exercised on prod" and move on.

## Coverage is deliberately partial — that's fine

Some features can't be fully verified with read-only actions on prod, **and that's okay** — the pre-prod `/qa` ladder is what proves behavior. Two shapes:

- **Read-only feature** (a report, a view, a computed display, a new column): you *can* smoke it end-to-end read-only — open it on prod and confirm it renders correctly with real data. Do that.
- **Write feature** (a form submit, an approval, a state change): you **cannot** exercise the write on prod. Smoke the *read-only surface* of it — does the page/route load, does the new UI render correctly, are there console/network errors, did the deploy land — and explicitly record that the write path itself was verified pre-prod, not on prod.

A smoke test that says "the deploy is healthy and the read-only surface looks right; the write path was proven on staging" is a **complete** `/smoke-prod` result, not a partial failure.

## Workflow

### 1. Scope
Identify the shipped feature/change from the argument or conversation, and what "still healthy" looks like for it: which prod route(s) to view, what should render, and — critically — which parts are read-only-verifiable vs. write-paths to leave alone.

### 2. Confirm the browser is on an authenticated prod session
Attach via the Chrome DevTools MCP (`${CHROME_DEBUG_PORT:-9222}`; launch Chromium on that port only if nothing's there — but **the user still does the prod login**). `list_pages` / navigate to a known prod route and take a snapshot. Resolve each user-facing app's prod host from its prod config (e.g. a base-URL setting) rather than from memory.

If the snapshot shows a **login screen** (or an unauthenticated redirect), **stop and ask the user to log into prod** in the browser — always naming the app and its prod URL (e.g. "log into app A prod, `https://app-a.example.com`"); someone switching between several apps can't tell which one you mean — then resume. Do not fill the login.

### 3. Drive the read-only smoke
Walk the scoped view(s) using only the ALLOWED interactions. For each:
- Confirm the route loads (no white screen / error boundary / 500).
- Confirm the feature's read-only surface renders as expected against real prod data.
- Capture a screenshot for the record.
- Check `console` + `network` for errors (failed API calls, 4xx/5xx, thrown exceptions).

The instant a useful next step would require a mutation, stop that thread and note it as pre-prod-verified.

### 4. Smoke verdict (terminus)

```
### Prod Smoke — <feature>
**Session:** <confirmed authenticated prod session as <who>, or "stopped — asked the user to log in">
**Checked (read-only):** <routes/surfaces viewed + what rendered correctly>
**Console / network:** <clean / the specific errors seen>
**Not exercised on prod:** <write paths deferred to pre-prod /qa — one line, or "none (read-only feature, fully smoked)">
**Verdict:** <✅ healthy — deploy live, nothing visibly broken / ⚠️ anomaly: <what> / 🛑 broken: <what>>
```

If ⚠️/🛑, be concrete about the observation (route, console error, what rendered wrong) — and remember a prod break is live, so surface it loudly and stop; a fix goes through a fresh `/ship` (or hotfix) cycle, never a prod poke.

## Guardrails
- **The three invariants are absolute:** no prod login, no mutation (reads only, proven from code), no write credential. Unsure whether a step writes → it writes → don't. No caller, token, or "just this once" relaxes them.
- **Attach, don't authenticate.** The user owns the prod login; you inherit the session. No login screen driving, ever.
- **Read-only ≠ full QA.** Don't reach for a mutation to "complete" a test — partial read-only coverage is the expected shape on prod. Behavior is proven pre-prod.
- **Runs inline against the live browser** (like `/devtools`, `/qa`) — it can't run in a forked subagent, because it needs the real authenticated session. Don't call it from inside a fork.
- **Data-shape questions go to a read-only prod DB query** (SELECT-only, if your project has one), not to clicking around prod.
- **One terminus: the Smoke verdict.** Don't trail off; end on the block.
