---
name: mermaid
description: Write Mermaid diagrams that render on GitLab, GitHub, Linear and in IDE previews — whether a diagram is worth drawing at all, which type to pick, the syntax that survives both renderers, the size budget, and a render-and-look validation loop through a `diagrams:mermaid-validate` subagent. Use when a plan, MR description, review comment, ticket or doc would be clearer with a picture, or when an existing mermaid block has to be repaired.
trigger-keywords: mermaid, diagram, flowchart, sequence diagram, state diagram, er diagram, draw this, visualize, visualise
---

# mermaid

A diagram in a plan, an MR description or a review comment is a **sketch**: selective, carrying one idea, thrown away when the work lands. It is not a specification of the system, and completeness is not the goal — "comprehensiveness is the enemy of comprehensibility" ([Fowler](https://martinfowler.com/bliki/UmlAsSketch.html)).

The unit of work is a standalone `.mmd` file in the scratchpad, one diagram per file, with no code fence around it. Write it, validate it there, then hand the file content to whatever document needs it inside a `mermaid` code fence. Inlining is the calling command's last step, not this skill's.

## 1. Whether to draw at all

**Write text instead when** the relationship is linear (a numbered list), there are fewer than about three nodes (a sentence), the content is a payload or a data structure (a code fence), the reader needs exact values such as timeouts or error codes (a table), or you cannot say in one sentence what the reader should conclude. A picture with no conclusion is decoration.

**Draw when** a flow crosses three or more components, an entity has a lifecycle with guarded transitions, the point is ordering — a race, a retry, a handshake — or a structure changes and the before/after difference is the finding.

## 2. Which type

- **`flowchart`** — the path a request takes through components, a decision with branches. The default when nothing more specific fits.
- **`sequenceDiagram`** — who calls whom in what order, two to six participants. The only type that shows time.
- **`stateDiagram-v2`** — one entity's lifecycle: order status, job state, a saga. Not a process with no return.
- **`erDiagram`** — tables and cardinality for a schema change. Not an object model.

Secondary, when they clearly fit: `classDiagram`, `gitGraph`, `timeline`. Every type with `-beta` in its keyword, every `C4*` type and `mindmap` are opt-in only — use one when the user asks for it by name. [`references/diagram-types.md`](references/diagram-types.md) has the per-type "use when / do not use when / pitfalls" table, including the reasons the beta types are excluded.

## 3. Authoring rules

- **Give it a title** in frontmatter, and set config there too. `%%{init: ...}%%` directives are deprecated; frontmatter is the current form and both hosts are far past the version that needs it.
- **Show the mechanism, not boxes with nouns.** Draw the path a request takes, not a box labeled "system".
- **Label every arrow with a verb**: `writes`, `invalidates`, `polls every 30s`. An unlabeled arrow means "related somehow", which is worth nothing.
- **12 to 15 nodes is the ceiling.** Past that, auto-layout stops producing something readable and the answer is two diagrams, not a bigger one.
- **Quote any label containing anything outside `[A-Za-z0-9 _-]`.** `A["Cache (Redis)"]`, never `A[Cache (Redis)]`. This one rule prevents most parse errors.
- **`<br>` for a line break, never `<br/>`.** GitLab rewrites `<br/>`; GitHub does not.
- **`flowchart`, not `graph`**, and `-->|label|` for edge labels. `%%` starts a comment; a single `%` does not.
- **No `classDef` or styling on the first pass.** GitHub applies its own theme to match the reader's light or dark setting, so colors are not yours to control there.
- **In a sequence diagram use `->>+` and `-->>-`** rather than bare `activate` / `deactivate`, so activation is balanced by construction — unbalanced activation is the most-failed dimension in the one published benchmark of LLM-generated sequence diagrams ([MermaidSeqBench](https://arxiv.org/html/2511.14967v3)). **Draw the error path, not only the happy path**; missing failure branches is the second-most-failed dimension there.

```
---
title: Cart checkout
config:
  theme: neutral
---
flowchart LR
  %% one idea: where the reservation is written before payment
  Client -->|POST /orders| API["Order API"]
  API -->|reserves lines| Stock["Stock service (Redis)"]
  API -->|publishes OrderPlaced| Bus{{Event bus}}
  Bus -->|charges| Billing["Billing worker"]
```

[`references/pitfalls.md`](references/pitfalls.md) is the broken/fixed table. Read it when a render fails, not before.

## 4. Size budget

GitLab auto-renders at most **2000 characters of mermaid per page**, counted as a running total across every fence on the page, and at most 50 blocks. MR descriptions, MR comments, issues and epics are **not** exempt — only wikis, the repo landing README and the file view are. Over budget nothing errors: the diagram is replaced by a yellow "Displaying this diagram might cause performance issues on this page" warning with a **Display** button the reader has to click, which is worse than no diagram.

Keep each diagram **under about 700 characters** (`wc -c <slug>.mmd`) and put **at most three** on one page. GitHub documents no such limit. Linear renders mermaid natively since November 2025. Anywhere else — npm, PyPI, PDF export, most static site generators — the fence degrades to a plain code block, so the source should still read acceptably as text.

## 5. Workflow

1. **Check the renderer is there:** `command -v mmdc >/dev/null && mmdc --version || echo "mmdc missing"`. If it is missing, read [`references/install.md`](references/install.md), propose the install to the user, and stop. Never ship an unvalidated diagram in silence. `npx` finding a cached copy does not count — the validator subagent runs `mmdc`, so `mmdc` is what has to be on PATH.
2. **Write `<scratchpad>/<slug>.mmd`** — bare mermaid source, no code fence, no surrounding markdown.
3. **Spawn a validator subagent** (model `sonnet`) and wait for it. Its prompt is exactly this, with the absolute path filled in:

   ```
   First, invoke the diagrams:mermaid-validate skill to load its usage guidance before running any commands. Validate <absolute path>.mmd.
   ```

   It reports the render status, then what it sees in the picture, then a verdict of "clear" or "confusing because …" with concrete suggestions.
4. **Read the report.** If the render failed, read [`references/pitfalls.md`](references/pitfalls.md) and fix the source from the reported error. If the picture is confusing, decide whether to change it — you own the diagram, and not every remark needs a change.
5. **After a change, message the same validator subagent** ("check again") instead of spawning a new one. It still holds the previous render and its own earlier remarks, so it can say what actually changed.
6. **Done** when the render passes and you accept the picture. Then hand the `.mmd` content to the document that needs it, wrapped in a `mermaid` code fence.
