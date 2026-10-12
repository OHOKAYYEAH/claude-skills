---
name: poll
description: >-
  Wait for someone else's reply (an email, a PR review, a Slack thread) and
  wake the session only when it lands. A script does the checking, so waiting
  costs no tokens. Fire on "/poll", "watch for X's reply", "let me know when X
  answers"; never on your own initiative. NOT /loop (repeat a task), /schedule
  (cloud job), or /wait (only tags the session as waiting). Personal-tooling
  example (genericized)
disable-model-invocation: true
argument-hint: "[minutes] [whose reply / which thread] [then …] — optional"
---

> **Read-only example.** Put the repeated checking in a zero-token script run as a background command, so the model only decides *what* to watch and handles the result. Don't install it — adapt the pattern.

Watch one thread for a reply from someone other than you, and spend as close to zero tokens as possible while waiting. The costly part is deciding *what* to watch, which you do once. The repeated checking is done by a small stdlib Python script in this skill's folder (not shipped here): it takes a source and its IDs, loops at the interval, and exits with one JSON status line only on a result. A background Bash command re-invokes the session when it exits, so the session sleeps until something happens.

## 1. Parse the call

- **Interval:** a leading bare number is minutes (`/poll 15`). Default 5. Under 5 minutes is fine on the script path (a check is a ~2s API call), but on the cron fallback every check is a full turn, so say what it costs and use 10.
- **Target:** whatever words follow ("the designer's reply", "PR #42", "the Slack thread with the ops lead"). If there are none, use the email or Slack message you most recently sent or drafted in this session. If the session has no clear candidate, ask, because watching the wrong thread fails silently.
- **Then clause:** anything after "then" is the action to take on a hit ("then draft a response"). Keep it for step 4.
- **Cap:** 8 hours unless the call says otherwise. A forgotten watch should end on its own.

## 2. Resolve the target to something exact

Pin the thread and the moment, so replies from before the watch, and your own messages, never count:

- **Email (e.g. Outlook or Gmail):** find the thread with the mail MCP (a message search, or a message already in context) and take its conversation ID. `--since` is the send time of your latest message in the thread, in UTC. `--me` is your mailbox address, taken from your own messages in that thread. The script reads mail through a local mail API client that holds its own login.
- **Code-host PR (e.g. GitHub, GitLab or Bitbucket):** owner/workspace, repo slug, and PR number (read the repo's `git remote get-url origin` if needed). `--since` is now, or when you last pushed or pinged. The script authenticates with a code-host API token kept in a local file.
- **Chat (e.g. Slack), or any other source with an MCP but no script path:** the channel ID + thread `ts` (or the DM channel), plus the `ts` of your last message. Go to step 3b.

Then run a single check with `--once` before arming the watch. It proves the query works (a bad ID or an expired login shows up now, not as eight hours of silence), and it catches a reply that already arrived. `reply` → go straight to step 4. `error` → report it and stop; a mail-client auth error means the user needs to re-run that client's login.

## 3a. Arm the script (email, PR)

Run with Bash `run_in_background: true`. It prints one JSON line and exits:

```
python3 <skill dir>/scripts/poll.py mail \
  --conversation-id '<id>' --since <iso> --me <address> \
  --interval <seconds> --max-hours <h>

python3 <skill dir>/scripts/poll.py pr \
  --owner <owner> --repo <slug> --pr <n> --since <iso> \
  --interval <seconds> --max-hours <h>
```

Tell the user in one line what is being watched, how often, and until when. Then end the turn. Every status wakes you, including `error` and `expired`, because a watch that dies quietly looks exactly like one still waiting.

## 3b. Arm the cron fallback (chat and the rest)

A chat plugin's login (Slack here) lives inside Claude Code, where no script can reach it, so each check here is a real turn. Use `CronCreate` with a recurring schedule on an off-minute (`3-59/10 * * * *`, not `*/10`). Write a prompt that stands alone: the exact read call and IDs, "a message after `<ts>` not from me counts", the deadline, and "on a hit or past the deadline, `CronDelete` this job and report; otherwise reply with a single line `no reply yet`". A quiet tick should cost almost nothing. Remember the job ID. Cron jobs die with the session and expire on their own after 7 days.

## 4. On a result

- **reply:** send `PushNotification` ("The designer replied on the onboarding-flow thread: approves the mockup, asks about dates"). Then give a two-line summary in chat: who, what they said, and anything they asked you. If the call had a then clause, do it now. The watch has already stopped, so don't re-arm.
- **expired:** one line saying no reply by the deadline, plus an offer to re-arm.
- **error:** the detail line and the likely fix (re-login, wrong ID, token scope).

The watch only lives as long as this session. If the user is about to close it, say the watch ends too.
