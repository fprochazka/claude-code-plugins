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

1. **Load skills** — invoke the `git:git-workflow` skill for commit/MR shaping judgment, and the skill that covers the CLI for the remote host (GitHub, GitLab, …) so you don't guess at its syntax. On GitLab, also invoke the `glab:glab-discussion` skill — step 5 posts standalone MR discussions and that is where their syntax lives. Resolve the tracker with the `teamwork:workflow-identify` skill and invoke the installed skill it names; this command names no tracker CLI of its own. The ticket is usually already in context from earlier in the session — read it through that skill if it is not.
2. **Open the draft MR** — push the branch, then open the merge/pull request **as a draft**, targeting the repository's base branch and assigned to the user. If an **open** MR/PR for this branch already exists, take its URL and carry on with step 3. A merged or closed MR of an earlier branch with the same name does not count. On GitLab, set both merge options explicitly, so that the project defaults do not decide them:
   - **Delete the source branch on merge**: always on (`--remove-source-branch=true`).
   - **Squash on merge**: judge the branch history by the `git:git-workflow` skill. Keep a history that a reviewer can read commit by commit, with atomic commits whose subjects name a behavior: `--squash-before-merge=false`. Squash a history that cannot be read that way, with `WIP` commits, "address review" or "fix previous commit" commits, or a feature split into build steps: `--squash-before-merge=true`. Pending `fixup!` and `squash!` commits do not make a history messy, because they are autosquashed before the merge.

   On an MR that already exists, set both through the API fields `remove_source_branch` and `squash`. `glab mr update` toggles these two flags instead of setting them. A project that requires or forbids squash overrides the MR's value. On GitHub both are repository settings and the merge method is picked at merge time, so skip them there.
3. **Inspect what actually changed** — review the diff against the base branch and the commit history. Don't trust the original ticket title/description verbatim; the implementation may have diverged.
4. **Put the Why in the ticket** — the problem, the constraints, and the decision that shaped the approach, in the ticket and never in the MR description. If the ticket body is empty or a stub, write it from the work actually done. If the body already carries content, leave it alone and add the approach as a ticket comment. Then tell the user which of the two you did and what you wrote.
5. **Post the MR comments** — each one a top-level MR discussion, and each one only when it has something to say. An empty heading posted anyway is noise the reviewer has to read past. Write every body to a scratchpad file and pass it with `"$(cat …)"` rather than inlining it. Every body ends with `<!-- sdlc:mr-open -->`, following the `glab:glab-discussion` skill's comment-signing convention.
   - **Guidelines for reviewer** — what changed and the order to read it in; the one to three most load-bearing parts of the diff, with `file:line` pointers; what to skim (renames, formatting, mechanical refactors); the gotchas and trade-offs, meaning the parts that look wrong until you know the constraint. If the change is one a reader would follow faster from a picture — a flow crossing three or more components, a state machine, an ordering-sensitive interaction, a before/after structural change — draw it as a diagram in this comment, and invoke the `diagrams:mermaid` skill first so the diagram is written and validated the right way. One diagram is the budget here: GitLab renders at most 2000 characters of mermaid per page, shared across every fence on it.
   - **Release procedure** — only when releasing the change needs more than a plain deploy: migration ordering, a feature flag, config or secrets to set, a backfill, deploy order across services, what to watch afterwards, how to roll back. Its own thread, so the release can be discussed without disturbing the review threads.
   - **Verification results** — only when you have measured evidence: before/after numbers, a rebuilt export compared against the old one, a benchmark, a query plan. Every number names where it came from, and nothing you did not measure goes in.
6. **Write the description** — it must fit one screen without scrolling. **Hard cap ~12 lines**, and it holds exactly three things:
   - the ticket link, on its own line;
   - what the change does, in three to six sentences — behavior, not mechanism;
   - when step 5 posted a release procedure, one line: `**Must read before release:** <link to that comment>`.

   Nothing else belongs here. No Why (it is in the ticket), no commit list, no per-commit bullets, no tables, no analysis, no "where to focus" (that is the reviewer comment), no "already done in branch X" meta-commentary. The comments are posted before this step so their links are known.
7. **Set the title and description** — the title is short, imperative and specific. It follows the repository's title convention: the one its agent instructions (`AGENTS.md`, `CLAUDE.md`) state, otherwise the one that recent commits on the base branch follow, a `<ticket-id>:` prefix included. Write the description to `<scratchpad>/<ticket-or-branch>-mr-description.md` and set it through the host's CLI with `"$(cat …)"` rather than inlining the text.
8. **Report** — print the MR URL, one line per comment you posted, what you wrote to the ticket, the title you set, and the squash verdict with its reason. On GitHub, say that the merge options were left to the repository settings.

## Notes

- Keep the MR in **draft** state — do not mark it ready.
- **Promise nothing** in anything you post — invoke `teamwork:review-handshake` for the rule. The ticket update, the MR comments and the description state facts: what the change does, what was measured, what the release needs.
- Do not push `--no-verify` or skip hooks if the push fails on a hook; fix the underlying issue.
- Take the ticket ID from the `<ticket-id>` arg, then from the session context, then from the branch name, matched against the ticket pattern that `teamwork:workflow-identify` returns. If the title convention needs a ticket ID and none of these gives one, ask the user for it before opening the MR.
