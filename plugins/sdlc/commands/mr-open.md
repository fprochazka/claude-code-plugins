---
description: Open a draft MR for the current branch and refine its title and description
argument-hint: [ticket-id]
allowed-tools: Bash, Read, Edit, Write, Skill, Agent
---

# Open MR

Open a draft merge/pull request for the current branch, then refine the title and description so they accurately describe the actual changes.

$ARGUMENTS

## Process

1. **Load skills** — invoke the `git:git-workflow` skill for commit/MR shaping judgment. Also invoke the skill that covers the CLI for the remote host (GitHub, GitLab, …) so you don't guess at its syntax.
2. **Open the draft MR** — push the branch, then open the merge/pull request **as a draft**, targeting the repository's base branch and assigned to the user. Prefer whatever the project or the user's setup already provides for this — a dedicated script or alias that derives the title from the ticket, otherwise the host's CLI directly. If an MR/PR for this branch already exists, take its URL and proceed to step 3.
3. **Inspect what actually changed** — review the diff against the base branch and the commit history. Don't trust the original ticket title/description verbatim; the implementation may have diverged.
4. **Write an accurate title** — short, imperative, specific. Keep the repository's title convention, including any `<ticket-id>:` prefix already in place. Update the rest to describe what the MR actually does.
5. **Write a description for the reviewer** — the goal is to set the reviewer up with the right optics for reading the diff, not to recap *what* changed (the diff already shows that). Cover, as applicable:
   - **Why** — the motivation / problem being solved, the constraint or decision that shaped the approach. If the ticket already captures this well, a one-line pointer is enough.
   - **Gotchas** — non-obvious tradeoffs, things that look wrong but aren't, assumptions that depend on external state, anything a reviewer might flag as a bug without context.
   - **Where to focus** — call out the 1-3 most complex / load-bearing parts of the diff (with file:line pointers) that deserve the most careful review. Trivial parts (renames, formatting, mechanical refactors) can be explicitly de-prioritized.
   - Keep it tight. No empty sections, no filler, no "already done in branch X" meta-commentary.
6. **Update the MR** — write the new description to a file in the session scratchpad dir (e.g. `<scratchpad>/<ticket-or-branch>-mr-description.md`), then set it through the host's CLI by reading that file into the argument rather than inlining the text. Update the title the same way if it changed.
7. **Report** — print the MR URL and a one-line summary of what you set.

## Notes

- Keep the MR in **draft** state — do not mark it ready.
- Do not push `--no-verify` or skip hooks if the push fails on a hook; fix the underlying issue.
- If the repository's title convention needs a ticket ID, the branch has none recorded, and no `<ticket-id>` arg was passed, ask the user for it before opening the MR.
