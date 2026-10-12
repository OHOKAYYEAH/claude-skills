# Shape: meeting

A multi-speaker meeting as a record someone who missed it can act on: what was decided, who owes what, and what the discussion established. It suits standups, syncs, show-and-tells, planning calls, and interviews with several voices. It's the default for a speaker-labelled transcript with three or more voices when the call names no shape (`meeting_shape` in config changes that).

- `## TL;DR`: 3–5 sentences: what the meeting was, its main topic, and what came out of it.
- `## Decisions`: what the room settled, each with who decided or proposed it and its anchor. Count only real settlements ("we'll keep project skills in the project repo"), not opinions voiced. Write "None" if nothing was settled, because that's worth knowing.
- `## Action items`: `**Owner** — the action (anchor)`, one per line. Include only what someone took on or was asked to do; an idea nobody picked up goes under Discussion. Write `(unowned)` when the room agreed something should happen and nobody took it.
- `## Discussion`: grouped under 2–6 **bold topic headings** you name from the content. Each bullet is a claim or position, attributed to its speaker when the labels make that clear ("Sam: require *a* process, not this one"), ending with its anchor. Keep disagreement visible: who argued what against whom is the part a summary most often flattens.
- `## Open questions`: raised and not resolved, each anchored, with who raised it. Skip the section when there are none.
- `## Reader's note` (optional; see SKILL.md). For meetings it usually carries the speaker-label caveats: a room microphone or dial-in line that merges several people under one name, and names the captions mangled.
