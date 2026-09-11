---
name: mermaid-validate
description: Render one `.mmd` file with `mmdc`, look at the PNG, and report whether the diagram is correct and clear. Loaded by the validator subagent that `diagrams:mermaid` spawns, when its prompt names this skill. The author of the diagram fixes the source; this skill never edits it.
---

# mermaid-validate

You are the validator subagent. Your prompt names one `.mmd` file. Render it, look at the result, report. **Never edit the `.mmd` file** — the agent that spawned you owns it and decides what to change.

## Render

```bash
rm -f <slug>.png
mmdc -q -i <slug>.mmd -o <slug>.png -s 2
```

One command does both jobs: it fails on a syntax error, which is the lint, and it produces the picture, which is the visual check.

- **Do not pass `-w`.** On mermaid-cli 11.17.0 an explicit `-w` makes `-s` a no-op: `-w 1200 -s 1` and `-w 1200 -s 3` both produce the same 1184 px wide PNG, while `-s 2` alone produces 1568 px and `-s 3` produces 2352 px from the same source.
- **`-s` is the only size control you need.** With the default 800 px viewport the output is always 784 px times the scale, whatever the diagram: `-s 2` gives 1568 px wide, `-s 3` gives 2352 px. Start at `-s 2`; re-render at `-s 3` when the labels are too small for you to read them.
- **`-w` only ever shrinks a diagram, never enlarges it.** It sets the page viewport, and the SVG stops at its natural width — a sequence diagram whose natural width is 910 px renders at 910 px under both `-w 1600` and `-w 2400`. A diagram wider than the viewport is scaled down to fit, which is what makes small text small.
- **`command -v mmdc` comes first.** If `mmdc` is not on PATH, report that and stop. Do not install anything and do not reach for `npx` — the author handles the install.
- **A browser-launch failure is not a diagram problem.** `Failed to launch the browser process` with `No usable sandbox` means Chromium cannot start under this kernel's user-namespace restrictions. Write `{ "args": ["--no-sandbox", "--disable-dev-shm-usage"] }` to a `pptr.json` next to the diagram, retry once with `-p pptr.json`, and say in your report that you needed it.

## When the render fails

`mmdc` exits **1**, writes nothing to stdout under `-q`, prints the error on **stderr**, and **creates no output file** — which is why you delete a stale PNG first, so you can never report on a picture from an earlier round. A quoting error looks like this:

```
Error: Parse error on line 2:
...wchart LR  A[Cache (Redis)] --> B[API]
----------------------^
Expecting 'SQE', 'DOUBLECIRCLEEND', 'PE', ... got 'PS'
```

Report the first four lines verbatim and quote the offending source line from the file. The echoed source in the error is flattened onto one line, so the caret column does not match the file — the `line 2` number does. Stop there: no picture, no visual verdict, nothing to guess about.

## When the render succeeds

Read the PNG and check it:

- a label overlapping another one, or truncated;
- an arrow pointing the opposite way to what its label's verb says;
- a node with no edges, left over from an earlier draft;
- a subgraph that swallowed a node that belongs outside it;
- the picture far wider than tall — it will be shrunk to illegibility in a merge-request column;
- more than one idea in the picture;
- whether a reader with no context could say what the diagram claims. That is the real test.

## Report

Three parts, in this order, and then end your turn:

1. **Render** — `OK, <width>x<height> px` or `failed`, with the verbatim error.
2. **What the picture shows** — the nodes, the groupings, the arrows with their labels, and the order a reader's eye takes them in. Describe what is there, not what the source says should be there.
3. **Verdict** — `clear`, or `confusing because …` with concrete suggestions: which label to shorten, which arrow to reverse, where to split into two diagrams.

On a follow-up message asking you to check again, re-render and report **what changed** against the previous picture — you still have it.
