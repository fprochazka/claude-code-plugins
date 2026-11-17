# research: design

Read this before changing the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

Claude answers web questions from the first page of search results: it cites snippets it never read, stops after one search, and misses the precise terms that would have found the authoritative source. This plugin gives it a research method: search, read, learn the vocabulary and the primary sources, search again, and stop when the question is answered or the sources repeat each other. The answer cites the sources it rests on.

The method comes from two earlier agents in this marketplace: `web-researcher:agent`, which used the built-in WebSearch and WebFetch tools, and `searxngcli:agent`, which used the `searxng` CLI. Both had the same loop, each tied to one search tool. The maintainer stopped using the built-in WebSearch, and the searxngcli plugin moved to its own repository, so the loop now lives here without a tool attached.

## Goals

- One skill that works with any web search and page fetching the session has.
- Usable as a command (`/research:research <question>`) and loaded by Claude when the user asks to research something on the web.
- Answers that name the source of each claim, prefer primary sources, and say what stayed unconfirmed.

## Non-goals and scope

- **No tool choice.** The skill never names a search tool, a fetch tool, or their flags. Which backend runs the search is the user's setup: an installed CLI plugin, the built-in tools, or a permission rule.
- **No isolation.** The skill runs in the context of whoever loads it. Running research in a subagent, so the dead ends stay out of the main session, is the job of the agent-roles plugin and the caller.
- **No agent, no hooks, no model pin.** Each of these ties the plugin to a tool set or a runtime decision that belongs to the user.

## Principles

1. **Method, not mechanics.** The skill says "web search" and "fetch the page". A tool name in the text would make Claude prefer that tool even when the user set up another one.
2. **Read before citing.** A search snippet is a lead. Only a page that was fetched and read can be a source.
3. **Stop on evidence, not on a count.** The loop stops when the question is answered or the sources repeat. The round count is a guide, not a target.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-17 | One tool-agnostic skill replaces `web-researcher:agent` and the `searxngcli:agent` loop; the web-researcher plugin is removed | The maintainer no longer uses the built-in WebSearch, and the same method was kept twice, once per search tool |
| 2026-11-17 | No agent, hooks, `model:` pin or subagent instructions | Isolation in a research subagent is the agent-roles plugin's job; tool permissions belong to the tools' own plugins |

## How changes are checked

The plugin has no eval suite. Check a change by hand: run `/research:research` on a question with a known answer, once with each search backend you use, and confirm that the answer cites pages that were read and that the loop stops on its own. A change to the method needs the maintainer's explicit approval.
