#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.0"]
# ///
"""Build the explain page from JSON data and the fixed HTML template.

Run it with `uv run --script build.py ...`; uv installs jsonschema from the header above into a cached
environment. Without uv, `python3 build.py ...` works when jsonschema is importable.

    build.py merge subdomain-*.json --out contracts.json [--checklist contract-files.json] [--code-tree <dir> [--base <sha>]]
        Validate the deep dives' fragments against contracts.schema.json and merge them. Interface
        objects are combined by key, packages by name. Two fragments that describe one object with
        different facts are printed as conflicts. With --code-tree, every `path:line` ref is checked
        against the head tree (and `base:path:line` against --base), and each bad one is printed.

    build.py diagrams contracts.json --out-dir <dir>
        Write the generated Mermaid sources: services.mmd (more than one service), one flow-<slug>.mmd per
        entry point, and database-er.mmd (the tables and their foreign keys). Prints the ids written, for
        the render step to draw with mmdc. Every box links to the card that explains its diff.

    build.py page page.json --contracts contracts.json --diagrams-dir <dir> --out <file.html> [--code-tree <dir> [--base <sha>]]
        Validate page.json against page.schema.json, render the page, inline the SVG diagrams that
        the render subagent produced with mmdc, and check the result. Never runs mmdc itself.

Every violation is printed with its JSON path. Exit codes: 0 built (warnings may be printed),
1 invalid input or a failed check, 2 usage error.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "template.html"

# The CDN fallback for diagrams that have no rendered .svg. Same major as the local mmdc:
# Mermaid 12 changed the default layout and look, so 11 and 12 draw one source differently.
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@12.3.0/dist/mermaid.esm.min.mjs"

# Width of the page's content column in CSS pixels; template.html uses the same number.
CONTENT_WIDTH = 1240
# The diagram panel's padding and border take this much of the column.
DIAGRAM_WIDTH = CONTENT_WIDTH - 30
MAX_PAGE_BYTES = 5 * 1024 * 1024
# Soft prose limits per section, in words. The page's length should follow the number of contract
# changes, not the size of the diff, so everything outside the interfaces is kept short.
SOFT_SECTION_WORDS = {"framing": 450, "requirements": 250, "interfaces": 900, "modules": 300, "concepts": 250, "internals": 250, "discussion": 250}
MAX_FLOW_STEPS = 5

GLYPH = {"added": "+", "removed": "−", "changed": "~", "unchanged": " ", "accessed": "·", "semantics changed": "!"}
CONTRACT_KINDS = ["tables", "routes", "messages", "endpoints", "boundaries"]
SINGULAR = {"tables": "table", "routes": "route", "messages": "message", "endpoints": "endpoint", "boundaries": "boundary"}
# Top-level fragment lists that feed the overview diagrams and the far-side note.
MAP_KINDS = ["services", "service_links", "entry_points", "far_side_reads"]
# Ids of the diagrams build.py generates; page.json lists only the hand-written ones.
GENERATED_SERVICES = "services"
GENERATED_ER = "database-er"

# ---------------------------------------------------------------------------------------------
# Validation. The JSON Schemas next to this script are the source of truth for the structure;
# references/deep-dive.md and references/render.md explain what the fields mean.
# ---------------------------------------------------------------------------------------------

PAGE_SCHEMA = HERE / "page.schema.json"
CONTRACTS_SCHEMA = HERE / "contracts.schema.json"


def load_validator(schema_path: Path, definition: str | None = None):
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("error build.py needs the jsonschema package: run it with `uv run --script build.py ...`, or install jsonschema for python3")
        sys.exit(1)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if definition:
        schema = {**schema, "$ref": f"#/$defs/{definition}"}
    return Draft202012Validator(schema)


def json_path(root: str, parts) -> str:
    out = root
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out


def validate(value, schema_path: Path, root: str, definition: str | None = None) -> list[str]:
    """Every schema violation in value, each prefixed with its JSON path, in document order."""
    validator = load_validator(schema_path, definition)
    errors = sorted(validator.iter_errors(value), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{json_path(root, e.absolute_path)}: {e.message}" for e in errors]


# ---------------------------------------------------------------------------------------------
# refs
# ---------------------------------------------------------------------------------------------

REF_RE = re.compile(r"^(base:)?([^\s:]+\.[A-Za-z0-9]+|[^\s:]+/[^\s:]+):(\d+)(?:-(\d+))?$")


def git_env() -> dict:
    """The environment without the variables git sets for hooks, so `git -C <tree>` reads that tree."""
    import os

    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def check_refs(value, root: str, tree: Path, base: str | None) -> list[str]:
    """Every `path:line` ref in value that does not exist: a missing file, or a line past its end.

    Head refs are checked in the code tree, `base:` refs with `git show <base>:<path>` when base is known."""
    problems: list[str] = []
    base_cache: dict[str, int | None] = {}

    def line_count(path: str, at_base: bool) -> int | None:
        if not at_base:
            f = tree / path
            return len(f.read_text(encoding="utf-8", errors="replace").splitlines()) if f.is_file() else None
        if path not in base_cache:
            r = subprocess.run(["git", "-C", str(tree), "show", f"{base}:{path}"], capture_output=True, text=True, env=git_env())
            base_cache[path] = len(r.stdout.splitlines()) if r.returncode == 0 else None
        return base_cache[path]

    def walk(node, parts):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "ref" and isinstance(v, str):
                    m = REF_RE.match(v)
                    if not m or (m.group(1) and not base):
                        continue
                    at_base, path, line, end = bool(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4) or m.group(3))
                    count = line_count(path, at_base)
                    where = json_path(root, [*parts, k])
                    if count is None:
                        problems.append(f"{where}: {v}: the file does not exist at the {'base' if at_base else 'head'}")
                    elif end > count:
                        problems.append(f"{where}: {v}: the file has {count} lines")
                else:
                    walk(v, [*parts, k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, [*parts, i])

    walk(value, [])
    return problems


# ---------------------------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------------------------


def object_key(kind: str, item: dict) -> str:
    if kind == "routes":
        return f"{item['exchange']['name']} | {item['key']} | {item['queue']['name']}"
    if kind == "endpoints":
        return f"{item['direction']} {item['method'].upper()} {item['path']}"
    if kind == "boundaries":
        return f"{item['kind']} {item['name']}"
    if kind == "service_links":
        return f"{item['from']} -> {item['to']} | {item['via']}"
    if kind == "entry_points":
        return f"{item['kind']} {item['name']}"
    if kind == "far_side_reads":
        return f"{item['service']} {item['clone']}"
    return item["name"]


# Keys that legitimately differ when two areas describe one object.
MERGE_IGNORED = {"area", "areas", "ref", "accesses", "note", "lead"}


def facts(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in MERGE_IGNORED}


def differing_keys(a: dict, b: dict) -> list[str]:
    fa, fb = facts(a), facts(b)
    return sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))


def merge(fragments: list[tuple[str, dict]], contract_files: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Combine fragments into one contracts document. Returns (merged, error messages).

    contract_files is the surface scan's list of contract files. A file that no fragment's checklist
    covers, or that a fragment left unknown, becomes a checklist gap, which the page shows at the top of
    its interfaces section: a missing contract must be visible, never silently absent."""
    errors: list[str] = []
    for name, fragment in fragments:
        errors += validate(fragment, CONTRACTS_SCHEMA, name, "fragment")
    if contract_files is not None:
        errors += validate(contract_files, CONTRACTS_SCHEMA, "contract-files", "contract_files")
    if errors:
        return {}, errors

    merged: dict = {"areas": [f["area"] for _, f in fragments]}
    conflicts: list[dict] = []
    for kind in [*CONTRACT_KINDS, "packages", *MAP_KINDS]:
        by_key: dict[str, dict] = {}
        for _, fragment in fragments:
            if kind in CONTRACT_KINDS:
                items = fragment.get("contracts", {}).get(kind, [])
            else:
                items = fragment.get(kind, [])
            tracks_area = kind not in MAP_KINDS
            for item in items:
                item = json.loads(json.dumps(item))
                key = item["name"] if kind == "packages" else object_key(kind, item)
                if key not in by_key:
                    if tracks_area:
                        item.setdefault("areas", [item["area"]])
                    by_key[key] = item
                    continue
                kept = by_key[key]
                if tracks_area and item["area"] not in kept["areas"]:
                    kept["areas"].append(item["area"])
                differs = differing_keys(kept, item)
                if differs:
                    conflicts.append({"kind": kind, "key": key, "areas": [kept.get("area", "?"), item.get("area", fragment["area"])], "differs": differs})
                elif "accesses" in item:
                    seen = {json.dumps(a, sort_keys=True) for a in kept.get("accesses", [])}
                    for access in item["accesses"]:
                        if json.dumps(access, sort_keys=True) not in seen:
                            kept.setdefault("accesses", []).append(access)
        if by_key:
            merged[kind] = list(by_key.values())
    if conflicts:
        merged["conflicts"] = conflicts
    gaps = []
    results: dict[str, dict] = {}
    for _, fragment in fragments:
        for entry in fragment["checklist"]:
            if results.get(entry["path"], {}).get("result") in (None, "unknown"):
                results[entry["path"]] = {**entry, "area": fragment["area"]}
    for cf in contract_files or []:
        entry = results.get(cf["path"])
        if entry is None:
            gaps.append({"path": cf["path"], "area": cf["area"], "kind": cf["kind"], "reason": "no deep dive covered this file"})
    for path, entry in results.items():
        if entry["result"] == "unknown":
            gaps.append({"path": path, "area": entry["area"], "reason": entry["note"]})
    if gaps:
        merged["checklist_gaps"] = gaps
    return merged, []


def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_merge(args: argparse.Namespace) -> int:
    fragments = []
    for path in args.fragments:
        try:
            fragments.append((Path(path).name, read_json(path)))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error {path}: {exc}")
            return 1
    contract_files = None
    if args.checklist:
        try:
            contract_files = read_json(args.checklist)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error {args.checklist}: {exc}")
            return 1
    merged, errors = merge(fragments, contract_files)
    for message in errors:
        print(f"error {message}")
    if errors:
        return 1
    Path(args.out).write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for conflict in merged.get("conflicts", []):
        print(f"conflict {conflict['kind']} \"{conflict['key']}\": {' and '.join(conflict['areas'])} differ in {', '.join(conflict['differs'])}; the first is kept")
    for gap in merged.get("checklist_gaps", []):
        print(f"gap {gap['path']}: {gap['reason']}")
    if args.code_tree:
        for name, fragment in fragments:
            for problem in check_refs(fragment, name, Path(args.code_tree), args.base):
                print(f"ref {problem}")
    counts = ", ".join(f"{len(merged[k])} {k}" for k in [*CONTRACT_KINDS, "packages", "entry_points"] if k in merged)
    print(f"merged {len(fragments)} fragments into {args.out}: {counts or 'no objects'}")
    return 0


# ---------------------------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------------------------

E = html.escape
LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")


def md(text: str) -> str:
    """The markdown subset: `code`, **bold** and [text](http(s) url). Everything else is escaped text."""
    out = []
    for i, part in enumerate(text.split("`")):
        if i % 2:
            out.append(f"<code>{E(part)}</code>")
        else:
            part = E(part, quote=False)
            part = BOLD_RE.sub(r"<strong>\1</strong>", part)
            part = LINK_RE.sub(lambda m: f'<a href="{E(html.unescape(m.group(2)))}">{m.group(1)}</a>', part)
            out.append(part)
    return "".join(out)


def plain(text: str) -> str:
    """The markdown subset reduced to plain text, for code comments."""
    text = LINK_RE.sub(r"\1", text)
    return BOLD_RE.sub(r"\1", text).replace("`", "")


def words(value) -> int:
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, list):
        return sum(words(v) for v in value)
    if isinstance(value, dict):
        return sum(words(v) for k, v in value.items() if k not in ("code", "ref", "url"))
    return 0


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def status_slug(status: str) -> str:
    return slug(status)


# ---------------------------------------------------------------------------------------------
# anchors: one id per interface object, shared by the cards and the generated diagrams
# ---------------------------------------------------------------------------------------------


def contract_entries(contracts: dict) -> list[tuple[str, str, dict]]:
    """(kind, key, item) for every interface object, in page order."""
    out = []
    for plural in CONTRACT_KINDS:
        for item in contracts.get(plural, []):
            out.append((SINGULAR[plural], object_key(plural, item), item))
    return out


def anchor_map(contracts: dict) -> dict[tuple[str, str], str]:
    anchors: dict[tuple[str, str], str] = {}
    used: set[str] = set()
    for kind, key, _ in contract_entries(contracts):
        base = f"{kind}-{slug(key)}"
        anchor, n = base, 2
        while anchor in used:
            anchor, n = f"{base}-{n}", n + 1
        anchors[(kind, key)] = anchor
        used.add(anchor)
    return anchors


# ---------------------------------------------------------------------------------------------
# generated Mermaid: services, change flows, and the tables' foreign keys
# ---------------------------------------------------------------------------------------------

# Diagrams are drawn once in Mermaid's light theme and shown on a light panel, so these colors are fixed.
MERMAID_CLASSES = (
    "  classDef added fill:#dafbe1,stroke:#1a7f37,color:#0d3d1a\n"
    "  classDef changed fill:#fff8c5,stroke:#9a6700,color:#3d2a00\n"
    "  classDef semantics fill:#fff8c5,stroke:#9a6700,stroke-dasharray:4 3,color:#3d2a00\n"
    "  classDef removed fill:#ffebe9,stroke:#cf222e,color:#5c0a12\n"
    "  classDef accessed fill:#ddf4ff,stroke:#0969da,color:#0a3069\n"
    "  classDef context fill:#f6f8fa,stroke:#8c959f,color:#1f2328\n"
)
MERMAID_CLASS = {"added": "added", "changed": "changed", "semantics changed": "semantics", "removed": "removed", "accessed": "accessed", "unchanged": "context"}


def mlabel(text: str) -> str:
    """A Mermaid label, quoted, with the characters Mermaid would parse replaced by entity codes."""
    escaped = text.replace("&", "#amp;").replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;")
    return '"' + escaped.replace("#lt;br#gt;", "<br>") + '"'


class MermaidGraph:
    def __init__(self, direction: str = "LR"):
        self.lines = [f"flowchart {direction}"]
        self.nodes: dict[str, str] = {}
        self.classes: list[str] = []
        self.clicks: list[str] = []

    def node(self, key: str, label: str, status: str, shape: str = "box", href: str | None = None) -> str:
        if key in self.nodes:
            return self.nodes[key]
        nid = f"n{len(self.nodes) + 1}"
        self.nodes[key] = nid
        glyph = GLYPH.get(status, " ").strip()
        # A no-break space keeps the status glyph on the first line of a wrapped label.
        text = mlabel(f"{glyph}\u00a0{label}" if glyph else label)
        open_, close = {"box": ("[", "]"), "db": ("[(", ")]"), "msg": (">", "]"), "entry": ("([", "])"), "queue": ("{{", "}}"), "config": ("[/", "/]")}[shape]
        self.lines.append(f"  {nid}{open_}{text}{close}")
        self.classes.append(f"  class {nid} {MERMAID_CLASS.get(status, 'context')}")
        if href:
            self.clicks.append(f'  click {nid} href "#{href}"')
        return nid

    def edge(self, a: str, b: str, label: str, dashed: bool = False) -> None:
        arrow = "-.->" if dashed else "-->"
        self.lines.append(f"  {a} {arrow}|{mlabel(label)}| {b}")

    def source(self) -> str:
        return "\n".join(self.lines + self.classes + self.clicks) + "\n" + MERMAID_CLASSES


TARGET_SHAPE = {"table": "db", "message": "msg", "route": "queue", "endpoint": "box", "boundary": "config"}


def target_label(kind: str, name: str, item: dict | None) -> str:
    if kind == "endpoint":
        parts = name.split(" ", 1)
        if parts[0] == "client" and item and item.get("target", {}).get("service"):
            return f"{item['target']['service']}<br>{parts[1]}"
        return parts[1] if len(parts) > 1 else name
    if kind == "route" and item:
        return f"{item['exchange']['name']}<br>{item['key']} → {item['queue']['name']}"
    if kind == "boundary":
        return name.split(" ", 1)[1] if " " in name else name
    return name


def generated_diagrams(contracts: dict) -> list[tuple[str, str, str]]:
    """(id, title, mermaid source) for every diagram build.py draws from the data."""
    anchors = anchor_map(contracts)
    index = {(k, key): item for k, key, item in contract_entries(contracts)}
    out: list[tuple[str, str, str]] = []

    services = contracts.get("services", [])
    links = contracts.get("service_links", [])
    names = [s["name"] for s in services] + [n for link in links for n in (link["from"], link["to"])]
    if len(set(names)) > 1:
        g = MermaidGraph("LR")
        status = {s["name"]: s["status"] for s in services}
        href: dict[str, str] = {}
        for link in links:
            t = link.get("target")
            if t and (t["kind"], t["name"]) in anchors:
                for n in (link["from"], link["to"]):
                    href.setdefault(n, anchors[(t["kind"], t["name"])])
        for n in dict.fromkeys(names):
            g.node(n, n, status.get(n, "unchanged"), "box", href.get(n, "interfaces"))
        for link in links:
            label = (GLYPH.get(link["status"], "").strip() + " " + link["via"]).strip()
            g.edge(g.nodes[link["from"]], g.nodes[link["to"]], label, dashed=link["status"] == "removed")
        out.append((GENERATED_SERVICES, "Services the change touches", g.source()))

    for ep in contracts.get("entry_points", []):
        g = MermaidGraph("LR")
        own = ep.get("target")
        start = g.node("entry", f"{ep['kind']}<br>{ep['name']}", ep["status"], "entry", anchors.get((own["kind"], own["name"])) if own else None)
        for action in ep["actions"]:
            t = action["target"]
            item = index.get((t["kind"], t["name"]))
            node_status = item["status"] if item else "unchanged"
            n = g.node(f"{t['kind']} {t['name']}", target_label(t["kind"], t["name"], item), node_status, TARGET_SHAPE[t["kind"]], anchors.get((t["kind"], t["name"])))
            glyph = GLYPH.get(action["status"], "").strip()
            label = (f"{glyph} " if glyph and action["status"] != "unchanged" else "") + action["verb"]
            if action["verb"] == "consumes":
                g.edge(n, start, label, dashed=action["status"] == "removed")
            else:
                g.edge(start, n, label, dashed=action["status"] == "removed")
        out.append((f"flow-{slug(ep['kind'] + ' ' + ep['name'])}", f"{ep['kind'].capitalize()} {ep['name']}", g.source()))

    tables = contracts.get("tables", [])
    edges = []
    for t in tables:
        for c in t.get("columns", []):
            if c.get("references"):
                edges.append((t["name"], c["references"].rsplit(".", 1)[0], c["name"], c.get("foreign_key", True), c["status"]))
    if edges or len(tables) > 1:
        g = MermaidGraph("LR")
        for t in tables:
            g.node(t["name"], t["name"], t["status"], "db", anchors.get(("table", t["name"])))
        for src, dst, col, fk, st in edges:
            if dst not in g.nodes:
                g.node(dst, dst, "unchanged", "db")
            label = col if fk else f"{col}, no foreign key"
            g.edge(g.nodes[src], g.nodes[dst], (GLYPH[st].strip() + " " + label).strip() if st in ("added", "removed") else label, dashed=not fk or st == "removed")
        out.append((GENERATED_ER, "Tables and their foreign keys", g.source()))
    return out


def cmd_diagrams(args: argparse.Namespace) -> int:
    try:
        contracts = read_json(args.contracts)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error {exc}")
        return 1
    errors = validate(contracts, CONTRACTS_SCHEMA, "contracts", "merged")
    for e in errors:
        print(f"error {e}")
    if errors:
        return 1
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ids = []
    for diagram_id, _, source in generated_diagrams(contracts):
        (out / f"{diagram_id}.mmd").write_text(source, encoding="utf-8")
        ids.append(diagram_id)
    print("generated " + (" ".join(ids) if ids else "no diagrams"))
    return 0


# ---------------------------------------------------------------------------------------------
# code diffs: CREATE TABLE statements and JSON-like payloads, with aligned trailing comments
# ---------------------------------------------------------------------------------------------

SIGN = {"added": "+", "removed": "-", "unchanged": " ", "accessed": " ", "semantics changed": "!"}
# Lines past the comment column get their comment on the next line, in the same column.
MAX_COMMENT_COLUMN = 64
LINE_WIDTH = 150
CONTEXT_KEEP = 2
CONTEXT_FOLD_MIN = 4
SQL_KEYWORDS = re.compile(r"\b(CREATE|TABLE|NOT|NULL|DEFAULT|PRIMARY|KEY|UNIQUE|REFERENCES|FOREIGN|CONSTRAINT|CHECK|INDEX|ON)\b")
JSON_KEY = re.compile(r"^(\s*)(&quot;[^&]*?&quot;)(:)")


class Line:
    __slots__ = ("sign", "code", "comment")

    def __init__(self, sign: str, code: str, comment: str = ""):
        self.sign, self.code, self.comment = sign, code, comment


def highlight(code: str, lang: str) -> str:
    escaped = E(code)
    if lang == "sql":
        return SQL_KEYWORDS.sub(r'<span class="kw">\1</span>', escaped)
    return JSON_KEY.sub(r'\1<span class="key">\2</span>\3', escaped)


def code_diff(lines: list[Line], lang: str) -> str:
    """A unified diff as HTML: one row per line, comments aligned in one column, long context runs folded."""
    marker = "--" if lang == "sql" else "//"
    commented = [len(x.code) for x in lines if x.comment]
    column = min(max(commented, default=0), MAX_COMMENT_COLUMN) + 2
    width = max(36, LINE_WIDTH - column)

    def rows(line: Line) -> list[str]:
        cls = {"+": "d-add", "-": "d-del", "!": "d-sem", " ": "d-ctx"}[line.sign]
        sign = f'<span class="sg">{E(line.sign)}</span>'
        if not line.comment:
            return [f'<div class="dl {cls}">{sign}<span class="c">{highlight(line.code, lang)}</span></div>']
        wrapped = textwrap.wrap(line.comment, width) or [""]
        out = []
        if len(line.code) + 2 > column:
            out.append(f'<div class="dl {cls}">{sign}<span class="c">{highlight(line.code, lang)}</span></div>')
            first_code = ""
        else:
            first_code = line.code
        for i, text in enumerate(wrapped):
            code = first_code if i == 0 else ""
            pad = " " * (column - len(code))
            out.append(f'<div class="dl {cls}">{sign}<span class="c">{highlight(code, lang)}</span>{pad}<span class="cm">{E(marker)} {E(text)}</span></div>')
        return out

    changed = [i for i, x in enumerate(lines) if x.sign != " "]
    keep = set()
    for i in changed:
        keep.update(range(i - CONTEXT_KEEP, i + CONTEXT_KEEP + 1))
    keep.update({0, len(lines) - 1})
    html_rows: list[str] = []
    run: list[Line] = []

    def flush():
        if not run:
            return
        if len(run) >= CONTEXT_FOLD_MIN:
            inner = "".join(r for x in run for r in rows(x))
            html_rows.append(f'<details class="dfold"><summary>{len(run)} unchanged lines</summary>{inner}</details>')
        else:
            html_rows.extend(r for x in run for r in rows(x))
        run.clear()

    for i, line in enumerate(lines):
        if changed and i not in keep:
            run.append(line)
            continue
        flush()
        html_rows.extend(rows(line))
    flush()
    return f'<div class="diff lang-{lang}" role="figure">{"".join(html_rows)}</div>'


def references_sql(ref: str) -> str:
    table, _, column = ref.rpartition(".")
    return f"{table} ({column})" if table else ref


def column_sql(c: dict, old: bool = False) -> str:
    was = c.get("was", {}) if old else {}
    name = was.get("name", c["name"])
    type_ = was.get("type", c.get("type", "?"))
    nullable = was.get("nullable", c.get("nullable"))
    default = was.get("default", c.get("default"))
    out = f"  {name} {type_}"
    if nullable is False:
        out += " NOT NULL"
    if default is not None:
        out += f" DEFAULT {default}"
    key = (c.get("key") or "").lower()
    if key == "primary key":
        out += " PRIMARY KEY"
    elif key == "unique":
        out += " UNIQUE"
    return out


def column_comment(c: dict) -> str:
    parts = []
    key = (c.get("key") or "").lower()
    if key and key not in ("primary key", "unique"):
        parts.append(c["key"])
    if c.get("references") and c.get("foreign_key") is False:
        parts.append(f"refers to {c['references']}, no foreign key")
    if c.get("note"):
        parts.append(plain(c["note"]))
    return "; ".join(parts)


def table_sql_lines(t: dict) -> list[Line]:
    """The table's CREATE TABLE statement as a diff between before and after the change."""
    dialect = t.get("dialect", "other")
    whole = {"added": "+", "removed": "-"}.get(t["status"])
    # (sign, sql, comment, inner): inner lines sit inside the parentheses and need commas between them.
    entries: list[tuple[str, str, str, bool]] = []

    def element(item: dict, new: str, old: str | None, comment: str) -> None:
        st = item.get("status", "unchanged")
        if st == "changed" and old is not None and old != new:
            entries.append(("-", old, "", True))
            entries.append(("+", new, comment, True))
        elif st == "changed":
            entries.append(("+", new, comment, True))
        elif st == "semantics changed":
            entries.append(("!", new, ("meaning changed: " + comment) if comment else "meaning changed", True))
        else:
            entries.append((SIGN.get(st, " "), new, comment, True))

    for c in t.get("columns", []):
        element(c, column_sql(c), column_sql(c, old=True) if c.get("was") else None, column_comment(c))
    if t.get("unchanged_columns"):
        entries.append((" ", "  …", f"{t['unchanged_columns']} more unchanged columns, not listed", False))
    for c in t.get("columns", []):
        if c.get("references") and c.get("foreign_key", True):
            st = c["status"] if c["status"] in ("added", "removed") else "unchanged"
            entries.append((SIGN[st], f"  FOREIGN KEY ({c['name']}) REFERENCES {references_sql(c['references'])}", "", True))
    inline_indexes = dialect in ("mysql", "mariadb")
    if inline_indexes:
        for ix in t.get("indexes", []):
            kw = "UNIQUE KEY" if ix.get("unique") else "KEY"
            new = f"  {kw} {ix['name']} {ix.get('definition', '')}".rstrip()
            old = f"  {kw} {ix['name']} {ix['was']['definition']}" if ix.get("was", {}).get("definition") else None
            element(ix, new, old, plain(ix.get("note", "")))
    for ct in t.get("constraints", []):
        element(ct, f"  {ct['text']}", None, plain(ct.get("note", "")))

    # Commas: an inner line gets one when a later inner line exists on its own side of the diff.
    def side(sign: str, after: bool) -> bool:
        return sign in (" ", "!", "+") if after else sign in (" ", "!", "-")

    lines = [Line(whole or " ", f"CREATE TABLE {t['name']} (")]
    for i, (sign, sql, comment, is_inner) in enumerate(entries):
        if is_inner:
            after = sign != "-"
            later = any(e[3] and side(e[0], after) for e in entries[i + 1:])
            sql += "," if later else ""
        lines.append(Line(whole or sign, sql, comment))
    lines.append(Line(whole or " ", ");"))
    if not inline_indexes:
        for ix in t.get("indexes", []):
            kw = "CREATE UNIQUE INDEX" if ix.get("unique") else "CREATE INDEX"
            new = f"{kw} {ix['name']} ON {t['name']} {ix.get('definition', '')}".rstrip() + ";"
            st = ix.get("status", "unchanged")
            if st == "changed" and ix.get("was", {}).get("definition"):
                lines.append(Line(whole or "-", f"{kw} {ix['name']} ON {t['name']} {ix['was']['definition']};"))
                lines.append(Line(whole or "+", new, plain(ix.get("note", ""))))
            else:
                lines.append(Line(whole or SIGN.get(st, "+"), new, plain(ix.get("note", ""))))
    return lines


def payload_lines(fields: list[dict], unchanged_count: int = 0, whole: str | None = None) -> list[Line]:
    """A payload as a JSON-like structure: types as values, required/optional and notes in `//` comments."""

    def comment(f: dict, old: bool) -> str:
        was = f.get("was", {}) if old else {}
        req = was.get("required", f.get("required"))
        parts = [] if req is None else ["required" if req else "optional"]
        if f.get("note") and not old:
            parts.append(plain(f["note"]))
        if f.get("status") == "semantics changed" and not old:
            parts.insert(0, "meaning changed")
        return "; ".join(parts)

    def walk(items: list[dict], depth: int, unchanged: int, forced: str | None) -> list[Line]:
        out: list[Line] = []
        pad = "  " * depth
        for f in items:
            st = f.get("status", "unchanged")
            sign = forced or SIGN.get(st, " ")
            name = f["name"]
            is_array = name.endswith("[]")
            name = name[:-2] if is_array else name
            children = f.get("fields") or f.get("unchanged_fields")
            if children:
                inner_forced = forced or ({"added": "+", "removed": "-"}.get(st))
                open_sign = sign if sign in "+-!" else " "
                opener = f'{pad}"{name}": ' + ("[{" if is_array else "{")
                out.append(Line(open_sign, opener, comment(f, False)))
                out += walk(f.get("fields", []), depth + 1, f.get("unchanged_fields", 0), inner_forced)
                out.append(Line(open_sign if open_sign in "+-" else " ", pad + ("}]" if is_array else "}")))
                continue
            type_ = f.get("type", "?")
            if st == "changed" and not forced and f.get("was"):
                old_type = f["was"].get("type", type_)
                out.append(Line("-", f'{pad}"{name}": {"[" + old_type + "]" if is_array else old_type}', comment(f, True)))
                out.append(Line("+", f'{pad}"{name}": {"[" + type_ + "]" if is_array else type_}', comment(f, False)))
            else:
                out.append(Line(sign if sign != " " or st != "changed" else "+", f'{pad}"{name}": {"[" + type_ + "]" if is_array else type_}', comment(f, False)))
        if unchanged:
            out.append(Line(forced or " ", f"{pad}…", f"{unchanged} more unchanged field{'s' if unchanged > 1 else ''}"))
        return out

    return [Line(whole or " ", "{"), *walk(fields, 1, unchanged_count, whole), Line(whole or " ", "}")]


# ---------------------------------------------------------------------------------------------
# page
# ---------------------------------------------------------------------------------------------


class Page:
    """Renders one page.json plus contracts.json into HTML fragments."""

    def __init__(self, page: dict, contracts: dict, diagrams_dir: Path | None):
        self.page = page
        self.contracts = contracts
        self.diagrams_dir = diagrams_dir
        self.diagram_meta = {d["id"]: d for d in page.get("diagrams", [])}
        self.generated = {d[0]: d for d in generated_diagrams(contracts)}
        self.used_diagrams: list[str] = []
        self.svg_ids: set[str] = set()
        self.cdn_needed = False
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.anchors = anchor_map(contracts)

    # -- references --------------------------------------------------------------------------

    def ref(self, ref: str | None, label: str | None = None) -> str:
        """A path:line reference as a short link (file name and line) to the forge's blob view at the pinned
        SHA; the full path is in the tooltip."""
        if not ref:
            return ""
        diff = self.page.get("diff") or {}
        m = REF_RE.match(ref)
        if not m:
            return f'<span class="ref">{E(ref)}</span>'
        base, path, line, end = m.groups()
        lines = f"{line}" + (f"-{end}" if end else "")
        full = ("base " if base else "") + f"{path}:{lines}"
        text = label or (("base " if base else "") + f"{path.rsplit('/', 1)[-1]}:{lines}")
        sha = diff.get("base_sha") if base else diff.get("head_sha")
        repo = (diff.get("repo_url") or "").rstrip("/")
        if diff.get("forge") in ("gitlab", "github") and repo and sha:
            middle = "/-/blob/" if diff["forge"] == "gitlab" else "/blob/"
            anchor = f"#L{line}" + ((f"-{end}" if diff["forge"] == "gitlab" else f"-L{end}") if end else "")
            return f'<a class="ref" href="{E(repo + middle + sha + "/" + path + anchor)}" title="{E(full)}">{E(text)}</a>'
        return f'<span class="ref" title="{E(full)}">{E(text)}</span>'

    @staticmethod
    def status_class(item: dict, key: str = "status") -> str:
        cls = f"st-{status_slug(item.get(key, 'unchanged'))}"
        return cls + (" proposed" if item.get("proposed") else "")

    @staticmethod
    def glyph(item: dict) -> str:
        status = item.get("status", "unchanged")
        return f'<span class="glyph" aria-label="{status}">{E(GLYPH[status])}</span>'

    def badge(self, item: dict) -> str:
        text = item["status"] + (" · proposed" if item.get("proposed") else "")
        return f'<span class="badge {self.status_class(item)}">{E(text)}</span>'

    def chips(self, item: dict) -> str:
        out = [f'<span class="chip cost">{E(label)}</span>' for label in item.get("cost", {}).get("labels", [])]
        if item.get("rollout"):
            out.append(f'<span class="chip rollout r-{slug(item["rollout"]["label"])}">{E(item["rollout"]["label"])}</span>')
        return "".join(out)

    def why(self, item: dict) -> str:
        """The reasons behind the labels, one compact line each."""
        rows = []
        if item.get("cost", {}).get("text"):
            rows.append(("Changing it later", item["cost"]["text"]))
        r = item.get("rollout", {})
        if r.get("text"):
            rows.append(("Rollout", r["text"]))
        if r.get("rollback"):
            rows.append(("Rollback", r["rollback"]))
        return "".join(f'<p class="why"><span class="why-label">{E(k)}:</span> {md(v)}</p>' for k, v in rows)

    def meta(self, item: dict, extra: str = "") -> str:
        areas = item.get("areas") or [item.get("area", "")]
        parts = [extra, f'<span class="area">{E(", ".join(a for a in areas if a))}</span>', f'<span class="source">{E(item["source"])}</span>', self.ref(item.get("ref"))]
        return '<div class="meta">' + " · ".join(p for p in parts if p) + "</div>"

    @staticmethod
    def changed(new, old) -> str:
        return f'<span class="was">{E(str(old))}</span> → {E(str(new))}' if old is not None and old != new else E(str(new)) if new is not None else ""

    def card(self, kind: str, key: str, item: dict, title: str, body: str, meta_extra: str = "", lead_key: str = "lead") -> str:
        """Every interface card: name, status and labels on one line, then the one-sentence lead, then the diff,
        then the reasons and the origin in small print."""
        lead = item.get(lead_key)
        if not lead and item["status"] not in ("unchanged", "accessed"):
            self.warnings.append(f"{kind} \"{key}\" has no lead sentence")
        return (
            f'<article class="card {self.status_class(item)}" id="{self.anchors[(kind, key)]}">'
            f'<header><span class="obj-name">{title}</span>{self.badge(item)}<span class="chips">{self.chips(item)}</span></header>'
            + (f'<p class="lead">{md(lead)}</p>' if lead else "")
            + body + self.why(item) + self.meta(item, meta_extra)
            + "</article>"
        )

    # -- diagrams ----------------------------------------------------------------------------

    def diagram(self, diagram_id: str | None) -> str:
        if not diagram_id:
            return ""
        meta = self.diagram_meta.get(diagram_id)
        if meta is None:
            self.errors.append(f"diagram \"{diagram_id}\" is referenced but not listed in page.json diagrams")
            return ""
        return self.figure(diagram_id, meta["title"], meta.get("caption"), failed=meta.get("failed", False))

    def figure(self, diagram_id: str, title: str, caption: str | None, failed: bool = False, generated: str | None = None) -> str:
        if diagram_id in self.used_diagrams:
            self.warnings.append(f"diagram \"{diagram_id}\" is shown more than once")
        self.used_diagrams.append(diagram_id)
        cap = f'<figcaption><strong>{E(title)}</strong>' + (f" — {md(caption)}" if caption else "") + "</figcaption>"
        svg_path = self.diagrams_dir / f"{diagram_id}.svg" if self.diagrams_dir else None
        mmd_path = self.diagrams_dir / f"{diagram_id}.mmd" if self.diagrams_dir else None
        source = generated or (mmd_path.read_text(encoding="utf-8") if mmd_path and mmd_path.is_file() else None)
        if failed:
            if source is None:
                self.errors.append(f"diagram \"{diagram_id}\" is marked failed but has no {diagram_id}.mmd")
                return ""
            return f'<figure class="diagram"><details class="fold"><summary>Diagram source; it could not be drawn</summary><pre>{E(source)}</pre></details>{cap}</figure>'
        if svg_path and svg_path.is_file():
            svg = self.inline_svg(diagram_id, svg_path.read_text(encoding="utf-8"), source)
            if svg is None:
                return ""
            return f'<figure class="diagram"><div class="diagram-panel">{svg}</div>{cap}</figure>'
        if source is not None:
            self.cdn_needed = True
            if generated:
                self.warnings.append(f"diagram \"{diagram_id}\" has no {diagram_id}.svg; run `build.py diagrams` and render it with mmdc, or the page needs the network to draw it")
            return f'<figure class="diagram"><div class="diagram-panel"><pre class="mermaid-src" data-mermaid>{E(source)}</pre></div>{cap}</figure>'
        self.errors.append(f"diagram \"{diagram_id}\" has neither {diagram_id}.svg nor {diagram_id}.mmd in the diagrams directory")
        return ""

    def inline_svg(self, diagram_id: str, svg: str, source: str | None) -> str | None:
        start = svg.find("<svg")
        if start == -1:
            self.errors.append(f"diagram \"{diagram_id}\": {diagram_id}.svg holds no <svg> element")
            return None
        svg = svg[start:]
        if re.search(r"<script|\son[a-z]+\s*=|javascript:", svg, re.I):
            self.errors.append(f"diagram \"{diagram_id}\": the SVG contains script or an event handler; render it again with mmdc")
            return None
        root = svg[: svg.find(">") + 1]
        m = re.search(r'\sid="([^"]+)"', root)
        if m:
            svg_id = m.group(1)
            if svg_id in self.svg_ids:
                # Mermaid scopes each SVG's CSS by the root id, so two inline SVGs with one id restyle each other.
                new_id = f"explain-{slug(diagram_id)}"
                self.warnings.append(f"diagram \"{diagram_id}\": SVG id \"{svg_id}\" is already used, renamed to \"{new_id}\"; pass -I to mmdc")
                svg = svg.replace(svg_id, new_id)
                svg_id = new_id
            self.svg_ids.add(svg_id)
        vb = re.search(r'viewBox="[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+[\d.]+"', root)
        if vb and float(vb.group(1)) > DIAGRAM_WIDTH:
            if (source or "").lstrip().startswith("sequenceDiagram") or "sequence" in root:
                fix = "use fewer participants or shorter messages; a sequence diagram has no direction to change"
            else:
                fix = "change its direction (LR to TB) or split it"
            self.warnings.append(f"diagram \"{diagram_id}\" is {float(vb.group(1)):.0f}px wide, the diagram panel is {DIAGRAM_WIDTH}px; {fix}")
        return svg

    def generated_figure(self, diagram_id: str, caption: str | None = None) -> str:
        if diagram_id not in self.generated:
            return ""
        _, title, source = self.generated[diagram_id]
        return self.figure(diagram_id, title, caption, generated=source)

    # -- database ----------------------------------------------------------------------------

    def access_table(self, accesses: list[dict]) -> str:
        if not accesses:
            return ""
        rows = []
        for a in accesses:
            who = self.ref(a["ref"], a["by"]) if a.get("ref") else "<code>" + E(a["by"]) + "</code>"
            what = md(a["what"]) if a.get("what") else ""
            rows.append(f'<tr><td class="acc-kind">{E(a["kind"])}</td><td>{who}</td><td>{what}</td></tr>')
        rows = "".join(rows)
        return f'<table class="access"><thead><tr><th>access</th><th>who</th><th>what</th></tr></thead><tbody>{rows}</tbody></table>'

    def table_card(self, t: dict) -> str:
        body = ""
        if t.get("columns") or t.get("indexes") or t.get("constraints"):
            if "dialect" not in t:
                self.warnings.append(f"table \"{t['name']}\" has no dialect; the statement is printed in generic SQL")
            body += code_diff(table_sql_lines(t), "sql")
        for dc in t.get("data_changes", []):
            if dc.get("sql"):
                body += f'<div class="data-change"><div class="body-head">data migration {self.ref(dc.get("ref"))}</div>' + code_diff([Line(" ", x) for x in dc["sql"].rstrip().split("\n")], "sql") + (f'<p class="note">{md(dc["summary"])}</p>' if dc.get("summary") else "") + "</div>"
            else:
                body += f'<p class="data-change"><span class="why-label">Data migration:</span> {md(dc["summary"])} {self.ref(dc.get("ref"))}</p>'
        if t.get("operations"):
            body += '<div class="ops"><span class="ops-label">What the migration does:</span> ' + "".join(f'<span class="chip op">{E(o)}</span>' for o in t["operations"]) + "</div>"
        body += self.access_table(t.get("accesses", []))
        if t.get("note"):
            body += f'<p class="note">{md(t["note"])}</p>'
        dialect = f'<span class="dialect">{E(t["dialect"])}</span>' if t.get("dialect") else ""
        return self.card("table", t["name"], t, E(t["name"]), body, dialect)

    def database(self, tables: list[dict]) -> str:
        context = [t for t in tables if t["status"] == "unchanged"]
        cards = "".join(self.table_card(t) for t in tables if t["status"] != "unchanged")
        if context:
            items = "".join(f'<li id="{self.anchors[("table", t["name"])]}"><code>{E(t["name"])}</code>' + (f" — {md(t['note'])}" if t.get("note") else "") + f" {self.ref(t.get('ref'))}</li>" for t in context)
            cards += f'<div class="context-tables"><span class="why-label">Unchanged tables shown for context:</span><ul>{items}</ul></div>'
        er = self.generated_figure(GENERATED_ER, "Green is added, yellow changed, red dropped, grey unchanged context; a dashed edge has no foreign key. Every box links to its table.")
        if not er:
            return cards
        return (
            '<div class="tabs">'
            '<input type="radio" name="tabs-db" id="tab-db-sql" checked><label for="tab-db-sql">CREATE TABLE diff</label>'
            '<input type="radio" name="tabs-db" id="tab-db-er"><label for="tab-db-er">Relationships</label>'
            f'<div class="tab-panel" data-radio="tab-db-sql">{cards}</div>'
            f'<div class="tab-panel" data-radio="tab-db-er">{er}</div>'
            "</div>"
        )

    # -- payloads ----------------------------------------------------------------------------

    @staticmethod
    def has_change(f: dict) -> bool:
        return f["status"] != "unchanged" or any(Page.has_change(c) for c in f.get("fields", []))

    def body(self, label: str, b: dict, whole: str | None = None) -> str:
        head = f'<div class="body-head">{E(label)}' + (f' <code>{E(b["type"])}</code>' if b.get("type") else "") + "</div>"
        note = f'<p class="note">{md(b["note"])}</p>' if b.get("note") else ""
        diff = code_diff(payload_lines(b.get("fields", []), b.get("unchanged_fields", 0), whole), "json") if b.get("fields") or b.get("unchanged_fields") else ""
        return f'<div class="payload">{head}{note}{diff}</div>'

    def endpoint(self, ep: dict) -> str:
        key = object_key("endpoints", ep)
        where = "server" if ep["direction"] == "server" else "client → " + ep.get("target", {}).get("service", "unknown service")
        if ep.get("target", {}).get("config_key"):
            where += f" (<code>{E(ep['target']['config_key'])}</code>)"
        else:
            where = E(where)
        whole = {"added": "+", "removed": "-"}.get(ep["status"])
        parts = []
        if ep.get("same_change_on"):
            parts.append('<p class="also"><span class="why-label">Same change on:</span> ' + ", ".join(f"<code>{E(x)}</code>" for x in ep["same_change_on"]) + "</p>")
        if ep.get("changes"):
            parts.append('<ul class="changes">' + "".join(f"<li>{md(c)}</li>" for c in ep["changes"]) + "</ul>")
        if ep.get("request"):
            parts.append(self.body("request body", ep["request"], whole))
        for r in ep.get("responses", []):
            label = f"response {r['status']}" + (f" ({r['change']})" if r.get("change") else "")
            parts.append(self.body(label, r, whole or {"added": "+", "removed": "-"}.get(r.get("change", ""))))
        if ep.get("note"):
            parts.append(f'<p class="note">{md(ep["note"])}</p>')
        title = f'<span class="method">{E(ep["method"].upper())}</span> {E(ep["path"])}'
        return self.card("endpoint", key, ep, title, "".join(parts), f'<span class="direction">{where}</span>')

    def message(self, msg: dict) -> str:
        fmt = f' <span class="format">{E(msg["format"])}</span>' if msg.get("format") else ""
        whole = {"added": "+", "removed": "-"}.get(msg["status"])
        body = self.body("payload", msg, whole) if msg.get("fields") or msg.get("unchanged_fields") else ""
        if msg.get("note"):
            body += f'<p class="note">{md(msg["note"])}</p>'
        return self.card("message", msg["name"], msg, f"message {E(msg['name'])}{fmt}", body)

    # -- messaging lanes ---------------------------------------------------------------------

    def lane_cell(self, el: dict | None, role: str, extra: str = "") -> str:
        if not el:
            return f'<div class="cell empty" data-role="{role}">—</div>'
        type_ = f' <span class="xtype">({E(el["type"])})</span>' if el.get("type") else ""
        return f'<div class="cell {self.status_class(el)}" data-role="{role}">{self.glyph(el)}<span class="cell-name">{E(el["name"])}</span>{type_}{extra}</div>'

    def lanes(self, routes: list[dict]) -> str:
        head = '<div class="arrow"></div>'.join(f'<div class="lane-head">{h}</div>' for h in ["producer", "exchange", "binding key", "queue", "consumer"])
        rows = []
        for r in routes:
            key = object_key("routes", r)
            args = ""
            if r["queue"].get("arguments"):
                args = '<div class="args">' + "".join(
                    f'<div class="{self.status_class(a)}">{self.glyph(a)} {E(a["name"])} = {self.changed(a["value"], a.get("was", {}).get("value"))}</div>' for a in r["queue"]["arguments"]
                ) + "</div>"
            msg = ""
            if r.get("message"):
                target = self.anchors.get(("message", r["message"]))
                msg = f'<a href="#{target}">{E(r["message"])}</a>' if target else E(r["message"])
            lane = (
                f'<div class="lane {self.status_class(r)}">'
                f'{self.lane_cell(r.get("producer"), "producer")}<div class="arrow">→</div>'
                f'{self.lane_cell(r["exchange"], "exchange")}<div class="arrow">→</div>'
                f'{self.lane_cell({"name": r["key"], "status": "unchanged"}, "key")}<div class="arrow">→</div>'
                f'{self.lane_cell(r["queue"], "queue", args)}<div class="arrow">→</div>'
                f'{self.lane_cell(r.get("consumer"), "consumer")}'
                + ('<span class="dot" aria-hidden="true"></span>' if r["status"] == "added" else "")
                + "</div>"
            )
            body = f'<div class="scroll"><div class="lanes">{lane}</div></div>' + (f'<p class="note">{md(r["note"])}</p>' if r.get("note") else "")
            title = f"{E(r['exchange']['name'])} → {E(r['queue']['name'])}"
            rows.append(self.card("route", key, r, title, body, ("carries " + msg) if msg else ""))
        return f'<div class="scroll"><div class="lanes"><div class="lane lane-header">{head}</div></div></div>' + "".join(rows)

    def boundaries(self, items: list[dict]) -> str:
        rows = []
        for b in items:
            value = self.changed(b.get("value"), b.get("was", {}).get("value")) if "value" in b else ""
            body = (f'<div class="value"><code>{value}</code></div>' if value else "") + (f'<p class="note">Used by {E(b["used_by"])}</p>' if b.get("used_by") else "")
            body += f'<p class="note">{md(b["note"])}</p>' if b.get("note") else ""
            kind = "" if b["kind"] == "other" else f'<span class="kind">{E(b["kind"])}</span> '
            rows.append(self.card("boundary", object_key("boundaries", b), b, f"{kind}{E(b['name'])}", body))
        return "".join(rows)

    def gaps(self) -> str:
        """Contract files that no deep dive covered, or left unknown. Shown first, never hidden."""
        gaps = self.contracts.get("checklist_gaps", [])
        if not gaps:
            return ""
        self.warnings.append(f"{len(gaps)} contract file(s) are not fully covered; the page lists them at the top of the interfaces section")
        items = "".join(f'<li>{self.ref(g["path"] + ":1") if REF_RE.match(g["path"] + ":1") else E(g["path"])} — {E(g["reason"])}</li>' for g in gaps)
        return f'<div class="gaps"><strong>Not covered by this page:</strong> these contract files may hold interface changes the page does not show.<ul>{items}</ul></div>'

    def far_side(self) -> str:
        reads = self.contracts.get("far_side_reads", [])
        if not reads:
            return ""
        items = "".join(
            f'<li><strong>{E(r["service"])}</strong>: {md(r["what"])} — clone <code>{E(r["clone"])}</code> at <code>{E(r["commit"][:12])}</code></li>' for r in reads
        )
        return (
            '<div class="far-side"><strong>Read from other services\' local clones.</strong> '
            "These facts come from the clone as it was on disk, which may differ from what that service runs in production.<ul>" + items + "</ul></div>"
        )

    def summary_table(self) -> str:
        """One row per interface object: what it is, its status, and the two label sets."""
        rows = []
        for kind, key, item in contract_entries(self.contracts):
            if item["status"] in ("unchanged", "accessed"):
                continue
            if kind == "endpoint":
                label = key.split(" ", 1)[1]
            elif kind == "boundary":
                label = item["name"]
            else:
                label = key
            shown_kind = item["kind"] if kind == "boundary" and item["kind"] != "other" else kind
            cost = ", ".join(item.get("cost", {}).get("labels", [])) or "not stated"
            rollout = item.get("rollout", {}).get("label", "not stated")
            rows.append(
                f'<tr class="{self.status_class(item)}"><td>{E(shown_kind)}</td><td><a href="#{self.anchors[(kind, key)]}">{E(label)}</a></td>'
                f'<td>{self.badge(item)}</td><td>{E(cost)}</td><td><span class="chip rollout r-{slug(rollout)}">{E(rollout)}</span></td></tr>'
            )
            if "cost" not in item or "rollout" not in item:
                self.warnings.append(f"{kind} \"{key}\" has no {'cost' if 'cost' not in item else 'rollout'} labels")
        if not rows:
            return ""
        return (
            '<div class="scroll"><table class="summary"><thead><tr><th>kind</th><th>interface</th><th>change</th>'
            "<th>changing it later</th><th>rollout</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )

    def packages(self, areas: list[dict]) -> str:
        by_area: dict[str, list[dict]] = {}
        for p in self.contracts.get("packages", []):
            by_area.setdefault(p["area"], []).append(p)
        names = [a["name"] for a in areas] + [a for a in by_area if a not in {x["name"] for x in areas}]
        area_meta = {a["name"]: a for a in areas}
        blocks = []
        for name in names:
            meta = area_meta.get(name, {"name": name})
            dive = f'<span class="chip">{E(meta["deep_dive"])}</span>' if meta.get("deep_dive") else ""
            pk_rows = []
            for p in by_area.get(name, []):
                counts = ", ".join(
                    f"{p[k]} {label}" for k, label in [("new_classes", "new"), ("changed_classes", "changed"), ("removed_classes", "removed")] if p.get(k)
                )
                classes = ""
                for cl in p.get("interface_classes", []):
                    target = ""
                    if cl.get("target"):
                        t = cl["target"]
                        found = self.anchors.get((t["kind"], t["name"]))
                        text = f'{E(t["kind"])} <code>{E(t["name"])}</code>'
                        target = f' → <a href="#{found}">{text}</a>' if found else f" → {text}"
                    classes += f'<li class="{self.status_class(cl)}">{self.glyph(cl)} <code>{E(cl["name"])}</code> <span class="role">{E(cl["role"])}</span>{target} {self.ref(cl.get("ref"))}</li>'
                pk_rows.append(
                    f'<div class="package {self.status_class(p)}"><div class="package-head">{self.glyph(p)}<code class="pkg">{E(p["name"])}</code>'
                    + (f'<span class="layer">{E(p["layer"])}</span>' if p.get("layer") else "")
                    + (f'<span class="counts">{E(counts)} classes</span>' if counts else "")
                    + "</div>"
                    + (f'<p class="note">{md(p["placement"])}</p>' if p.get("placement") else "")
                    + (f'<ul class="iface-classes">{classes}</ul>' if classes else "")
                    + "</div>"
                )
            blocks.append(
                f'<div class="area"><h3>{E(name)} {dive}</h3>'
                + (f'<p class="note">{md(meta["note"])}</p>' if meta.get("note") else "")
                + "".join(pk_rows)
                + "</div>"
            )
        return "".join(blocks)

    def code(self, c: dict) -> str:
        lines = c["text"].rstrip("\n").split("\n")
        if len(lines) > 15:
            self.warnings.append(f"code excerpt at {c.get('ref', 'unknown ref')} has {len(lines)} lines; keep excerpts to 15")
        head = f'<div class="code-head">{E(c.get("lang", ""))} {self.ref(c.get("ref"))}</div>'
        return f'<div class="code">{head}<pre><code>{E(chr(10).join(lines))}</code></pre></div>'

    def steps(self, steps: list[dict]) -> str:
        items = []
        for s in steps:
            items.append(f'<li><p>{md(s["text"])} {self.ref(s.get("ref"))}</p>' + (self.code(s["code"]) if s.get("code") else "") + "</li>")
        return f'<ol class="steps">{"".join(items)}</ol>'

    # -- sections ----------------------------------------------------------------------------

    def section(self, key: str, label: str, heading: str, body: str, data: object = None) -> tuple[str, str, str]:
        limit = SOFT_SECTION_WORDS.get(key)
        if data is not None and limit and words(data) > limit:
            self.warnings.append(f"section \"{key}\" has {words(data)} words of prose; the soft limit is {limit}")
        html_ = f'<section id="{key}" data-section="{key}"><div class="section-label">{E(label)}</div><h2>{E(heading)}</h2>{body}</section>'
        return key, label, html_

    def change_map(self) -> tuple[str, str, str] | None:
        """The overview right after the framing: the services diagram when more than one service is involved,
        then one change-flow diagram per entry point. Every box links to its card."""
        body = self.generated_figure(GENERATED_SERVICES, "Green is added, yellow changed, red removed, grey involved but unchanged. Click a box to jump to its interface.")
        flows = [d for d in self.generated if d.startswith("flow-")]
        if not flows:
            if self.contracts.get("tables") or self.contracts.get("endpoints") or self.contracts.get("routes"):
                self.warnings.append("no entry points in the fragments, so the page has no change-flow diagram")
            if not body:
                return None
        else:
            body += '<div class="flows">' + "".join(self.generated_figure(d) for d in flows) + "</div>"
            body += '<p class="map-legend">Each diagram starts at one entry point. Green is added, yellow changed, red removed, blue only read or written, grey unchanged. Click a box to jump to its diff.</p>'
        return "map", "Change map", f'<section id="map" data-section="map"><div class="section-label">Change map</div>{body}</section>'

    def render_sections(self) -> list[tuple[str, str, str]]:
        p, c = self.page, self.contracts
        out = []
        m = self.change_map()
        if m:
            out.append(m)

        # The interfaces section and its four parts are on every page, in the same place, so a reader who
        # has seen one page knows where to look on the next, and "no change" is stated instead of implied.
        s = p["interfaces"]
        body = (f"<p>{md(s['text'])}</p>" if s.get("text") else "") + self.gaps() + self.far_side() + self.summary_table()
        parts = [
            ("database", "Database", "No database object changes.", bool(c.get("tables")),
             lambda: self.database(c["tables"])),
            ("messaging", "Messaging", "No exchange, queue, binding or message changes.", bool(c.get("routes") or c.get("messages")),
             lambda: (self.lanes(c["routes"]) if c.get("routes") else "") + "".join(self.message(m) for m in c.get("messages", []))),
            ("http", "HTTP", "No HTTP endpoint or client changes.", bool(c.get("endpoints")),
             lambda: "".join(self.endpoint(e) for e in sorted(c["endpoints"], key=lambda e: e["direction"] != "server"))),
            ("boundaries", "Other boundaries", "No configuration, job, file, cache or event changes.", bool(c.get("boundaries")),
             lambda: self.boundaries(c["boundaries"])),
        ]
        for key, label, empty, present, render in parts:
            d = s.get(key) or {"heading": label}
            if present and not s.get(key):
                self.warnings.append(f"page.json interfaces has no \"{key}\" heading; the default \"{label}\" is used")
            if not present:
                body += f'<h3 id="{key}" data-section="{key}">{E(label)}</h3><p class="none">{E(empty)}</p>'
                if s.get(key):
                    self.warnings.append(f"page.json interfaces.{key} has a heading but contracts.json holds no {label.lower()} objects; it is not shown")
                continue
            body += (
                f'<h3 id="{key}" data-section="{key}"><span class="sub-label">{E(label)}:</span> {E(d["heading"])}</h3>'
                + (f"<p>{md(d['text'])}</p>" if d.get("text") else "") + render() + self.diagram(d.get("diagram"))
            )
        out.append(self.section("interfaces", "Interfaces", s["heading"], body, s))

        s = p["modules"]
        body = f"<p>{md(s['text'])}</p>" if s.get("text") else ""
        body += self.packages(s.get("areas", []))
        if s.get("crossings"):
            body += "<h3>Boundaries crossed</h3><ul>" + "".join(f"<li>{md(x)}</li>" for x in s["crossings"]) + "</ul>"
        if s.get("dependencies"):
            body += "<h3>New dependencies</h3><ul>" + "".join(f"<li>{md(x)}</li>" for x in s["dependencies"]) + "</ul>"
        body += self.diagram(s.get("diagram"))
        out.append(self.section("modules", "Modules and placement", s["heading"], body, s))

        if p.get("requirements"):
            s = p["requirements"]
            items = "".join(f"<li>{md(x['text'])}" + (f'<div class="where">{md(x["where"])}</div>' if x.get("where") else "") + "</li>" for x in s["criteria"])
            out.append(self.section("requirements", "Requirements", s["heading"], f'<ul class="criteria">{items}</ul>', s))

        if p.get("concepts"):
            s = p["concepts"]
            body = ""
            if s.get("terms"):
                body += "<dl>" + "".join(f"<dt>{E(t['term'])}</dt><dd>{md(t['text'])}</dd>" for t in s["terms"]) + "</dl>"
            if s.get("decisions"):
                body += "<h3>Decisions</h3><ul>" + "".join(
                    f"<li>{md(d['text'])}" + (f'<div class="where">Rejected: {md(d["rejected"])}</div>' if d.get("rejected") else "") + f" {self.ref(d.get('ref'))}</li>" for d in s["decisions"]
                ) + "</ul>"
            if s.get("open_points"):
                body += "<h3>Open points the source lists</h3><ul>" + "".join(f"<li>{md(x)}</li>" for x in s["open_points"]) + "</ul>"
            out.append(self.section("concepts", "Concepts and decisions", s["heading"], body, s))

        if p.get("internals"):
            s = p["internals"]
            body = f"<p>{md(s['text'])}</p>" if s.get("text") else ""
            for f in s.get("flows", []):
                if len(f["steps"]) > MAX_FLOW_STEPS:
                    self.warnings.append(f"flow \"{f['heading']}\" has {len(f['steps'])} steps; keep code internals to {MAX_FLOW_STEPS} per flow")
                body += f'<h3>{E(f["heading"])}' + (f' <span class="chip">{E(f["area"])}</span>' if f.get("area") else "") + "</h3>"
                body += (f"<p>{md(f['text'])}</p>" if f.get("text") else "") + self.diagram(f.get("diagram")) + self.steps(f["steps"])
            out.append(self.section("internals", "Code internals", s["heading"], body, s))

        if p.get("discussion"):
            s = p["discussion"]
            items = "".join(
                f'<li><strong>{E(t["who"])}</strong>' + (f' <span class="chip">{E(t["state"])}</span>' if t.get("state") else "")
                + f": {md(t['asked'])}" + (f'<div class="where">Answer: {md(t["answer"])}</div>' if t.get("answer") else "")
                + (f' <a href="{E(t["url"])}">thread</a>' if t.get("url", "").startswith(("http://", "https://")) else "") + "</li>"
                for t in s.get("threads", [])
            )
            out.append(self.section("discussion", "Discussion", s["heading"], f'<ul class="threads">{items}</ul>', s))

        if p.get("files"):
            s = p["files"]
            rows = "".join(
                f'<tr><td>{self.ref(f["path"] + ":1", f["path"]) if REF_RE.match(f["path"] + ":1") else E(f["path"])}</td><td>{E(f.get("status", ""))}</td>'
                f'<td class="num add">{"+" + str(f["added"]) if "added" in f else ""}</td><td class="num del">{"−" + str(f["removed"]) if "removed" in f else ""}</td></tr>'
                for f in s.get("files", [])
            )
            body = f'<details class="fold"><summary>{len(s.get("files", []))} files</summary><div class="scroll"><table class="files"><tbody>{rows}</tbody></table></div></details>'
            out.append(self.section("files", "Files", s["heading"], body))
        return out

    def header(self) -> str:
        p = self.page
        src = p["source"]
        label = E(src["label"])
        if src.get("url", "").startswith(("http://", "https://")):
            label = f'<a href="{E(src["url"])}">{label}</a>'
        facts_ = [f"{E(src['kind'])} {label}"]
        if src.get("author"):
            facts_.append(f"by {E(src['author'])}")
        if src.get("date"):
            facts_.append(E(src["date"]))
        diff = p.get("diff")
        if diff:
            facts_.append(f"<code>{E(diff['head_ref'])}</code> → <code>{E(diff['base_ref'])}</code> at <code>{E(diff['head_sha'][:12])}</code>")
        t = p.get("ticket")
        if t:
            tl = E(t["id"]) + (f" {E(t['title'])}" if t.get("title") else "")
            facts_.append("ticket " + (f'<a href="{E(t["url"])}">{tl}</a>' if t.get("url", "").startswith(("http://", "https://")) else tl))
        return (
            f'<header class="page-header"><div class="state chip">{E(p["state"])}</div><h1>{E(p["title"])}</h1>'
            f'<p class="lede">{md(p["summary"])}</p><p class="facts">{" · ".join(facts_)}</p>'
            f'<p class="facts">generated {E(p["generated"])} · size {E(p["size"])}</p></header>'
            f'<section id="framing" data-section="framing" class="framing">{"".join(f"<p>{md(x)}</p>" for x in p["framing"])}</section>'
        )


def cdn_script() -> str:
    return (
        '<script type="module">\n'
        "const blocks = [...document.querySelectorAll('pre[data-mermaid]')];\n"
        "const fail = (pre, text) => { const p = document.createElement('p'); p.className = 'diagram-error'; p.textContent = text; pre.before(p); };\n"
        "if (blocks.length) {\n"
        "  try {\n"
        f"    const {{ default: mermaid }} = await import('{MERMAID_CDN}');\n"
        "    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default' });\n"
        "    let n = 0;\n"
        "    for (const pre of blocks) {\n"
        "      try {\n"
        "        await mermaid.parse(pre.textContent);\n"
        "        const { svg } = await mermaid.render('explain-cdn-' + n++, pre.textContent);\n"
        "        const holder = document.createElement('div');\n"
        "        holder.innerHTML = svg;\n"
        "        pre.replaceWith(holder);\n"
        "      } catch (e) { fail(pre, 'This diagram could not be drawn; its source is below.'); }\n"
        "    }\n"
        "  } catch (e) { blocks.forEach(pre => fail(pre, 'Mermaid could not be loaded, so the diagram source is shown instead.')); }\n"
        "}\n"
        "</script>"
    )


EXTERNAL_RE = re.compile(r"""(?:\ssrc\s*=\s*["']?\s*https?://|<link\b[^>]*\shref\s*=\s*["']?\s*https?://|url\(\s*["']?\s*https?://)""", re.I)


def build_page(page: dict, contracts: dict, diagrams_dir: Path | None) -> tuple[str | None, list[str], list[str], dict]:
    """Return (html or None, errors, warnings, info)."""
    errors = validate(page, PAGE_SCHEMA, "page") + validate(contracts, CONTRACTS_SCHEMA, "contracts", "merged")
    if errors:
        return None, errors, [], {}
    ids = [d["id"] for d in page.get("diagrams", [])]
    for d in ids:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", d):
            errors.append(f"page.diagrams: id \"{d}\" must be lower-case letters, digits and hyphens, the .mmd and .svg file name")
        if d in (GENERATED_SERVICES, GENERATED_ER) or d.startswith("flow-"):
            errors.append(f"page.diagrams: id \"{d}\" is reserved for the diagrams build.py generates")
    if len(ids) != len(set(ids)):
        errors.append("page.diagrams: two diagrams share an id")
    if errors:
        return None, errors, [], {}

    r = Page(page, contracts, diagrams_dir)
    sections = r.render_sections()
    framing_words = words(page["framing"])
    if framing_words > SOFT_SECTION_WORDS["framing"]:
        r.warnings.append(f"the framing has {framing_words} words; the soft limit is {SOFT_SECTION_WORDS['framing']}")
    for d in ids:
        if d not in r.used_diagrams:
            r.warnings.append(f"diagram \"{d}\" is listed but no section shows it")
    if r.errors:
        return None, r.errors, r.warnings, {}

    toc = '<li><a href="#framing">Overview</a></li>' + "".join(f'<li><a href="#{key}">{E(label)}</a></li>' for key, label, _ in sections)
    data = json.dumps({"page": page, "contracts": contracts}, ensure_ascii=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    out = (
        template.replace("{{TITLE}}", E(page["title"]))
        .replace("{{CONTENT_WIDTH}}", str(CONTENT_WIDTH))
        .replace("{{HEADER}}", r.header())
        .replace("{{TOC}}", toc)
        .replace("{{SECTIONS}}", "".join(h for _, _, h in sections))
        .replace("{{DATA}}", data)
        .replace("{{MERMAID_FALLBACK}}", cdn_script() if r.cdn_needed else "")
    )

    if EXTERNAL_RE.search(out):
        r.errors.append("the page loads a resource from the network (src, <link href> or CSS url()); it must work offline")
    size = len(out.encode("utf-8"))
    if size > MAX_PAGE_BYTES:
        r.errors.append(f"the page is {size / 1024 / 1024:.1f} MB, the limit is {MAX_PAGE_BYTES // 1024 // 1024} MB")
    if r.errors:
        return None, r.errors, r.warnings, {}
    info = {"sections": [k for k, _, _ in sections], "diagrams": r.used_diagrams, "cdn_fallback": r.cdn_needed, "bytes": size}
    return out, [], r.warnings, info


def cmd_page(args: argparse.Namespace) -> int:
    try:
        page = read_json(args.page)
        contracts = read_json(args.contracts) if args.contracts else {"areas": []}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error {exc}")
        return 1
    diagrams_dir = Path(args.diagrams_dir) if args.diagrams_dir else None
    out, errors, warnings, info = build_page(page, contracts, diagrams_dir)
    if args.code_tree:
        warnings = warnings + [f"bad ref {p}" for p in check_refs(page, "page", Path(args.code_tree), args.base)]
    for w in warnings:
        print(f"warning {w}")
    for e in errors:
        print(f"error {e}")
    if out is None:
        return 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"built {args.out}: sections {', '.join(info['sections'])}; diagrams {', '.join(info['diagrams']) or 'none'}"
          + ("; diagrams without an SVG are drawn by the Mermaid CDN fallback" if info["cdn_fallback"] else "")
          + f"; {info['bytes'] // 1024} KB")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge", help="merge the deep dives' fragments into contracts.json")
    m.add_argument("fragments", nargs="+")
    m.add_argument("--checklist", help="the surface scan's contract-files.json; files no fragment covers are reported as gaps")
    m.add_argument("--code-tree", help="the head checkout; every path:line ref is checked against it")
    m.add_argument("--base", help="the base SHA, for base:path:line refs")
    m.add_argument("--out", required=True)
    m.set_defaults(func=cmd_merge)
    d = sub.add_parser("diagrams", help="write the generated Mermaid sources")
    d.add_argument("contracts")
    d.add_argument("--out-dir", required=True)
    d.set_defaults(func=cmd_diagrams)
    p = sub.add_parser("page", help="build the HTML page")
    p.add_argument("page")
    p.add_argument("--contracts")
    p.add_argument("--diagrams-dir")
    p.add_argument("--code-tree", help="the head checkout; every path:line ref in page.json is checked against it")
    p.add_argument("--base", help="the base SHA, for base:path:line refs")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_page)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
