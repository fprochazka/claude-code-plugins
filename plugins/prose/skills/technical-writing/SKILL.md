---
name: technical-writing
description: Rule set for text people read — docs, READMEs, doc comments (Javadoc, docstrings), inline comments, commit bodies, MR/PR descriptions, error messages, release notes, and comments posted to chat or a tracker. Use when writing or rewriting any of these, when asked to make text clear, plain, human, or not sound like AI, or when documenting a decision. Never for code, identifiers, or chat replies to the user (reply-style).
trigger-keywords: docs, documentation, README, javadoc, docstring, doc comment, code comment, MR description, PR description, commit message, release notes, changelog, error message, Slack message, ticket comment, plain english, STE, slop, unslop
---

# technical-writing

The reader can read the code. Text earns its place by saying what the code cannot: why it is this way, what will surprise the reader, what it connects to. Everything else is a restatement that goes stale the day the code changes.

## What to write down

- **Why, not what.** Decisions, trade-offs, constraints: "orders are versioned by validity period because the legal export must reproduce any past state". Not "the entity has validFrom and validTo".
- **Gotchas.** Surprising behavior, implicit contracts, the thing that is easy to get wrong: "this repository queries the legacy schema directly; there is no entity to look for".
- **Business meaning.** What a value means to the domain and why anyone cares: "a sell-off promotion means purchasing over-ordered; it should feed the next forecast".
- **Non-obvious relationships.** How parts feed each other, especially when the data flow is not visible from one file: "requirements are computed from forecast plus reservations, never stored".
- **Legacy reasons.** Why something looks odd today: "the `sites` table holds warehouses; the name predates the warehouse model". This is the one kind of history worth keeping.

## What not to write down

- Lists of classes, methods, files, or endpoints. They go stale at once and the reader can search.
- Column descriptions, config values, environment settings. They live in the schema, the annotations, and the config files.
- The pattern, at the place where it is used. A project convention is documented once, in the central place for conventions; a use of it gets at most a pointer ("follows the repository convention, see docs/conventions"). A deviation from the pattern is documented where it happens, with its reason.
- Anything the code says in thirty seconds of reading.
- The change. "Previously X, now Y", "renamed from", "no longer", "this commit adds" belong to git, not to docs or comments. Describe the current state only.
- Ticket references in code comments, schema comments, migrations, or descriptions. They belong in the commit and the MR.

## Form — every artifact

- Short sentences, one idea each. Active voice with a named actor: "the parser reads the file", not "the file is read".
- A verb for an action: "analyze the log", not "perform an analysis of the log". No "-ing" main verb where a simple tense works. No phrasal verb where a plain one exists ("start", not "spin up").
- The short common word: use, start, help, make sure, before, after, about, get, show, also. Not utilize, initiate, facilitate, ensure, prior to, subsequent to, regarding, obtain, demonstrate, furthermore.
- One name for one thing, the whole document through.
- Second person for the reader ("you"), present tense, imperative for steps, the condition before the instruction ("if the cache is warm, skip this step").
- One topic per paragraph, at most six sentences. Steps as a numbered list, one action per item.
- Lists instead of two-column tables; a table only at three or more columns.
- No marketing adjectives (robust, seamless, comprehensive, powerful, cutting-edge). No LLM vocabulary (leverage, delve, holistic, pivotal, streamline, empower, "it is important to note"). No rule-of-three padding, no em-dash pile-ups, no "this file contains". American spelling.
- Write only the requested text. No preamble, no summary of what you wrote, no closing remarks.

The form rules derive from ASD-STE100 Simplified Technical English (https://asd-ste100.org). For procedures, runbooks, and error messages apply them strictly: one instruction per sentence, at most 20 words, no contractions.

## Per artifact

**Doc pages.** Decide the type before writing — tutorial (learn by doing), how-to (reach a goal, competence assumed), reference (neutral description), explanation (why) — and stay in it. Keep the doc next to the code it describes; fewer, denser files. A subsystem page is: what this is (one paragraph, business purpose), gotchas, key decisions, relationships. Update a doc when a decision changes, not when code changes; delete a gotcha once it is fixed.

**README.** What it is and for whom, install, the most common usage with copy-paste commands, then the rest. Contributor and build-from-source setup last: most readers are users.

**Doc comments (Javadoc, docstrings).** The first sentence stands alone as the summary. Say what the thing is for and what the caller must know — contracts, side effects, thread-safety, what it throws and when — one level above the code. Never restate the signature or the name. Follow the language's convention for the summary verb (Javadoc "Returns the…", Python "Return the…"). A getter, setter, or an obvious constructor gets no comment.

**Inline comments.** Only what the code cannot say: intent, constraint, trade-off, a rejected simpler approach and why. If someone could write the comment from the code alone, delete it. A comment that needs a paragraph points at an abstraction that needs fixing. Revisit a comment when it stops being true, not when nearby code changes.

**Commit messages.** Subject in the imperative, under about 70 characters, no trailing period. Blank line. Body says what changed and why — the constraint that forced the change, the alternative rejected — never how; the diff shows how.

**MR / PR descriptions.** For the reviewer: why (the problem, with the ticket link) → what changed, as a short list → how to review (where to start, what to look at closely, how it was tested) → how to release (migrations and their order, config or secrets to set, feature flags, deploy order across services, what to watch after, how to roll back) → risks and follow-ups. Omit the release section only when a plain deploy is enough. Nothing the diff already shows.

**Error messages.** What happened, and what the reader can do next. Specific, not "operation failed". No blame words (invalid, illegal, wrong), no jargon, no humor, no exclamation marks. Keep the user's input available for correction.

**Release notes and changelogs.** For humans, never a commit dump. Breaking changes first, each with what breaks and the migration steps to take. Then the rest, grouped: Added, Changed, Deprecated, Removed, Fixed, Security. Newest version first, ISO date on each.

**Messages to other people (chat, review threads, ticket comments, email).** Very short: the highlights that the reader needs to act on, and a link to the full document for everything else. The reader must not read the same thing twice.

## Self-lint before returning text

1. A sentence over 25 words, or over 20 in a procedure? Split it.
2. Passive voice with a known actor? Make it active.
3. A nominalization, an "-ing" main verb, a phrasal verb? Replace with a plain verb.
4. The same thing named two ways? Pick one.
5. A sentence that restates the code, narrates the change, or lists what a file contains? Delete it.
6. A marketing adjective or an LLM word? Delete it.

These rules fix the form of the text. They cannot make a hollow paragraph true — if a section has nothing to say that the code does not, delete the section.
