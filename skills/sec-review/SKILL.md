---
name: sec-review
description: Diff-scoped security audit that runs in an isolated fork and returns its findings as a result, so a chaining caller (/super-review) keeps control. Proves a non-empty diff first, then audits every changed file (committed, uncommitted, untracked) for vulnerabilities the change introduces. Standalone it is chain-safe too. NOT /code-review (correctness) or /blast-radius (downstream consumers).
disable-model-invocation: false
context: fork
agent: general-purpose
argument-hint: "[optional repo path and/or focus, e.g. \"services/api the new auth endpoint\"]"
---

Audit the current change for security vulnerabilities **in this isolated fork**, then return the findings to the caller.

This skill does not call the native `/security-review`. That pass computes its diff once, from the session's cwd against `origin/HEAD`, committed changes only — so when cwd is a parent directory rather than the repo holding the change, on uncommitted work, or when the branch was cut from something other than the default branch, it reviews the wrong diff or none. The audit below is the review.

## What to do

### 0. Establish the diff — and PROVE it is non-empty (do this first, always)

**Find the repo.** The fork's cwd may be a parent directory that holds none of the change. Resolve the target repo from `$ARGUMENTS` or the caller's named worktree/path, falling back to cwd; then run every git command as `git -C <repo>`.

```
git -C <repo> rev-parse --show-toplevel          # the repo root, not a parent dir
git -C <repo> rev-parse --abbrev-ref HEAD
git -C <repo> diff --stat <base>...HEAD ; git -C <repo> diff --stat   # committed + uncommitted
git -C <repo> status --porcelain                 # UNTRACKED too — git diff never shows new files
```

`<base>` is the branch this work was cut from (the project's integration branch), **not** `origin/HEAD` — that is only the remote's default branch, which may not be where this work started, and diffing against it drags in commits this change never touched.

**The untracked line is not optional.** Neither `git diff` form sees a file that has never been added, so an all-new-files change reads as an empty diff. Count a file as part of the diff if it appears in *any* of the three commands.

Record **the file list and total changed lines**. Two hard rules:

- **If the diff is empty, STOP and return `🛑 could not establish a diff`** — naming the cwd, the resolved toplevel, and the base you compared against. Do NOT return "clean". An empty diff is a tooling failure, not a security result.
- **If `$ARGUMENTS` named a scope**, confirm the diff actually contains it. A scope hint that matches nothing is the same failure in a quieter costume.

### 1. Audit the diff

Review exactly the step-0 file list: the diff hunks for tracked files, and every untracked file read in full. Read surrounding code where it decides the answer — e.g. how sibling resolvers/routes gate the same data. If `$ARGUMENTS` names a focus, go deepest there, but still cover every file.

Audit as a senior security engineer. Check at least:

- **Authorization** — every new or changed resolver, route, job, or query gated like its siblings; object-level checks (can this caller see *this* row?), not just "is logged in".
- **Authentication and tokens** — signature, `aud`, `iss`, and expiry actually validated; sessions and cookies scoped correctly.
- **Injection and construction** — SQL, shell, template, path traversal, SSRF, unsafe deserialization.
- **Input handling** — regexes that backtrack on crafted input (ReDoS), unbounded sizes or loops on caller-controlled data.
- **Secrets and data exposure** — secrets or crypto misuse in code/config; personal data in logs, error messages, API responses, or test fixtures.
- **Dependencies** — new or bumped packages in the auth/parse/network path.

Test files and regex DoS are in scope — don't skip them as "low signal". Flag only what **this diff introduces or newly exposes**; a pre-existing issue is worth a line only when the change makes it reachable.

### 2. Return the findings

Return the complete findings verbatim — each with `file:line`, severity, and a concrete attack path (who can do what, how). Then:

- **Coverage:** `reviewed N/N step-0 files` — name any file you did not review and why. A partial review is never "clean".
- **Verdict:** clean / N findings. If there are no findings, say so plainly.

Do not abridge or summarize away detail; the caller needs the actual findings to triage.

## Guardrails

- **A non-empty diff is a precondition, not a nicety.** Never return a clean verdict you cannot tie to specific changed lines.
- **Read-only.** Surface findings; do not edit code. Fixing is the caller's decision.
- **Don't touch data files.** Never open or quote the contents of customer-data files (`*.csv`, `*.xlsx`, dumps, `*.sql` data scripts, exported reports) — review code and config, not data.
