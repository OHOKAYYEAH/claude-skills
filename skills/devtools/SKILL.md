---
name: devtools
description: >-
  Drive the Chrome DevTools MCP to QA, debug, or iterate in the browser: verify
  UI changes, reproduce bugs, chase console/network errors, walk drafted QA
  scenarios. The browser primitive /qa and ship composites chain into; degrades
  gracefully with no MCP or dev server. Local by default; pass dev/stage/prod or
  a URL.
disable-model-invocation: false
argument-hint: "[optional focus, e.g. \"the new modal\"] [optional target: local|dev|stage|prod or a URL]"
---

Use the Chrome DevTools MCP to verify, debug, or iterate on the current scope of work in the browser. Pick the mode that's most useful given context — the skill doesn't prescribe a single path:

- **Just shipped a UI change?** Verify the golden path and edge cases.
- **Chasing a reported bug?** Reproduce it, then inspect network/console/DOM state to localize.
- **Iterating?** Open the page, make changes elsewhere, refresh, observe, repeat.
- **Pre-checkin pass?** Walk the affected flows end-to-end.
- **Walking a drafted scenario list?** (e.g., from `/qa`) Step through each scenario and report pass/fail per item.
- **Performance smell?** Run a Lighthouse audit.

This skill is also the execution primitive that other skills chain into when they need browser verification — currently `/qa` (for walking drafted scenarios) and project ship composites (for their QA-and-land leg). `/work` deliberately has **no** browser-QA phase — the pairing is `/work` then `/qa run`.

## Step 0: Resolve the target environment

Decide which environment to drive, in this precedence:

1. **Explicit** — a target token (`local` / `dev` / `stage` / `prod`) or a raw URL in `$ARGUMENTS` wins.
2. **Session context** — if the conversation has already established the target (you've been debugging dev, a deployed URL is in play, the user said "on dev"), use that. Don't make them re-state it.
3. **Default** — local dev.

Resolve a named env to a base URL from the project's CLAUDE.md / docs (it documents local ports, and deployed env URLs where applicable). If a named env has no documented URL, ask once for it or accept a raw URL from the args. Record the resolved target in the Step 3 report so it's unambiguous which env you drove.

## Step 1: Availability gates

Three things must be in place. Check them in order; recover what you can; if anything is still missing, surface and stop.

1. **MCP tools loaded.** Confirm `mcp__chrome-devtools__*` tools are available in this session.
2. **Target reachable.** Hit the resolved target's health endpoint or root (for `local`, the dev server port from CLAUDE.md). If it doesn't respond, that's a gate failure.
3. **Debug browser on the MCP port.** Try `curl -sf http://127.0.0.1:${CHROME_DEBUG_PORT:-9222}/json/version`. If nothing answers, launch one — **the binary differs per machine, so probe, don't assume:**
   - **A real Chromium on PATH** (`command -v chromium-browser || command -v chromium || command -v google-chrome`) → the workstation case. Launch it with `--remote-debugging-port=${CHROME_DEBUG_PORT:-9222}`, give it a second, re-check. The user often already has one up on that port — attach to it rather than spawning a second.
   - **No Chromium binary at all** → a headless-only box. Use a headless launcher the project or machine provides (e.g. one that boots Playwright's `chrome-headless-shell` on a throwaway per-port profile). If none exists, that's a gate failure — say so rather than guessing at a binary.

   If your setup runs parallel sessions with one browser each, `$CHROME_DEBUG_PORT` is that session's port, not 9222 — the MCP binds it at launch and can't be re-pointed mid-session.

If any gate is still failing after recovery attempts, output one of:

> DevTools unavailable — MCP not loaded in this session.
> DevTools unavailable — target not reachable at \<url\>.
> DevTools unavailable — Chromium debug bridge could not be started.

…and STOP. Don't fake the verification. This is the expected outcome in worktrees with no local server; the calling skill (e.g., `/qa run`) will record it and continue.

## Step 2: Drive the browser

Once the gates pass:

- **Open your own plain tab** — `new_page` without `isolatedContext`. Parallel sessions share one browser, and a tab already keeps you off their pages. `isolatedContext` is a separate cookie jar that Chrome always opens in a **new window**; use it only when you must be signed in as a *different user* than another session might be on the same host (cookies are per host, not per port, so `localhost:3000` and `:5173` share a login).
- Navigate to the relevant page.
- Sign in if the flow requires it. The project may have permissioned test credentials documented in CLAUDE.md — use those. Where the project authorizes them, a `fill` that puts a test-cred value in the transcript is fine; never stall a pass to avoid it.
- Interact: click, fill forms, navigate, take snapshots.
- Watch: console messages, network requests, dialog/error states.
- For specific bugs: reproduce first, then narrow the cause via inspection.
- **Screenshot every state worth showing, to a file, as you reach it.** The browser is already on the page and authenticated, so a capture costs one call here and is unrecoverable later — a caller that wants visual evidence (`/before-after`, and the ship composites through it) harvests what this pass produced rather than re-driving the browser. Name them in capture order (`<ticket>-NN-<state>.png`), and note the viewport: a layout that holds at 1440px can still strand at ~1900px, so a wide capture earns its own frame. Record the paths in the Step 3 report.
- **Frames go to a git-ignored evidence folder in the main checkout (e.g. `docs/local/<ticket>/`), by absolute `filePath`** — never a bare filename (it resolves against the MCP server's cwd, often the repo root) and never a linked worktree (removing the tree deletes its ignored files). QA frames can carry real customer data, so they are never committed.

Once the target token/URL is consumed by Step 0, the rest of `$ARGUMENTS` is your focus hint. If empty, use conversation context. If it says "performance" or "lighthouse", run an audit. Otherwise treat as a flow/feature/bug name to scope on.

### Driving inputs on data-heavy / React pages

The `fill` tool is the default for form inputs (it handles focus/blur like a real user) — but it needs a `uid` from `take_snapshot`, and on a data-heavy page (a long table/list) the a11y snapshot can blow the token budget, making `take_snapshot` (and `wait_for`, which also returns the tree) and thus `fill`-by-uid impractical. When that happens, drive inputs with `evaluate_script` and read state back with targeted DOM queries instead of snapshotting the whole page.

Setting a **React controlled input** from `evaluate_script` has two non-obvious gotchas (both cost a wasted round-trip if missed):

- Set the value through the element prototype's **native setter**, then dispatch `input` — assigning `el.value = x` alone doesn't notify React's `onChange`:
  `Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value').set.call(el, x); el.dispatchEvent(new Event('input',{bubbles:true}))`
- For a field that **commits on blur** (e.g. a commit-on-blur number field), `el.blur()` / `new FocusEvent('blur')` will **not** fire React's `onBlur` — React delegates blur via the native **`focusout`** event. So: `el.focus()` first, set the value, then `el.dispatchEvent(new FocusEvent('focusout',{bubbles:true}))`. For a `<select>`, set the value via the setter and dispatch `change` (its `onChange` fires on native `change`).

After driving inputs, give React a tick to re-render (`await new Promise(r=>setTimeout(r,~400))`) before reading results. `[workaround] — revisit if the chrome-devtools MCP gains a snapshot-free `fill`-by-selector, or `fill` stops needing a full-page snapshot.`

A bare `el.click()` from `evaluate_script` often won't open a React popover or dropdown. Use the MCP `click` by `uid` — snapshot a *light* page that renders the same trigger if the current one is too heavy — or dispatch the full `pointerdown → mousedown → pointerup → mouseup → click` sequence and await a tick.

## Step 3: Report

Tight summary at the end:

```
### DevTools Pass
**Status:** <✅ verified / ⚠️ issues found / 🛑 unavailable>

- **Target:** <env + base URL driven, e.g. "dev — https://dev.example.com">
- **Verified:** <flows / behaviors / screens that passed> (or "none")
- **Issues found:** <bugs, regressions, console errors, network failures, with file:line if known> (or "none")
- **Fixed inline:** <what you patched during the pass> (or "none")
- **Outstanding:** <still broken, with reproduction notes> (or "none")
- **Frames:** <screenshot paths in capture order, with viewport> (or "none captured")
```

## Guardrails

- **Never echo secret values into chat.** Test credentials the project explicitly designates for QA are the exception; real secrets stay no-echo, extracted via shell (e.g. `V=$(grep -E '^KEY=' file | cut -d= -f2-)`). Use shell variables; `.env`/`.env.local` stay off-limits unless the project explicitly authorizes a `.env.claude`-style file with accepted-leak semantics. **Never call `get_network_request` on an authenticated request** — it prints every request header, the `Authorization` bearer included, even with `responseFilePath` set. Confirm a call with `list_network_requests` (URL + status) and read its result from the rendered page, the DB, or an in-page read that returns only the body. A sign-in link or other bearer URL reaches the browser through a shell variable (e.g. CDP `PUT /json/new?<url-encoded>`), never as a tool parameter.
- **Don't auth real broker / production accounts.** Test users only. If a flow needs real auth, flag it in Outstanding and stop.
- **Prod/stage is read-mostly.** When the target isn't local, avoid mutations with blast radius beyond a test user (real billing, broker connections, other users' data). Test-user state changes are fine; anything riskier goes in Outstanding, not executed.
- **No commits, no pushes, no PR opens.** Verification, not shipping.
- **Stay scoped.** Bugs unrelated to the current work go in Outstanding — don't sprawl into fixing them mid-pass.
