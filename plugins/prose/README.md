# prose

How Claude talks to you and how it writes for other people. Two skills, one command, one hook:

- `prose:reply-style` — the shape of a chat reply: an opening line, a three-line progress note per phase, a final reply that leads with the outcome and ends with what you owe, and a list of things that never get shortened.
- `prose:technical-writing` — a rule set for text people read: docs, READMEs, Javadoc and docstrings, inline comments, commit bodies, MR descriptions, error messages, release notes, and comments posted to chat or a tracker.
- `/prose:bro` — restate the last message in plain language.
- A `UserPromptSubmit` hook that reminds Claude on every prompt that replies follow `reply-style`, so the style survives long sessions and context compaction.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install prose@fprochazka-claude-code-plugins --scope user
```

The hook needs `bash`; it uses `jq` when present and falls back to plain output without it.

## Highlights

- **Lead with the result** — the first sentence states what happened or what the answer is. Narration of the work, restated plans, and closing recaps are cut. Short by choosing what to include, not by compressing sentences; when short and clear conflict, clear wins
- **Two final-reply shapes** — done: outcome with the proving fact, findings, what was left out, written as a re-grounding for a reader who saw none of the work. Need input: what is blocked, then numbered questions that each end in a choice with a recommendation first, at the end of a turn that delivers the progress so far
- **Subagent output is never parroted** — the reply carries the file path and a gist of at most three lines
- **Never shorten** — error output, failing tests, security warnings, destructive-action confirmations, and the cost and limits of a proposal keep their full content
- **Why, not what** — docs and comments say what the code cannot: decisions, gotchas, business meaning, non-obvious relationships, legacy reasons. Listings, column descriptions, and change narration are out
- **Simplified Technical English underneath** — short active sentences, plain verbs, one name per thing, derived from ASD-STE100 and relaxed for conversation

Full rules in [`skills/reply-style/SKILL.md`](skills/reply-style/) and [`skills/technical-writing/SKILL.md`](skills/technical-writing/).

## Commands

- `/prose:bro [focus]` — says the last message again in plain language, keeping the conclusion and the concrete anchors (numbers, paths, commands). No tools, no new work.

## How the reminder works

Claude Code's built-in output styles re-inject a one-line reminder on every prompt because a style stated once in the system prompt stops being followed after a few turns. This plugin does the same with a hook instead of an output style: `hooks/reply-style-reminder.sh` prints one static line that states the behavior and names the skill. On the first prompt that makes Claude load the skill; on every later prompt it keeps the loaded rules in force, and after context compaction it makes Claude load them again. The line is static on purpose — hook output is replayed when a session is resumed.

The plugin assumes the output-style feature is unused (`outputStyle` left at `default`). Running the built-in `Concise` style alongside adds a second reminder whose body claims precedence over other instructions.

[`skill-keyword-reminder`](../skill-keyword-reminder/) is a dependency and installs with the plugin: it suggests `technical-writing` whenever a prompt mentions docs, comments, commits, MR descriptions, or error messages.

## What it isn't

Not a voice. The rules strip filler and structure the reply; they do not imitate a person. Not a linter — the self-lint sections are checklists for the model, not scripts.

## License

MIT
