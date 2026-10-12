---
name: envset
description: "Get a third-party API token/key from the user into a project env file SECURELY, and verified, when a task is blocked on a credential only the user can mint. Emits the whole recipe: a per-key mint checklist (exact URL, the NARROWEST scope that works, a name), one paste-once `envset()` shell function (hidden input, gitignore-gated, replace-or-append), one `envset KEY` line per key; then Claude verifies each credential vendor-side, reading from the FILE, never echoing it. Fire when a grep for the NAME shows the key is missing (\"I need a Resend key\", \"store this token\", \"add X to .env\", re-storing after a rotation). NOT for secrets Claude can fetch itself (`vercel env pull`), NOT for using a secret that already exists, NOT for configuring third-party dashboards. Never fires proactively."
disable-model-invocation: false
argument-hint: "[KEY_NAME ...] [--file path]"
---

The user has to do exactly one thing a machine can't: mint the credential and paste it in. Everything around that — knowing what to mint, where it lands, whether it's really in, whether it's scoped right — is yours. Make their part small, phone-sized, and impossible to get subtly wrong.

Why a dedicated skill: every naive path leaks or rots. `echo KEY=val >> .env` lands the secret in shell history. A prompt inside a pasted multi-line block eats the lines pasted after it as its stdin. `.env` files routinely lack a trailing newline, so a blind append splices onto the last line and corrupts it. GNU `sed -i` on a symlinked `.env` — common in worktree setups — silently replaces the link with a detached copy. And a one-off script per session leaves trash behind. The paste-once function in § 3 closes each of those and was tested against each.

## 1. Establish what's missing — names only

```bash
grep -oE '^[A-Z_0-9]+=' .env | tr -d '='
```

Do the same for the project's other env files (`frontend/.env.local`, a systemd `EnvironmentFile`, whatever its CLAUDE.md names) and compare against what the task needs. Never `cat` the file — you want the key inventory, not the values. If the task can run on a credential that already exists, or one you can pull yourself (`vercel env pull`, `railway run`), stop here: this skill is for keys only the user can mint.

Decide the **target file** and say which: the project's canonical env file by default (`.env` at repo root for most projects); a sub-app's own file when only that app consumes it; a `0600` out-of-repo file for a systemd unit. The function takes it as an optional second argument.

## 2. Mint checklist — one per key

For each key, tell the user:

- **Where** — the exact dashboard URL.
- **Scope** — the *narrowest* that does the job, named concretely: "Zone · DNS · Edit, Zone Resources → Specific zone → `example.com`", not "a DNS token". This is where the security judgment actually lives; a vague scope line is how a token ends up account-wide. When a broader scope is genuinely required, say so and why (Resend: creating a domain needs Full access, Sending won't).
- **Name** — project + purpose (`myproject-dns`), so it's recognizable in next year's token audit.
- **"Shown once — copy it now"** where that's true (most vendors).

Read `references/vendors.md` (next to this file) for the vendors already vetted — URLs, scope guidance, the token length to expect, the verify probe, and the gotcha each has already cost. If a vendor isn't there, look it up at mint time and add a row.

## 3. The paste — two blocks, never one

**Block A — define. Paste once per terminal session.** Every line is ≤ 36 chars so it survives a phone-width wrap (a mid-command wrap becomes a real newline on copy, which breaks a function body just as surely as a command). Emit it verbatim:

```bash
envset() {
  local k=${1:?key} f=${2:-.env} v
  git check-ignore -q "$f" 2>&-
  case $? in 1)
    echo "✗ $f not gitignored"
    return 1;; esac
  printf '%s: ' "$k"
  read -rs v; echo
  if [ -z "$v" ]; then
    echo "✗ empty"; return 1; fi
  f=$(readlink -f "$f")
  touch "$f"
  if [ -s "$f" ] &&
     [ -n "$(tail -c1 "$f")" ]
  then printf '\n' >>"$f"; fi
  sed -i "/^$k=/d" "$f"
  printf '%s=%s\n' "$k" "$v" >>"$f"
  chmod 600 "$f"
  echo "✓ $k → $f (${#v} chars)"
}
```

What each guard is for, so you can adapt it rather than cargo-cult it: `check-ignore` exit **1** means the path is not ignored → refuse (exit **128** means outside any repo → nothing to leak into, proceed). `read -rs` takes the value hidden and keeps it out of history. `readlink -f` *after* the ignore check and *before* the write keeps a worktree's symlinked `.env` a symlink. The `tail -c1` check repairs a missing trailing newline. `sed` then `printf` is replace-or-append, so a rotation is the same command as a first store. `${#v}` is the truncation tripwire — the report line carries a length, never a value.

> ⚠️ **Never emit a bare `$1` in this file.** Skill bodies are rendered with the
> invocation's positional arguments substituted into bare `$N`, so `local k=$1`
> reaches the model as `local k=<some word from the args>` and the function then
> writes a variable named after it — an invocation whose args contained the word
> "into" would render `local k=into` and write `into=<the secret>` into `.env`.
> Braced forms survive — which is why `${2:-.env}` is unaffected and `${1:?key}`
> is used above. It also fails loudly on a missing argument instead of silently
> writing a junk key.

**Block B — invoke. One short line per key, as a separate paste (or typed).** Never in the same block as A: without bracketed-paste, the `read` would consume the next pasted line as the value.

```bash
envset RESEND_API_KEY
envset CLOUDFLARE_API_TOKEN
```

Non-default file: `envset RAILWAY_TOKEN ~/.config/x/iac.env`.

Tell the user what to paste back: just the `✓` / `✗` lines. They carry lengths and paths, never values.

## 4. Verify — yours, from the file

When the user reports in, check each key against its vendor, **reading from the file** — not from anything in the conversation:

```bash
V=$(grep -E '^KEY=' .env | cut -d= -f2-)
curl -s -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $V" <probe-url>
```

Compare the reported length against the vendor's expected shape *first* — a 19-char Cloudflare token is a truncated paste, not a bad token. Then probe. Where the vendor exposes scope (Cloudflare zone listing, GitHub `X-OAuth-Scopes`), confirm it reaches what the task needs: a 200 proves the key is live, not that it can do the job. A read probe also says nothing about writes — if the task writes, do a no-op write probe before building on it (Supabase scoped tokens: read 200, `PATCH` 403). Report status codes and what they mean; never the value.

## Guardrails

- **The value never touches the transcript.** Not your output, not a tool param, not a log line, not a `curl -v`. The only secret-bearing event is the user's hidden `read`. If a value does land in chat, it's compromised: say so, and the re-store after rotation is the same `envset KEY`.
- **No generated scripts.** The function is the whole tool and dies with the shell. If the one-paste-per-session tax ever genuinely bites, the body is lift-and-shift into your shell dotfiles — a deliberate promotion, not a default.
- **Width is load-bearing.** Every emitted line ≤ 36 chars. If you change the function, re-measure (`awk 'length > 36'`).
- **Linux assumed.** GNU `sed -i` and `readlink -f`; macOS would need `sed -i ''` and `greadlink` — adapt the function before using it there.
- Run only when a task is actually blocked on a missing credential, never proactively "while we're here".
