---
name: interview
description: Interrogate the user's intent before executing an ambiguous or under-specified task — ask the sharp clarifying questions, then restate your understanding and lock it before proceeding. Fire when the user explicitly asks to be interviewed / "ask me questions first" / "make sure you understand before you build", or when an orchestrator chains this to capture intent (e.g. /create-skill). This is the deliberate, thorough counterpart to the single-sharp-question default (e.g. /work step 1) — when invoked, multiple questions are wanted. Do NOT fire proactively on every fuzzy task. NOT /recommend (that commits to a pick, or to what's next); NOT /spec (freezes settled intent onto the ticket — chain it after this when a build follows).
disable-model-invocation: false
argument-hint: "[optional: the task/context to interrogate, or a focus]"
---

You've invoked the interview. You've loaded context you sense is **not fully clear**, and you want it interrogated *before* execution — not guessed at, not charged ahead on a plausible reading. The whole value is catching a misunderstanding now, while it's a question, instead of after it's shipped code.

This is the deliberate opposite of the "ask ONE sharp question and move on" default. Here, asking several real questions is the point. But thoroughness is not the same as volume — see signal discipline below.

## The move

### 1. Scope what you're interrogating
The task/context is whatever's in the conversation, narrowed by any focus in `$ARGUMENTS`. If genuinely nothing is on the table to interrogate, say so and ask the user what they want scoped — don't invent a task to interview about.

### 2. Answer your own questions first
Before you ask the user anything, resolve what you *can* resolve yourself — read the code, check the conventions, look at sibling files, consult memory. Come prepared. A question you could have answered by reading a file is not a question for the user; asking it wastes their attention and reads as lazy. The questions that survive this filter are the ones that genuinely change what you'd do and that only the user can answer (intent, priorities, taste, business constraints, which-of-these-readings-did-you-mean).

### 3. Ask the surviving questions — structured, with your own take
Batch the open questions and ask them via the **AskUserQuestion** tool in a single pass:
- Multiple-choice where the decision space is discrete; free-form ("Other" is always available) where it's open.
- **Every question carries your recommendation as the first option, marked "(Recommended)", with the *why*.** The user's standing preference: "here are options, I'd pick X because Y" beats "here are options, you decide." Commit to a call in each one; they'll push back if they disagree.
- Cap at the tool's 4-questions-per-call. If more than four are genuinely open, ask the highest-leverage four first; a second round is cheaper than a wall of questions.
- Phrase each question so a busy user can answer it in one glance — concrete, specific, no preamble.

### 4. Lock intent — restate, then confirm
Once the answers are in, **synthesize them back** into a short, plain restatement of what you now understand:
- What the user wants, the scope, the key constraints, and **what you're about to do** as a result.
- Surface any assumption you're still carrying that they didn't explicitly confirm ("I'm assuming X — say the word if not").
- Then explicitly hand them the gate: confirm and I proceed, or correct me. This is the intent-lock — the forcing function that makes the interview worth more than just charging ahead.

Keep the restatement tight. It's a confirmation, not a document.

### 5. Proceed (or hand back)
On confirmation, execute — don't re-ask. If you were **chained by an orchestrator** (e.g. `/create-skill`), the confirmed intent is what you hand back so the caller continues; don't treat the interview as a place to start building yourself unless that's your job.

## Why the confirm-gate is a legitimate pause (not a chaining bug)
Interviewing inherently needs human input — the AskUserQuestion call and the final confirm both wait on the user. That's correct behavior, not the halt-bug that fork-wrappers exist to fix (an inner skill ending the turn with a terminal report). The AskUserQuestion result returns and execution continues; the final confirm is a real user-decision gate, the same kind `/work` allows. So this skill is **not** a `context: fork` skill — a fork can't talk to the user, which is the entire job. When chained, the orchestrator simply resumes after the user confirms.

## Guardrails
- **Signal discipline — don't manufacture questions to look thorough.** Same ethos as a good code review: real findings only, no manufactured nits. A short interview on a nearly-clear task is the right outcome; padding it with questions you could answer yourself is the failure mode. If two or three questions cover it, ask two or three.
- **Recommend, don't just enumerate.** A question with no recommendation pushes the cognitive load back onto the user — the thing this is supposed to relieve.
- **One pass of real questions, then lock.** Don't drip-feed an endless interrogation. Front-load the questions that matter, restate, confirm, go.
- **No charging ahead.** The point is to *not* execute before intent is locked. If you find yourself reaching for Edit/Write before the confirm gate, stop — that's the behavior this skill exists to prevent.
- Only on an explicit ask or an orchestrator's chain. For an ordinarily fuzzy task, ask one sharp question instead.
