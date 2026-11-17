# agent-roles: design

Read this before changing the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

A Claude Code session that does everything in its own context fills that context with grep output, build logs and dead ends, and stops responding to its user while it works. A subagent that backgrounds its work or promises to wait reports on work that never ran. This plugin gives every agent a role before its first tool call: the top-level session talks to the user and delegates, and each subagent works in the foreground and ends with findings or reports by message.

The role texts lived in `~/.claude/` behind a hand-wired hook, which the profile installer copied into every profile, so they drifted apart as six copies. A plugin keeps one copy.

## Goals

- One role per kind of agent, delivered by a hook, so the rules are in place without the agent loading anything.
- Role files that read correctly on their own, in any order next to other hooks' context, at any nesting depth.
- Rules calibrated from one person's experience with this harness, stated with the reason, so a reader can disagree with the reason rather than the rule.

## Non-goals and scope

- **No enforcement.** Nothing blocks a tool call. The `noisy-tools-in-subagent` plugin enforces the delegation of noisy commands.
- **No launching.** The plugin starts no sessions and imports no code from other projects.

## Principles

1. **Injected, not loaded.** A skill has to be loaded, and a subagent that skips it acts unconstrained. The cost is the role's tokens in every agent.
2. **Each role file stands alone.** Hooks from other plugins write on the same events in an unspecified order, so a role never refers to anything outside itself.
3. **The payload decides, never a brief.** No hook payload carries a nesting depth or a parent; `agent_type` is the only value the caller sets that reaches `SubagentStart`. A role is keyed on it, never on what a prompt claims.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-05 | The session gets an orchestrator role, every subagent a worker role, from a plugin instead of `~/.claude/` | Six installer copies drifted apart; plugin `SessionStart` hooks were believed not to fire, which was never tested and is false on 2.1.260 |
| 2026-09-05 | An unknown problem is probed on a small slice, then the same subagent is resumed for the full scope | A subagent handed the full problem runs its first idea against the full scope and fights it for an hour |
| 2026-09-05 | A worker sizes a wait to the job, 2–10 minutes for a pipeline | Fixed sleeps either overshoot a short job or poll a long one too often |
| 2026-09-21 | The worker role splits into `task-worker` and `resident-worker`, picked by `agent_type` through the `resident_agent_types` option | A resident watcher ends its turn only on its stop condition and reports by message, which contradicts the task role |
| 2026-10-09 | The orchestrator quotes the user's request and names every later write in a subagent's first prompt, never "read-only" | The auto mode classifier treats the first prompt as the user's instruction and a later message from the orchestrator as no consent |
| 2026-11-10 | The resident role stays, with no resident type by default | Its only default user, `glab:mr-watch`, was removed; the role stays for other resident subagents |

## How changes are checked

`make test` runs `hooks/test-inject-role.sh`, which feeds the hook payloads and environments and checks which role comes out. The rules themselves have no eval suite: check a change to a role text by running a session that exercises the rule, and say in the commit that it was not measured when it was not.
