---
name: peek
description: >-
  Read another live Claude session's recent turns WITHOUT interrupting it: find
  it by name or window, then summarize what it is doing, its branch and cwd, and
  its latest prompts and replies. Sends nothing. Fire on "/peek", "what is X
  doing", "did X touch Y", "where is X at", or before messaging a busy peer.
  NOT /relay (sends a message to X). Personal-tooling example (genericized)
disable-model-invocation: true
argument-hint: "[who] — session name, window or session-id prefix; optional"
---

> **Read-only example.** When several sessions run in parallel, one can read another's transcript tail without interrupting it, so "what is X doing?" costs the peer nothing. Don't install it — adapt the pattern.

Look at another session without touching it. The peer never sees a peek, so it's always
safe, even while the peer is busy. If the user wants to ask or tell the peer something, that's
a message (see the `/relay` example): it lands in the peer's queue and interrupts it at its next
tool round.

## 1. Find the session

Resolve who from the arguments, else the words around the invocation, else the
conversation (the session you were just discussing). The CLI's agent-listing tool shows the
live sessions on this machine, each with its name, state and terminal window.

- Match against the **name** first, then the **window or workspace** it runs in. A row's short
  display ref is not necessarily a session-id prefix, so peek by name.
- One clear match: peek it. Several: list them (name, window, started) with your pick and
  why, then ask. None: say so.
- Asked by **ticket or PR** ("who's on PROJ-123?"), no name may match: work spun off inside
  another ticket's session keeps that session's name. Grep the session transcripts
  (`~/.claude/projects/*/*.jsonl`) for the key, then peek each hit by session-id prefix
  (excluding your own).
- The peek helper resolves names and titles itself, so a session missing from the live list
  (for example, one that just ended) can still be peeked by name.

## 2. Peek

A small local helper script (not shipped here) takes a name, window or session-id prefix and a
turn count, finds that session's transcript file, and prints a header (name, session id, cwd,
branch, last write, window) plus the last N prompts and replies, with tool calls skipped. Start
around 6 turns; raise it when the question reaches further back ("did X ever touch the
migration?").

The transcript lags the screen: Claude Code writes a tool call only once it has a result, so
an open question form or a running tool isn't in it yet. When "is it waiting on the user?"
matters, capture the peer's terminal pane too and read its last ~30 lines.

## 3. Report

Answer the question the user asked in a line or two: what the peer is on, where it stopped, and
whether it's waiting on the user. Summarize, don't dump. Anything the peer *claims* (a deploy
state, line numbers, "already merged") is its claim, not a verified fact, so say so if the user
might act on it. If the answer needs the peer to reply, suggest a relay message instead.
