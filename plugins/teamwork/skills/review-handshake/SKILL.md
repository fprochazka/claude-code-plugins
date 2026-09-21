---
name: review-handshake
description: The protocol between the author side and the reviewer side of a merge request — how the ticket state and the draft flag say whose court the ball is in, what each side may do to the other's threads, how posted comments are signed, and where the run's ledgers live. Use when a command hands work over for review or takes it back, replies to or resolves a review thread, or asks "is this MR ready for review", "who has the ball", "may I resolve this thread". The sdlc and code-review commands invoke this skill by name.
trigger-keywords: ready for review, back to work, hand over, handshake, resolve the thread, review thread
---

# review-handshake

Two agents share one merge request: the author side, `/sdlc:mr-babysit`, which changes code, and the reviewer side, `/code-review:watch`, which never does. They never talk to each other directly. They agree on the state of the MR through the conventions below, and every one of them is read at run time from the MR and the ticket, never from memory.

## Whose court the ball is in

The ticket carries the ball. The MR's draft flag says only whether the work was ever handed over.

1. **The author works.** The MR is draft, the ticket is in `WORK_STATE`.
2. **The author hands over**: the MR is marked ready and the ticket moves to `REVIEW_STATE`. Neither side sets the draft flag again, but GitLab may: a push whose commit title starts with `fixup!` or `WIP` re-drafts the MR on its own. So marking ready is part of every move to `REVIEW_STATE`, not only the first, and it is a no-op when the MR is already ready.
3. **The reviewer reviews.** Either it comments that all is good and leaves the ticket in `REVIEW_STATE`, since approving and merging is a human's decision, or it posts its findings and moves the ticket back to `WORK_STATE`. It does not touch the draft flag.
4. **The author addresses the feedback**, marks the MR ready again in case a push re-drafted it, and moves the ticket back to `REVIEW_STATE`. The author side also moves the ticket to `WORK_STATE` itself when it takes work back after a handover, a red pipeline for example, with a comment saying why.

So **ready for review** is the ticket in `REVIEW_STATE` and the MR not draft; **back to work** is the ticket in `WORK_STATE`. The one broken state is a draft MR under a ticket in `REVIEW_STATE`: work that was never handed over, marked as if it were. A command that finds it does not repair it for the other side and does not comment on the mismatch; it waits.

The state names come from the `teamwork:workflow-identify` skill, resolved once per run and never hardcoded. With `tracker: none` nothing but the draft flag is left to carry the ball, so it carries it both ways: draft is back to work, ready is ready for review, and the reviewer re-drafts to hand back.

This is a convention of this protocol, not a law of the tracker. A watcher that reads the handshake for a command takes the definition from that command's prompt, written as conditions over the fields it observes.

## What each side does to the other's threads

- **The reviewer** opens finding threads, verifies a fix against the code at the MR head, and resolves its own threads on that evidence. It never resolves a thread the author opened, and it never changes code.
- **The author** replies to a reviewer's thread with the fix and its SHA, or with a reasoned disagreement, and **never resolves a reviewer's thread on its own initiative**. Resolving it would remove the reviewer's only signal that the finding still needs checking, and the reviewer un-resolves it again. The one exception is the user telling the author to resolve a specific thread; that is the person's decision.
- A reviewer thread that shows as resolved without the reviewer's verdict behind it was therefore closed on a person's decision, and the reviewer addresses that person when it un-resolves it.
- Threads by other reviewers, human or bot, keep the ordinary rules: the author resolves a bot nit it fully handled, and leaves a human's thread open when the person may want the last word.

## Signing a posted comment

Every comment a command posts on an MR ends with a blank line and an HTML comment naming the command that caused it:

```
<!-- <plugin>:<command> -->
```

The marker is invisible in rendered Markdown and stays in the API body. It tells a reader which automation wrote the comment, lets a later pass of the same command recognize its own threads, and lets a watcher tell one side's notes from the other's. Recognition is a **last-line equality** check, never a substring match, because review prose often quotes a marker in backticks. A command that runs another command's posting steps signs with its own name, since it is the cause. The git-host skill in play carries the same rule for its CLI; on GitLab that is the `glab` skill.

## Where the ledgers live

Every command that runs across more than one turn keeps its state in `./.claude/review-report/<topic>.<command>.md` in the working tree, one file per command per topic: `<topic>.babysit.md`, `<topic>.watch.md`, `<topic>.mr-watch.md`. The directory is in the repository so a fresh context window can pick the run up, and the sibling naming keeps the author's, the reviewer's and the watcher's files apart on one MR. A command writes only its own file and reads the others.

## Writing to other people

Every comment, ticket note, MR description or wrap-up these commands post is read by people who are not the user, and none of it may commit the user to anything.

- **State findings, facts, causes and numbers. Stop there.** What changed, which SHA carries it, why a finding does not hold, what the verification measured.
- **Promise nothing.** No "we will fix", "a follow-up is coming", "this will be improved", "next release", "a ticket is coming", or any softer paraphrase. A defect being real is not permission to announce that it will be fixed. A follow-up is an observation and an option, never planned work.
- **Do not ask anyone to wait**, and do not say work is under way unless the user said it is.
- **A fix that belongs in the picture is described as an option** in the reply to the user, not in the text addressed to others. Only the user decides what gets promised.
- **A reply that announces a fix names the commit that carries it.** A fix without a SHA is a promise.

The form rules for the same text, short sentences, plain words, no narration of the change, live in the `prose:technical-writing` skill.
