# prose: design

Read this before changing the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

Claude's chat replies were too long to read between two other tasks: walls of text, narration of the work, subagent reports repeated in full, conclusions buried at the end. Its docs and code comments restated the code, narrated changes ("previously X, now Y"), and referenced tickets. A scan of a month of the maintainer's sessions before the plugin existed found verbosity to be the dominant complaint by a wide margin, followed by narration, repeated content, and messages to other people that were too long.

The plugin gives Claude two rule sets and keeps them in force: `reply-style` for the form of replies to the user, and `technical-writing` for text that other people read. It replaced three private pieces in `~/.claude`: the code-comment rules (2026-06-10), an imported ASD-STE100 writing skill (2026-07-31), and the `/bro` restate command (2026-08-07). It was designed and first shipped on 2026-09-02 in session `0f25c096-45e8-4447-a275-d0f7d37750c1`.

## Goals

- A reply the user can read on a screen between two other things: the result first, length that follows the question, and what the user must act on stated where it cannot be missed.
- Short by selection, never by compression. When short and clear conflict, clear wins.
- The rules hold for the whole session, through long runs and context compaction, without the user having to repeat them.
- Docs and comments say what the code cannot: why, gotchas, business meaning, non-obvious relationships, legacy reasons. They describe the current state only.
- Plain language underneath both skills: short active sentences, plain verbs, one name per thing, derived from ASD-STE100 and relaxed for conversation.

## Non-goals and scope

- **Working method is out of scope.** When to ask for approval, when to stop or check in, finishing the task, verifying claims before reporting, following earlier instructions, debugging strategy. These are real problems, but they belong in other instructions. `reply-style` covers the form of a reply; it may say how to ask a question, never whether to ask one.
- **Rules about what to tell other people** (never promise work, facts only) live in `teamwork:review-handshake`, not here. `technical-writing` covers form.
- **Not a voice.** The rules strip filler and structure the text; they do not imitate a person.
- **Not an output style.** The plugin assumes `outputStyle` is left at `default`.
- **Not a linter.** The self-lint sections are checklists for the model.

## Principles

1. **Short skill text beats a slightly better score.** The rules compete with the task for the model's attention. A skill may grow a little when a measured gain needs it, but not explode: as a guideline, each skill stays within about a fifth above its 0.3.1 size (`reply-style` about 1.6k tokens, `technical-writing` about 2.2k), and an extra line is not worth arguing over. A rule stays only when it measurably helps; a rule whose removal changes nothing is deleted.
2. **The hook names the skill and says to load it, nothing more.** A paraphrase of the rules in the hook reads as sufficient guidance and the model stops loading the skill. Measured on 2026-10-03 over 121 sessions: with the 0.2.0 hook that summarized the rules, 11 of 16 sessions never loaded the skill; with the "load it" line, 3 of 105.
3. **The hook output is static.** It is saved in the transcript and replayed on `--resume`, so it may not depend on time or session state.
4. **No off switch.** A request for a different tone or style applies to that one reply, for that purpose. The next reply is back under the rules.
5. **Describe the wanted shape, and give the reason where it is not obvious.** The model generalizes from a reason; a bare ban list invites literal, narrow compliance.
6. **Consumers load the skills by name** through the Skill tool. Nobody passes skill file paths around.
7. **Changes are checked by evals, not by impression.** See [How changes are checked](#how-changes-are-checked).

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-06-10 | Comments and docs: why, not what; no change narration; no ticket references | Narrated history and ticket ids confuse later readers and go stale; git holds the history |
| 2026-08-01 | Plain-language (STE-flavored) rules apply to chat replies, not only to documents | The rules were being ignored in replies because they were scoped to artifacts |
| 2026-09-02 | One plugin, `prose`, with `reply-style` and `technical-writing`; the STE skill dissolved into both instead of shipped as-is | One place for both rule sets; the STE skill was third-party text written for a different scope |
| 2026-09-02 | Reminder through a `UserPromptSubmit` hook, a static bash + jq line, no transcript scanning, no `SubagentStart` hook | Output styles re-inject a reminder each turn because a style stated once stops being followed; the hook does the same without an output style. Simplest version first |
| 2026-09-02 | `skill-keyword-reminder` is a dependency and suggests `technical-writing` | Writing tasks are detected from prompt keywords |
| 2026-09-02 | Project patterns are documented once, centrally; a use of a pattern gets at most a pointer | Repeated explanation at every use goes stale; the pattern itself must be documented |
| 2026-09-02 | MR descriptions include how to release; release notes lead with breaking changes and migration steps | The reviewer and the releaser need these first |
| 2026-09-02 | The never-promise rule stays out of `technical-writing` | It is a rule about what to say to people, not about form. Moved to `teamwork:review-handshake` on 2026-09-21 |
| 2026-09-02 | Trigger keywords on `reply-style` added, then dropped the same day (0.1.1) | Two reminders fired on one prompt; the hook is the only reminder |
| 2026-09-03 | Progress note: "at most three lines", not "target three lines" | A cap is followed; a target drifts |
| 2026-09-03 | Removed: the "normal mode" off switch, the "debug spiral" section, "ask only for decisions that are yours" | Not prose rules: working method (see Non-goals) |
| 2026-09-07 | Hook reverted to the 0.1.x "load it" line (0.2.1); the 0.2.0 rule summary is not to be reintroduced | The skill loaded less often with the summary; confirmed by measurement on 2026-10-03 (Principle 2) |
| 2026-09-11 | The full mannered-prose paragraph from the Fable 5.1 prompting guide in both skills; corrections narrated only when they change the user's code, conclusions, or decisions (0.3.0) | Fable 5.1 writes denser, more figurative prose; Opus 5 narrates corrections. Putting the paragraph in the hook was considered and not adopted |
| 2026-09-11 | `bro` moved from `commands/` to `skills/` without content changes (0.3.1) | All commands in the marketplace became skills |
| 2026-10-03 | Changes are eval-driven, with a size budget; working-method rules are excluded from the rules and from the evals | Start of the first measured improvement round |

## How changes are checked

The eval suite lives in the private repository `github.com/fprochazka/claude-code-plugins-evals`, under `repos/fprochazka/claude-code-plugins/prose/`, because many cases are built from real sessions. Its repo skills describe the method. Before committing a change to a skill or the hook, run the suite against the current `master` and the change with `bin/run-evals fprochazka/claude-code-plugins prose <git-ref>`, and compare per case. A session without access to that repository says so in its summary instead of claiming the change was checked.

The suite is under construction as of 2026-10-03. Until it exists, a change to the rules needs the maintainer's explicit approval.
