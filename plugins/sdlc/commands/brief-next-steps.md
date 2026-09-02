---
description: Write a short briefing of the proposed next steps into ./.claude/plans/ so the conclusion can be read instead of the argument
argument-hint: [optional scope hint or slug]
allowed-tools: Read, Glob, Bash, Write
---

# Brief Next Steps

Compress what this session landed on into one short file the user can read in ten minutes and act on. The output is the **final proposal in implementation order** — the conclusion, not the argument.

## Scope

$ARGUMENTS

If empty, brief the whole session. If the session covered several unrelated threads, brief the one being worked on and note the omission in one line.

## Sources

**You (the orchestrator) write the file yourself — never a subagent**, because the primary source is the conversation you are holding. Priority order: (1) the session itself — this is often the *only* source, and that is the normal case; (2) `./.claude/plans/*.md` if any exist — newest proposal primary, older files for specific facts only; (3) docs/tickets already read this session — anchor, do not re-read. **Never go exploring for new material** — a missing fact goes in the "not yet verified" section, not into a research round.

## Style

Invoke the `prose:technical-writing` skill before you write. The file follows its form rules (short active sentences, plain verbs, no LLM vocabulary, no narration of change). The rules below are the briefing-specific ones on top of it.

## Output path

Worktree-local `./.claude/plans/<slug>-briefing.md` (`mkdir -p`; never `/tmp`, scratchpad, or `docs/`). Slug: `$ARGUMENTS`, else ticket ID (lowercase), else kebab-case topic. **If the file exists, overwrite it wholesale** — a briefing is a snapshot of current state; do not patch, do not suffix `-2`.

## The briefing

As short as the material allows, hard ceiling ~170 lines, **no floor** — padding is a failure. Structure:

- **Two or three sentences of context** at the top. No further preamble.
- If two terms were actually being confused, one short section separating them.
- **Steps in implementation order.** Each heading names the **problem in plain language, not the mechanism** ("The quantities we ordered are never refreshed on the mirror", not "Add a refresh job"). Within each: what is wrong → what we change and which parts we touch → what that gets us → what it unlocks next. Each step ships on its own; if two are independent, say so in one line instead of inventing a dependency.
- **Closing section: decisions the user still owes** — one line each, ending in an actual choice, pointing at its step. **Mandatory — this is the point of the file**; dropping the unblocking decisions is the failure mode in the other direction.
- **Second closing section: not yet verified** — one line each, no elaboration.

Write it to the user in the second person.

## Reply in chat

Only: file path, line count, and the step headings as a bare list. Nothing else.

## Hard rules

- **Only the final proposal.** No alternatives, comparisons, `Decided`/`Open` taxonomies, rule numbers, or revision history.
- **No narration.** Only the current state — never what changed or what an earlier version said.
- **Layman's terms.** Define internal vocabulary on first use, one clause, inline — no glossary section.
- Numbers only where they justify the work; `file:line` refs sparse and inline.
- Hedging lives in the closing sections only.
- Do not delete or rewrite the long source docs — the briefing points at them.
- Do not touch code or git, do not enter plan mode, do not implement, do not ask before writing — write the file.
