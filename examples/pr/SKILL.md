---
name: pr
description: Commit, push, and open a PR for the current branch — emitting a copy-friendly PR title + description + URL. The land-leg leaf that /qa-and-pr and /ship call. No outer markdown fences around the description so pasting into the git host's PR form is frictionless. Encodes one project's branch model, commit conventions, and PR-helper flow. Project-scoped example (genericized)
disable-model-invocation: true
argument-hint: [optional scope hint / extra context to fold into the PR body]
---

> **Read-only example.** This is a *project-scoped* skill, shown to illustrate how the generic atoms get a thin, repo-specific landing leaf. Don't install it — adapt the pattern.

You're at the "open a PR" step. Do the commit + push (if needed), open the PR, then emit the PR materials in a strictly-disciplined output shape the user can paste into the git host without cleanup.

## Hard rules (read these first)

1. **No outer ``` fence around the description.** The description body is raw markdown that pastes directly into the PR form's description field. Stripping an outer fence inside a web textarea is painful — don't make the user do it. Inner fences for actual code blocks are fine.
2. **No prose around the output.** No "here's your PR" intro, no "let me know if tweaks needed" outro. The whole response is the PR materials.
3. **PR target is the project's integration branch**, not the default branch blindly — gitflow repos merge integration → default on a release cadence. Resolve it from the project's branch table (e.g. `develop` in a gitflow repo, `main` in a trunk-based one). Verify from the repo's own `CLAUDE.md` if one exists.
4. **Don't PR from an integration branch.** If the current branch is an integration or default branch, stop and ask what the user meant.
5. **Open the PR via the PR helper**, not by hand in the browser. The paste-ready text block below is the **fallback** — emit it only when the helper can't open the PR (no token, a PR already open for this branch, API error). Use the host's own CLI if it has one; if it doesn't, a small REST helper fills that gap.

## Workflow

### 1. Survey state (parallel)

- `git status` — uncommitted/untracked
- `git branch --show-current`
- `git log --oneline -10` — recent commit style
- `git diff` and `git diff --staged` — the change itself
- `git log @{u}..HEAD --oneline 2>/dev/null` — unpushed commits
- `git rev-parse --abbrev-ref @{u} 2>/dev/null` — is upstream set?
- `git remote get-url origin` — to construct the PR URL

### 2. Commit if dirty

- Draft a conventional-commit-style message matching the repo's recent style.
- Respect commitlint where it enforces scopes (one repo may allow only a fixed scope list; another may have no commitlint at all).
- **Stage by path, never `git add -A`** — the checkout may be shared with a parallel session. Don't stage untracked files unless they're clearly part of this PR — ask if ambiguous.
- Use heredoc for the message. End it with the commit attribution lines from this session's system reminder, which name the current model. Never hardcode a model name here.
- If a pre-commit hook fails, fix the issue and create a **new** commit — never `--amend`.

### 3. Push if needed

- No upstream → `git push -u origin <branch>`
- Ahead of upstream → `git push`
- Up to date → skip
- For the **fallback** URL only (helper failed): capture the "Create pull request for ..." line from push output, or construct the host's new-PR URL for the branch.

### 4. Open the PR (the PR helper)

The PR helper is a small script shipped next to this skill: it reads credentials from a local config file, parses owner/repo from `origin`, and POSTs the PR through the git host's REST API (scoped API token — the token never enters argv). It takes a source branch, a **required** destination branch, a title, a description file, and a `--dry-run` flag.

1. Write the crafted description (the raw markdown body from step 5) to a temp file and pass it as the description file, so markdown / quotes / `$` survive unescaped.
2. Call the helper with `source = <current-branch>`, `dest = <integration-branch>`, the title, and the description file.
   - **The destination is required** — the helper refuses to default, because a repo whose host default is a frozen release branch would otherwise silently get PRs aimed at it. Use the same integration branch you verified in hard-rule #3.
   - **Reviewers: omit.** The host's default-reviewers apply; add manually in the UI if needed. (Never add the PR author — some hosts reject a PR whose author is also a reviewer.)
   - Use the dry-run mode first if you want to show the user the resolved payload before sending.
3. **On success** the helper prints the new PR's URL → emit the success shape (step 5).
4. **On failure** (missing token, a PR already open for this source→dest, network/API error) → emit the fallback paste-ready block (step 5).
5. **Refreshing an EXISTING PR** (retitle / new description): the helper has no update subcommand. Update the git host's PR resource through its API with the new title and description, auth via a chmod-600 curl `-K` config built from the same credential files (never on argv), then GET it back to confirm.

### 5. Emit the output

**On success** (helper opened the PR) — short and glanceable, nothing else:

```
**PR opened:** <url>

**Base:** `<integration-branch>`
```

**Fallback** (helper couldn't open the PR) — the paste-ready block, exact shape:

```
**Title (paste into Title field):**

<conventional-commit-style title, plain text, under ~70 chars>

---

**Description (paste into Description field):**

<raw markdown body — headers, bullets, inline `code`, links all fine.
 NO outer ``` fence around this section. Inner fences OK for code blocks.>

---

**PR URL:** <url>

**Base:** `<integration-branch>` — verify the dropdown before clicking Create.
```

Nothing before the Title block. Nothing after the Base line.

## Description shape — default lean, add only what earns its place

Reviewers scan PRs; they don't read them. The description fits on one screen or it loses its audience. Every line earns its place or it goes.

### Default shape (fits most PRs)

One section, nothing else:

- **## Summary** — 1–3 sentences. Name the concrete thing this PR adds or changes, *and* what it does. The description must stand on its own — a reviewer opening just the description should know what landed without having to parse the title. Don't restate the title's exact words, but do include the subject: the added file/component/function, the path, the behavior, any shape-level fact worth knowing up front ("no new deps", "opt-in via flag", "breaking", etc).

Do **not** emit a `## Test plan` / `## Tests` section. This default assumes QA tests off the ticket's acceptance criteria, not the PR body, so the section would only get stripped by hand. If your team reads test plans in PRs, reintroduce it.

Add **## Why** when the motivation isn't obvious from the title or diff — a ticket link, an incident, or a constraint that explains a non-obvious choice. One or two sentences plus the link. Not a paragraph.

Link tickets as `[PROJ-123](https://tracker.example.com/browse/PROJ-123)`.

**Summary calibration** (PR titled `chore(tooling): add docs dead-link checker`):

- ✅ *Good:* "Adds `scripts/check-doc-links.js` — a standalone Node script that finds relative links in `docs/` pointing at missing files or anchors. No new deps."
- ❌ *Too lean:* "Checks doc links." — reviewer can't tell what landed.
- ❌ *Too verbose:* walking through the markdown parser, anchor slugging, and path resolution — that's diff territory (or a `## How` bullet if truly non-obvious).

### Optional sections — use sparingly

- **## How** — only when the approach is genuinely non-obvious. If the diff explains itself (most PRs), skip. When included: 2–4 one-line bullets, max.
- **## Scope** — only for *deliberate* narrowness ("band-aid; real fix tracked in PROJ-X") or to preempt a reviewer asking why something isn't included.
- **## Findings / Results** — only the aggregate (counts, headline number). Not an enumeration. "9 errors across 7 types" is the signal; the list belongs in follow-up tickets, not the PR body.

### Anti-patterns — actively cut these

- **Implementation narration.** If it's in the diff, cut it. Don't describe what the code does — the reviewer will read it.
- **Enumerations.** Don't list every error / every affected file / every config value. Aggregate + one example is enough.
- **Editorial flourishes.** Cute framing ("a statistical bet that usually loses") is zero reviewer value. Cut.
- **Restating the title.** The reader just read it.
- **Nested bullets.** Flat lists only. If a bullet needs sub-bullets, make it one line or split into two top-level bullets.
- **Multiple code blocks.** One `usage` block is the ceiling, and only if the commands aren't self-evident from the diff.

### Length guide

- Pure chore (dep bump, config tweak, typo) → ~5–8 lines
- Normal fix/feature → ~10–20 lines
- Load-bearing change with real tradeoffs → up to ~30

Past 30 lines you're probably documenting the diff. Cut.

## Credential setup (one-time)

The PR helper needs a scoped API token from the git host. If the token file (e.g. `~/.config/<pr-helper>/api-token`) is missing, the helper fails with a clear message — set it up once:

1. Mint a scoped API token in the git host's account settings, scoped to your org or repos, granting PR **write** + PR **read** + repository **read**, with an expiry.
   - **Grant PR-read even though you only create PRs** — some hosts 403 a create call without it, and the error names the missing scope.
2. Drop it in **without echoing**, in a **plain terminal** (not Claude's `!` prefix — it needs interactive paste):
   ```
   read -rs TOK < /dev/tty && printf '%s' "$TOK" > ~/.config/<pr-helper>/api-token && chmod 600 ~/.config/<pr-helper>/api-token && unset TOK
   ```
   The command **goes silent waiting for the paste — that's expected, not frozen.** Paste the token, hit Enter. (`printf '%s'`, never `echo`/`cat` — a trailing newline folds into the token and auth fails with 401.)

Any username the host's auth scheme needs lives in a sibling file in the same config dir.

## $ARGUMENTS

If extra context was passed (e.g., `/pr quick band-aid for PROJ-324, mention the follow-up ticket`), fold it into the right section and honor directives like "skip X" or "mention Y".

$ARGUMENTS
