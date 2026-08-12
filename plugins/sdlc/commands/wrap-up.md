---
description: Post a condensed wrap-up comment to the ticket — outcome, verification numbers, findings, follow-ups — and mark it completed
argument-hint: [ticket ref or extra context]
allowed-tools: AskUserQuestion, Read, Glob, Bash, Write, Edit, Skill
---

# Wrap Up

Close out finished work: post one dense comment to the ticket with everything this session learned that is worth keeping, then mark the ticket completed in the issue tracker.

## Scope

$ARGUMENTS

## Sources

**You (the orchestrator) write the comment yourself — never a subagent.** The primary source is the conversation you are holding, and no subagent can see it. Priority order: (1) the session itself, including every production check, query result, and dashboard reading done in it, (2) `./.claude/plans/*.md` for what the work set out to do, (3) the diff and the MR discussion, as far as the session already read them. **Do not go exploring for new material and do not re-run the analysis** — a fact the session never established stays out of the comment.

Numbers must be the real ones you saw. Never reconstruct a figure from memory of a shape ("about 5%"). If you cannot state a number exactly as it was measured, drop it or state the reading you actually have.

## Process

1. **Take the scope from the session.** This command normally runs at the end of the work it wraps up, so the ticket, the MR, and the checks are already in the conversation. Use them. The scope above only narrows or overrides that, and is empty most of the time. Fall back to the branch name or the MR title when the session is genuinely fresh, and ask the user only when the session covered several tickets and you cannot tell which one is finished. Load the skill for the issue tracker in play — you need it to post and to close.
2. **Judge from the session whether the work is finished** — MR merged, CI green on the target branch, every step of the plan done. **Do not go and look any of it up.** You either watched it happen or you did not. If the session left something open, say so in your reply to the user and ask before you mark the ticket completed. If the session never established a state at all, treat it as unknown, keep it out of the comment, and mention it to the user. Post the comment either way.
3. **Draft the comment to `<scratchpad>/<ticket-id>-wrap-up.md`.** Follow the structure and the density rules below. When the material calls for more than one comment, draft each into its own numbered file — `<ticket-id>-wrap-up-1-outcome.md`, `-2-verification.md`, and so on.
4. **Show the user a high-level summary and the file paths.** They can read the drafts from the files. Iterate if they want changes.
5. **Post the comments** by reading each file into the argument (`"$(cat <path>)"`), not by inlining the text. Post them in file order, so the ticket reads top to bottom.
6. **Mark the ticket completed** — read the tracker's real workflow states and pick its terminal one instead of guessing a name. Do not change assignee, labels, project, or priority.
7. **Report** — ticket URL, the state you set, and the follow-ups worth filing. Point at `/sdlc:ticket-new` for those. Do not file them yourself.

## The comment

Every section is optional. Drop the heading when there is nothing to put under it.

- **Outcome** — one or two lines. What now works that did not before, and where it is deployed. **Leave the MR link out** — the ticket already carries it. Name an MR only when the work spans several and the comment says something different about each one.
- **Verification** — what was checked and what came back. This is the heart of the comment when the session verified anything on production. Per check: what you asked, the result with units, the time window, and the source, so a reader can re-run it. Name the connection, the dashboard, the log query, the endpoint. A production check with no number attached is worth less than the number alone.
- **Findings** — facts about the system the diff does not show and the ticket did not know: a wrong assumption in the ticket, a legacy naming trap, coupling nobody expected, the real size of the affected data.
- **Limits** — what the change does not cover, and any condition it depends on.
- **Possible follow-ups** — one line each. What is true, and what could be done about it. Never that it will be done.

## Splitting into several comments

One comment is the default. Split when the material is long enough that a single comment buries its own best parts — a production verification with many readings, or a set of follow-ups that each deserve their own thread.

- Split along the section boundaries above, never mid-section. The usual cut is: what we did, how we verified it on production, what to consider next.
- Each comment stands on its own and carries its own heading. Do not write "continued from above" or number them in the text — the ticket already shows the order.
- Splitting does not buy more room. Every comment obeys the density rules below on its own, and three padded comments are worse than one dense one.
- Follow-ups as a separate comment is the one split worth making even when the material is short. It keeps the thread that people reply to away from the record of what shipped.

## Density

- Hard ceiling ~50 lines per comment, **no floor**. Padding is a failure. Every line carries a fact, a number, or a pointer.
- Use a bare list for anything with more than two items. No prose bridges between sections, no closing paragraph.
- Never restate the ticket, the acceptance criteria, or the diff. The reader has all three.
- Never narrate the session — no "first we tried X", no "it turned out that", no ordering by when you learned it. Order by what matters most to a reader six months from now.
- Cut adjectives that carry no information. "Runs in 40 ms at p99" beats "performance is good".

## Hard rules

- The comment is addressed to other people. **State findings, facts, causes, and numbers. Stop there.** No commitments, no timelines, no "we will fix", "next release", "a ticket is coming", or any softer version of the same. This holds for the follow-ups section above all — a follow-up is an observation and an option, never planned work.
- Do not ask anyone to wait for anything, and do not say work is under way unless the user told you it is.
- **The session is the whole world.** Report what it established and nothing else. Do not check a pipeline, re-read a ticket, re-query production, or look up a status to fill a gap. A gap stays a gap — leave it out of the comment and tell the user instead.
- Do not invent a verification you did not run. Missing coverage goes under Limits.
- Do not change code, do not commit, do not touch the MR.
