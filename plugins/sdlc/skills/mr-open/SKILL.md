---
name: mr-open
description: Open a draft MR for the current branch — the Why in the ticket, the reviewer's guide in comments, a one-screen description
argument-hint: [ticket-id]
allowed-tools: Bash, Read, Edit, Write, Skill, Agent
---

# Open MR

Open a draft merge/pull request for the current branch, then write what the reviewer needs — each piece in the place it belongs. The Why goes to the ticket. The reading guide, the release procedure and the verification numbers go to MR comments, one thread each. The description stays a one-screen summary and nothing more.

$ARGUMENTS

## Where each piece goes

- **The ticket** holds the Why: the problem, the constraints, the decision that shaped the approach. It outlives the MR, and the people who look for that reasoning later look there.
- **MR comments** hold everything that invites a discussion — the reading guide, the release procedure, the measured results. Each is its own thread, so the reviewer can answer one without dragging the others into it.
- **The description** holds the ticket link and a short summary of what the change does. A reviewer reads it in fifteen seconds, before deciding where to start. Anything longer buries the thing that mattered.

## Process

1. **Load skills** — invoke the `git:git-workflow` skill for commit/MR shaping judgment, and the skill that covers the CLI for the remote host (GitHub, GitLab, …) so you don't guess at its syntax. On GitLab, also invoke the `glab-discussion` skill — step 5 posts standalone MR discussions and that is where their syntax lives. Resolve the tracker with the `sdlc:team-workflow-identify` skill and invoke the installed skill it names; this command names no tracker CLI of its own. The ticket is usually already in context from earlier in the session — read it through that skill if it is not.
2. **Open the draft MR** — push the branch, then open the merge/pull request **as a draft**, targeting the repository's base branch and assigned to the user. Prefer whatever the project or the user's setup already provides for this — a dedicated script or alias that derives the title from the ticket, otherwise the host's CLI directly. If an MR/PR for this branch already exists, take its URL and carry on with step 3.
3. **Inspect what actually changed** — review the diff against the base branch and the commit history. Don't trust the original ticket title/description verbatim; the implementation may have diverged.
4. **Put the Why in the ticket** — the problem, the constraints, and the decision that shaped the approach, in the ticket and never in the MR description. If the ticket body is empty or a stub, write it from the work actually done. If the body already carries content, leave it alone and add the approach as a ticket comment. Then tell the user which of the two you did and what you wrote.
5. **Post the MR comments** — each one a top-level MR discussion, and each one only when it has something to say. An empty heading posted anyway is noise the reviewer has to read past. Write every body to a scratchpad file and pass it with `"$(cat …)"` rather than inlining it. Every body ends with `<!-- sdlc:mr-open -->`, following the `glab` skill's comment-signing convention.
   - **Guidelines for reviewer** — what changed and the order to read it in; the one to three most load-bearing parts of the diff, with `file:line` pointers; what to skim (renames, formatting, mechanical refactors); the gotchas and trade-offs, meaning the parts that look wrong until you know the constraint. If the change is one a reader would follow faster from a picture — a flow crossing three or more components, a state machine, an ordering-sensitive interaction, a before/after structural change — draw it as a diagram in this comment, and invoke the `diagrams:mermaid` skill first so the diagram is written and validated the right way. One diagram is the budget here: GitLab renders at most 2000 characters of mermaid per page, shared across every fence on it.
   - **Release procedure** — only when releasing the change needs more than a plain deploy: migration ordering, a feature flag, config or secrets to set, a backfill, deploy order across services, what to watch afterwards, how to roll back. Its own thread, so the release can be discussed without disturbing the review threads.
   - **Verification results** — only when you have measured evidence: before/after numbers, a rebuilt export compared against the old one, a benchmark, a query plan. Every number names where it came from, and nothing you did not measure goes in.
6. **Write the description** — it must fit one screen without scrolling. **Hard cap ~12 lines**, and it holds exactly three things:
   - the ticket link, on its own line;
   - what the change does, in three to six sentences — behavior, not mechanism;
   - when step 5 posted a release procedure, one line: `**Must read before release:** <link to that comment>`.

   Nothing else belongs here. No Why (it is in the ticket), no commit list, no per-commit bullets, no tables, no analysis, no "where to focus" (that is the reviewer comment), no "already done in branch X" meta-commentary. The comments are posted before this step so their links are known.
7. **Set the title and description** — the title is short, imperative and specific, and it keeps the repository's title convention, including any `<ticket-id>:` prefix already in place. Write the description to `<scratchpad>/<ticket-or-branch>-mr-description.md` and set it through the host's CLI with `"$(cat …)"` rather than inlining the text.
8. **Report** — print the MR URL, one line per comment you posted, what you wrote to the ticket, and the title you set.

## Notes

- Keep the MR in **draft** state — do not mark it ready.
- **Promise nothing** in anything you post. The ticket update, the MR comments and the description state facts: what the change does, what was measured, what the release needs. No "we will fix", no timeline, no follow-up the user has not committed to.
- Do not push `--no-verify` or skip hooks if the push fails on a hook; fix the underlying issue.
- If the repository's title convention needs a ticket ID, the branch has none recorded, and no `<ticket-id>` arg was passed, ask the user for it before opening the MR.
