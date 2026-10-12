---
name: present
description: >-
  Put a finished thing in front of the user as ONE styled HTML page:
  screenshots become a captioned sheet, a markdown doc becomes a read-only
  rendered copy. Builds with the bundled `present` engine and delivers to fit
  the machine (browser tab, or sent as a file when headless, or an Artifact
  URL), plus a PDF of the same page when it's going to someone who won't open
  HTML. The one way pictures or documents reach the user; never loose image
  files. Fire when a skill has images or a deliverable doc to show, or on
  "show me that file", "open the report", "send me the screenshots", "make a
  PDF of that to send". NOT
  /before-after (gathers before/after evidence of a change, then chains this),
  NOT /mockup (renders an unbuilt UI).
disable-model-invocation: false
argument-hint: "<.md path | screenshots to sheet> [publish] [open | noopen] [pdf]"
---

# Present — one page in front of the user

A single styled page reads far more easily than a stack of image cards or raw markdown, and someone running several sessions at once needs every picture and document to arrive the same way: **one HTML page, one design, delivered once.** Other skills chain this rather than sending files themselves.

## Build it — never hand-write the HTML

The engine is `bin/present` inside this skill's folder (the base directory shown when the skill loads). Its header documents the full manifest schema; read it when building a sheet. Writing the HTML yourself would push base64 through a tool call and drift from the one design. It needs `python3`; doc mode also needs the `markdown` and `pygments` packages.

- **A markdown document** → `present doc <abs path.md>`. It renders a read-only copy under `~/.cache/present/`, embeds local images, and renders linked `.md` files so a doc set stays navigable. Pass one index doc to deliver a whole set.
- **Pictures** → write a small JSON manifest beside the frames, then `present sheet <manifest.json>`. One section per surface or state, frames in capture order, each labelled (`desktop` / `phone`, or `before` / `after` for a pair), and a caption stating the decisions a reader should check. Even a single image goes in a sheet. Real captures only: the engine refuses a missing file, and you never describe a frame you didn't take.

Both print the path of the page. Keep frames where their caller keeps evidence, and throwaway renders in the scratchpad.

## Deliver it — to fit the machine

Default, decided by the environment:

- **A desktop session** (`$DISPLAY` or `$WAYLAND_DISPLAY` is set, or macOS) → add `--open`. It opens with `$PRESENT_OPENER` if set, else `xdg-open` / `open`. Point `PRESENT_OPENER` at a script if pages should land in a particular browser profile. Open pages only through `--open` (for a page already built, rerun with `--open` or call `$PRESENT_OPENER` on it), never a bare `xdg-open`, which skips that routing.
- **Headless** (SSH box, remote session) → send the page to the user as a file if the session has a send-file tool; otherwise hand back the absolute path. Do this every time a page is put in front of the user, an approval preview included. A browser here would show nobody anything.

Caller tokens adjust that:

- **`publish`** → an Artifact URL instead of a file. Build a sheet with `--linked -o <dir>/index.html` and publish `shots/` as its supporting files, so the page stays small. A doc publishes as-is. Then emit `● Published: <url>`. Artifacts are account-bound: one published from one account 404s in a browser signed in to another, which looks like a dead link.
- **`open`** → with `publish`, also open the Artifact now. Without it, stay link-only.
- **`noopen`** → build and return the absolute path, deliver nothing.
- **`pdf`** → also print the page to a `.pdf` beside it (`--pdf` on either mode), for emailing or Slacking to someone who won't open an HTML file. It combines with the others: the page still delivers as usual unless `noopen`. A doc's PDF lands in `~/.cache/present/`, so copy it next to the caller's evidence and give that path. **A PDF usually leaves the team, so check the audience before you print:** a sheet written for the user (provenance, working notes, session shorthand) needs captions rewritten for its reader, not just a format change. Sometimes the right file isn't this page at all, e.g. the real report pages rather than a sheet about them. It needs Chromium's headless shell or Chrome/Chromium on `PATH`.

When the user says they're following from another device, send the page as a file as well, whatever else the delivery was.

## The one judgment: a tab is not free

Present what the user asked for or needs to judge: the report they requested, the audit, a preview awaiting approval, evidence at the end of a ship. **Don't open a byproduct** such as notes a skill wrote for its own next step, intermediate findings, or a doc regenerated mid-pipeline while they're away. For those, give the absolute path (`noopen`) and let them ask. When it's ambiguous, give the path: they can ask for the page, but they can't un-open one. A forked skill never presents; it returns the path, and its caller decides.

## Report back one line

```
● Presented: /abs/path/page.html (opened | sent as a file | path only)
```

With `pdf`, add the PDF on a second line: `  PDF: /abs/path/page.pdf (N pages)`.

Never summarize the content you just presented. If there's a verdict the user needs, it goes in the terminal response too; the page holds the detail, not the answer.

## Guardrails

- **Never loose images.** Individual image files only when the user asks for them by name.
- **Never present a file you haven't written or read this session.** A stale report from three sessions ago under "here's your report" is worse than nothing.
- **Absolute paths, always.** A path gets pasted into a fresh terminal or file manager, where a relative one is dead on arrival.
- **One design, every project.** The engine has no per-repo theming, on purpose. Don't add a project's colors to a page.
