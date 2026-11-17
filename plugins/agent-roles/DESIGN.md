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
- **No launching.** The plugin starts no sessions and imports no code from other projects. A launcher such as cc-auth-switch can put a role into the system prompt; the plugin then stays silent for that session.

## Principles

1. **Injected, not loaded.** A skill has to be loaded, and a subagent that skips it acts unconstrained. The cost is the role's tokens in every agent.
2. **Each role file stands alone.** Hooks from other plugins write on the same events in an unspecified order, so a role never refers to anything outside itself.
3. **The payload decides, never a brief.** No hook payload carries a nesting depth or a parent; `agent_type` is the only value the caller sets that reaches `SubagentStart`. A role is keyed on it, never on what a prompt claims.
4. **Every role file stays under 9,500 characters.** Claude Code replaces a hook's `additionalContext` above 10,000 characters with a short preview and a file path. `make test` fails above 9,500.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-05 | The session gets an orchestrator role, every subagent a worker role, from a plugin instead of `~/.claude/` | Six installer copies drifted apart; plugin `SessionStart` hooks were believed not to fire, which was never tested and is false on 2.1.260 |
| 2026-09-05 | An unknown problem is probed on a small slice, then the same subagent is resumed for the full scope | A subagent handed the full problem runs its first idea against the full scope and fights it for an hour |
| 2026-09-05 | A worker sizes a wait to the job, 2–10 minutes for a pipeline | Fixed sleeps either overshoot a short job or poll a long one too often |
| 2026-09-21 | The worker role splits into `task-worker` and `resident-worker`, picked by `agent_type` through the `resident_agent_types` option | A resident watcher ends its turn only on its stop condition and reports by message, which contradicts the task role |
| 2026-10-09 | The orchestrator quotes the user's request and names every later write in a subagent's first prompt, never "read-only" | The auto mode classifier treats the first prompt as the user's instruction and a later message from the orchestrator as no consent |
| 2026-11-09 | The resident role and its `resident_agent_types` option are removed; every subagent gets the task role | `mr-babysit` and `code-review:watch` moved to `glab-watch` background tasks that report by message, so no subagent stayed resident |
| 2026-11-10 | The resident role comes back, with no resident type by default; the option alone lists them | The removal took the role away from other resident subagents together with its only default user, `glab:mr-watch` |
| 2026-11-17 | A subagent's model is picked by three questions (is the path known, does something catch a wrong result, what builds on the result) over four tiers, haiku to fable | "Subtask complexity" was vague. Haiku is proven only for `noisy-runner` (`plugins/noisy-tools-in-subagent/DESIGN.md`). The claim that a weak model fails silently on exploration is adopted without measurement |
| 2026-11-17 | Between two tiers, work whose error nobody would notice takes the stronger model; work with a check behind it keeps opus over fable. Open-ended research is fable | An exploration error nobody notices costs more than the model. Open-ended investigation moves from opus to fable, which costs more |
| 2026-11-17 | The roles are `worker`, `task-subagent` and `resident-subagent`; the top-level session is a worker on one task | A dispatcher role that runs worker sessions is coming, and "orchestrator" does not tell the two session levels apart. Subagent roles say "subagent" so a session role and a subagent role cannot be confused |
| 2026-11-17 | `SessionStart` follows the cc-auth-switch role variables: silent when the role is in the system prompt, the launcher's file in mode `none`, `roles/<name>.md` for a bare role name, else the `default_role` option (`worker`) | The launcher config stays the one place that names a role's file, and a role in the system prompt survives compaction without a 10,000-character limit. Without a launcher the plugin behaves as before |

## How changes are checked

`make test` runs `hooks/test-inject-role.sh`, which feeds the hook payloads and environments and checks which role comes out, and fails when a role file exceeds 9,500 characters. The rules themselves have no eval suite: check a change to a role text by running a session that exercises the rule, and say in the commit that it was not measured when it was not.
