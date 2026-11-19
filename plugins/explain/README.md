# explain

Explains a change to a software service as one HTML page, for a tech lead who wants to judge the parts that are hard to change without reading the whole merge request, ticket or design document.

One skill, `explain:changes-high-level`. Give it a merge request, a pull request, a ticket, a document, a chat thread, a URL, a file or pasted text. The page has the same layout every time: a short framing of what the change is and why; a change map with the services involved and one flow per entry point, whose boxes link to the diffs; every database, messaging, HTTP and other cross-system interface it touches, as a diff (tables as `CREATE TABLE` statements, payloads as JSON-like structures), each with what it costs to change again later and how it rolls out; the modules and packages it touches; and the code internals, last and short. Contract files that nothing covered are listed at the top, so a gap is visible. A change that is not implemented yet is compared with the current code and marked as proposed.

It explains and never reviews: no findings, no verdicts, nothing posted anywhere. For a review, use `/code-review:full`.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install explain@fprochazka-claude-code-plugins --scope user
```

This installs the `prose` and `diagrams` plugins it depends on. The tools it runs are a manual install:

- **`uv`**, which runs the page build script with its one dependency, `jsonschema`, declared inline. Without uv, `python3` works when `jsonschema` is installed for it.
- **`mmdc`** from `@mermaid-js/mermaid-cli`, which renders the diagrams to SVG inside the page; see the [diagrams plugin's install notes](../diagrams/skills/mermaid/references/install.md). Without it, the page draws the diagrams from a pinned Mermaid import on jsDelivr and needs the network to show them.
- **`glab` or `gh`** to read GitLab merge requests or GitHub pull requests. For GitLab, [glab-cli-extras](https://github.com/fprochazka/glab-cli-extras) is optional and preferred: it reads an MR with all its threads in one call.
- **`noisy-tools-in-subagent`**, optional: when installed, the diagram rendering runs in its `noisy-runner` subagent.

## Usage

```
/explain:changes-high-level https://gitlab.example.com/acme/billing/-/merge_requests/128
/explain:changes-high-level 412                       # a pull request or MR number in the current repository
/explain:changes-high-level ACME-1234                 # a ticket
/explain:changes-high-level docs/design/reminders.md focus on the retry handling
/explain:changes-high-level                           # the current branch
```

Claude also loads the skill when you ask what a change does, or ask it to explain a dense ticket or document. A typical run takes about 10 minutes, a large one about 15. The page works offline, in light and dark mode. It is written to the session's scratchpad, which a reboot or a cleanup can clear, so publish any page you want to keep.

## Opening and publishing the page

The page opens in your browser at the end of every run. If your CLAUDE.md or AGENTS.md names a command that opens links or files, the run uses it, for example:

```markdown
Open links and files with: BROWSER_PROFILE=work my-link-opener open <url or file:///absolute/path>
```

To also publish the page, tell Claude where HTML pages go in `~/.claude/CLAUDE.md` or the project's CLAUDE.md or AGENTS.md. Any heading and wording works, as long as it names a tool, a skill or a shell command, or says to keep pages local, for example:

```markdown
## HTML artifacts
Publish HTML pages with: <a tool, a skill, or a shell command; or "local only">
```

Without one, the first run asks where to publish and offers to save your answer.

## License

MIT
