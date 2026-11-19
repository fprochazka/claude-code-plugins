"""Tests for build.py against the hand-made fixture in fixtures/. Needs jsonschema, not mmdc."""

from __future__ import annotations

import contextlib
import copy
import html
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))

import build  # noqa: E402


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fragments() -> list[tuple[str, dict]]:
    return [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(FIXTURES.glob("subdomain-*.json"))]


def merged() -> dict:
    result, errors = build.merge(fragments(), load("contract-files.json"))
    assert not errors, errors
    return result


class SchemaTest(unittest.TestCase):
    def test_schemas_are_valid_json_schema(self):
        from jsonschema import Draft202012Validator

        for path in (build.PAGE_SCHEMA, build.CONTRACTS_SCHEMA):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_fixture_page_is_valid(self):
        self.assertEqual(build.validate(load("page.json"), build.PAGE_SCHEMA, "page"), [])

    def test_every_error_is_reported_with_its_json_path(self):
        page = load("page.json")
        page["state"] = "finished"
        del page["interfaces"]["heading"]
        page["modules"]["areas"][1]["deep_dive"] = "maybe"
        page["requirements"]["colour"] = "red"
        errors = build.validate(page, build.PAGE_SCHEMA, "page")
        self.assertEqual(len(errors), 4, errors)
        joined = "\n".join(errors)
        self.assertIn("page.state:", joined)
        self.assertIn("page.interfaces:", joined)
        self.assertIn("page.modules.areas[1].deep_dive:", joined)
        self.assertIn("page.requirements:", joined)

    def test_invalid_fragment_errors_name_the_file_and_path(self):
        frags = fragments()
        bad = copy.deepcopy(frags[1][1])
        bad["contracts"]["endpoints"][0]["request"]["fields"][2]["status"] = "renamed"
        bad["contracts"]["endpoints"][0]["rollout"]["label"] = "fine"
        _, errors = build.merge([frags[0], (frags[1][0], bad)])
        joined = "\n".join(errors)
        self.assertIn("subdomain-shipments.json.contracts.endpoints[0].request.fields[2].status:", joined)
        self.assertIn("subdomain-shipments.json.contracts.endpoints[0].rollout.label:", joined)

    def test_unknown_checklist_entry_needs_a_note(self):
        frags = fragments()
        bad = copy.deepcopy(frags[0][1])
        del bad["checklist"][-1]["note"]
        _, errors = build.merge([(frags[0][0], bad)])
        self.assertTrue(any("checklist[5]" in e for e in errors), errors)


class MergeTest(unittest.TestCase):
    def test_objects_are_combined_by_key(self):
        m = merged()
        self.assertEqual(m["areas"], ["invoicing", "shipments"])
        self.assertEqual([t["name"] for t in m["tables"]], ["invoice", "invoice_reminder", "payment", "customer_terms"])
        self.assertEqual(len(m["endpoints"]), 2)
        self.assertEqual(len(m["packages"]), 4)

    def test_identical_facts_merge_and_accesses_are_joined(self):
        payment = next(t for t in merged()["tables"] if t["name"] == "payment")
        self.assertEqual(payment["areas"], ["invoicing", "shipments"])
        self.assertEqual(len(payment["accesses"]), 2)

    def test_different_facts_are_a_conflict_and_the_first_is_kept(self):
        m = merged()
        self.assertEqual(len(m["conflicts"]), 1)
        conflict = m["conflicts"][0]
        self.assertEqual((conflict["kind"], conflict["key"]), ("tables", "invoice"))
        self.assertIn("columns", conflict["differs"])
        invoice = next(t for t in m["tables"] if t["name"] == "invoice")
        self.assertEqual(invoice["source"], "migration")

    def test_contract_files_without_coverage_are_gaps(self):
        gaps = {g["path"]: g["reason"] for g in merged()["checklist_gaps"]}
        self.assertEqual(gaps["shipments/src/main/resources/openapi/shipments.yaml"], "no deep dive covered this file")
        self.assertIn("shared base class", gaps["billing/src/main/kotlin/com/example/billing/reminder/ReminderMailListener.kt"])
        self.assertEqual(len(gaps), 2)

    def test_merged_document_is_valid(self):
        self.assertEqual(build.validate(merged(), build.CONTRACTS_SCHEMA, "contracts", "merged"), [])


class PageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for f in FIXTURES.glob("*.mmd"):
            shutil.copy(f, self.tmp)
        for f in FIXTURES.glob("*.svg"):
            shutil.copy(f, self.tmp)
        # Stand-ins for what mmdc draws from the generated sources: one <a> per click line, as mmdc writes them.
        for n, (diagram_id, _, source) in enumerate(build.generated_diagrams(merged()), 1):
            links = "".join(f'<a xlink:href="{h}"><rect/></a>' for h in re.findall(r'click \w+ href "([^"]+)"', source))
            (self.tmp / f"{diagram_id}.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" id="explain-g{n}" viewBox="0 0 600 200">{links}</svg>')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, page: dict | None = None, contracts: dict | None = None):
        return build.build_page(page or load("page.json"), contracts or merged(), self.tmp)

    def test_sections_come_in_the_fixed_order(self):
        out, errors, _, info = self.build()
        self.assertEqual(errors, [])
        self.assertEqual(info["sections"], ["map", "interfaces", "modules", "requirements", "concepts", "internals", "discussion", "files"])
        positions = [out.index(f'id="{k}" data-section="{k}"') for k in ["database", "messaging", "http", "boundaries"]]
        self.assertEqual(positions, sorted(positions))

    def test_interface_parts_without_changes_say_so(self):
        contracts = merged()
        del contracts["routes"], contracts["messages"]
        out, errors, _, _ = self.build(contracts=contracts)
        self.assertEqual(errors, [])
        self.assertIn('id="messaging" data-section="messaging"', out)
        self.assertIn("No exchange, queue, binding or message changes.", out)

    def test_framing_comes_first_and_has_one_to_three_paragraphs(self):
        out, errors, _, _ = self.build()
        self.assertEqual(errors, [])
        self.assertLess(out.index('id="framing"'), out.index('id="interfaces"'))
        page = load("page.json")
        page["framing"] = ["one", "two", "three", "four"]
        self.assertTrue(any(e.startswith("page.framing:") for e in build.validate(page, build.PAGE_SCHEMA, "page")))
        page["framing"] = []
        self.assertTrue(any(e.startswith("page.framing:") for e in build.validate(page, build.PAGE_SCHEMA, "page")))

    def test_cost_and_rollout_labels_are_shown(self):
        out, _, _, _ = self.build()
        self.assertIn('<span class="chip rollout r-breaks-existing-callers">breaks existing callers</span>', out)
        self.assertIn('<span class="chip cost">downtime or failover</span>', out)
        self.assertIn("Not covered by this page:", out)

    def test_interface_classes_link_to_their_interface(self):
        out, _, _, _ = self.build()
        self.assertIn('<a href="#table-invoice-reminder">table <code>invoice_reminder</code></a>', out)
        self.assertIn("10 new classes", out)

    def test_svgs_are_inlined_with_distinct_ids(self):
        out, errors, _, info = self.build()
        self.assertEqual(errors, [])
        self.assertFalse(info["cdn_fallback"])
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg" id="explain-d1"', out)
        self.assertIn('id="explain-d2"', out)
        self.assertNotIn("cdn.jsdelivr.net", out)

    def test_duplicate_svg_id_is_renamed(self):
        svg = (self.tmp / "architecture.svg").read_text().replace("explain-d2", "explain-d1")
        (self.tmp / "architecture.svg").write_text(svg)
        out, errors, warnings, _ = self.build()
        self.assertEqual(errors, [])
        # The architecture diagram comes first on the page, so the sequence diagram is the one renamed.
        self.assertIn('id="explain-invoicing-flow"', out)
        self.assertIn("#explain-invoicing-flow{", out)
        self.assertTrue(any("already used" in w for w in warnings))

    def test_wide_svg_warns(self):
        svg = (self.tmp / "architecture.svg").read_text().replace('viewBox="0 0 720 200"', 'viewBox="0 0 1800 200"')
        (self.tmp / "architecture.svg").write_text(svg)
        _, errors, warnings, _ = self.build()
        self.assertEqual(errors, [])
        self.assertTrue(any("1800px wide" in w for w in warnings), warnings)

    def test_diagram_without_svg_uses_the_cdn_fallback(self):
        (self.tmp / "invoicing-flow.svg").unlink()
        out, errors, _, info = self.build()
        self.assertEqual(errors, [])
        self.assertTrue(info["cdn_fallback"])
        self.assertIn(build.MERMAID_CDN, out)
        self.assertIn("<pre class=\"mermaid-src\" data-mermaid>sequenceDiagram", out)
        self.assertIsNone(build.EXTERNAL_RE.search(out))

    def test_svg_with_script_is_refused(self):
        (self.tmp / "architecture.svg").write_text('<svg id="x" viewBox="0 0 10 10"><script>alert(1)</script></svg>')
        out, errors, _, _ = self.build()
        self.assertIsNone(out)
        self.assertTrue(any("script" in e for e in errors))

    def test_text_is_escaped_and_markdown_is_limited(self):
        page = load("page.json")
        page["summary"] = "<script>alert(1)</script> **bold** `<b>` [x](javascript:alert(1)) [ok](https://example.com)"
        out, errors, _, _ = self.build(page=page)
        self.assertEqual(errors, [])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; <strong>bold</strong> <code>&lt;b&gt;</code> [x](javascript:alert(1))", out)
        self.assertIn('<a href="https://example.com">ok</a>', out)

    def test_embedded_data_cannot_close_its_script(self):
        page = load("page.json")
        page["title"] = "</script><script>alert(1)</script>"
        out, _, _, _ = self.build(page=page)
        data = re.search(r'<script type="application/json" id="explain-data">(.*?)</script>', out, re.S).group(1)
        self.assertEqual(json.loads(data)["page"]["title"], page["title"])

    def test_refs_link_to_the_blob_at_the_pinned_sha(self):
        out, _, _, _ = self.build()
        self.assertIn(
            'href="https://gitlab.example.com/acme/fulfilment/-/blob/2222222222222222222222222222222222222222/billing/src/main/resources/db/migration/V42__invoice_due_date.sql#L1"',
            out,
        )

    def test_refs_show_the_file_name_and_keep_the_full_path_in_the_tooltip(self):
        out, _, _, _ = self.build()
        self.assertIn('title="shipments/src/main/kotlin/com/example/shipments/api/ShipmentController.kt:41">ShipmentController.kt:41</a>', out)
        self.assertIn('title="billing/src/main/kotlin/com/example/billing/reminder/InvoiceReminderService.kt:58">InvoiceReminderService.findUnpaid()</a>', out)

    def test_access_list_is_a_table_of_access_who_and_what(self):
        out, _, _, _ = self.build()
        self.assertIn("<th>access</th><th>who</th><th>what</th>", out)
        self.assertIn("<td>selects the unpaid invoices of one customer</td>", out)

    def test_every_card_leads_with_its_one_sentence(self):
        out, _, warnings, _ = self.build()
        card = re.search(r'<article class="card st-changed" id="endpoint-server-post-orders-orderid-shipments">(.*?)</article>', out, re.S).group(1)
        self.assertTrue(card.split("</header>", 1)[1].startswith('<p class="lead">The shipment request takes a delivery window'))
        self.assertFalse(any("no lead sentence" in w for w in warnings), warnings)

    def test_summary_shows_the_boundary_kind_not_a_raw_label(self):
        out, _, _, _ = self.build()
        self.assertIn('<td>scheduled job</td><td><a href="#boundary-scheduled-job-billing-reminders-cron">billing.reminders.cron</a></td>', out)

    def test_database_part_has_a_sql_tab_and_a_relationships_tab(self):
        out, _, _, _ = self.build()
        self.assertIn('<input type="radio" name="tabs-db" id="tab-db-sql" checked>', out)
        er = out.split('data-radio="tab-db-er">', 1)[1]
        self.assertIn('id="explain-g', er.split("</div>", 1)[0])

    def test_far_side_reads_name_the_clone_and_commit_and_may_be_stale(self):
        out, _, _, _ = self.build()
        self.assertIn("clone <code>/home/dev/src/acme/customer-service</code> at <code>333333333333</code>", out)
        self.assertIn("may differ from what that service runs in production", out)

    def test_every_diagram_link_points_at_an_element_on_the_page(self):
        out, errors, _, info = self.build()
        self.assertEqual(errors, [])
        self.assertFalse(info["cdn_fallback"])
        hrefs = re.findall(r'xlink:href="#([^"]+)"', out)
        self.assertGreater(len(hrefs), 10)
        for h in hrefs:
            self.assertIn(f'id="{h}"', out)

    def test_page_has_no_network_resources(self):
        out, _, _, _ = self.build()
        self.assertIsNone(build.EXTERNAL_RE.search(out))
        self.assertNotIn("{{", out)

    def test_cli_prints_errors_and_exits_non_zero(self):
        page = load("page.json")
        page["size"] = "huge"
        (self.tmp / "page.json").write_text(json.dumps(page))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = build.main(["page", str(self.tmp / "page.json"), "--out", str(self.tmp / "out.html")])
        self.assertEqual(code, 1)
        self.assertIn("error page.size:", stdout.getvalue())


class CodeDiffTest(unittest.TestCase):
    @staticmethod
    def text(lines: list) -> list[str]:
        return [f"{x.sign} {x.code}" + (f"  -- {x.comment}" if x.comment else "") for x in lines]

    def table(self, name: str) -> dict:
        return next(t for t in merged()["tables"] if t["name"] == name)

    def test_changed_table_is_a_diff_of_its_create_table_statement(self):
        lines = [f"{x.sign} {x.code}" for x in build.table_sql_lines(self.table("invoice"))]
        self.assertEqual(lines, [
            "  CREATE TABLE invoice (",
            "    id bigint NOT NULL PRIMARY KEY,",
            "    number varchar(32) NOT NULL,",
            "    customer_id bigint NOT NULL,",
            "+   due_date date NOT NULL DEFAULT current_date,",
            "-   status varchar(16) NOT NULL,",
            "+   status varchar(32) NOT NULL",
            "-   legacy_ref varchar(64)",
            "  );",
            "+ CREATE INDEX invoice_due_date_idx ON invoice (due_date);",
            "  CREATE UNIQUE INDEX invoice_number_key ON invoice (number);",
        ])

    def test_new_table_is_all_added_with_its_foreign_key(self):
        lines = build.table_sql_lines(self.table("invoice_reminder"))
        self.assertEqual({x.sign for x in lines}, {"+"})
        self.assertIn("  FOREIGN KEY (invoice_id) REFERENCES invoice (id),", [x.code for x in lines])

    def test_reference_without_a_foreign_key_is_a_comment(self):
        line = next(x for x in build.table_sql_lines(self.table("invoice")) if "customer_id" in x.code)
        self.assertTrue(line.comment.startswith("refers to customer.id, no foreign key"))
        self.assertNotIn("REFERENCES", line.code)

    def test_mysql_keeps_indexes_inside_the_statement(self):
        t = copy.deepcopy(self.table("invoice"))
        t["dialect"] = "mysql"
        codes = [x.code for x in build.table_sql_lines(t)]
        self.assertIn("  KEY invoice_due_date_idx (due_date),", codes)
        self.assertEqual(codes[-1], ");")

    def test_comments_are_aligned_and_continue_in_the_same_column(self):
        lines = [build.Line(" ", "  id bigint", "short"), build.Line("+", "  a_much_longer_column_name text", "word " * 60)]
        rows = re.findall(r'<div class="dl[^"]*">(.*?)</div>', build.code_diff(lines, "sql"))
        plain = [html.unescape(re.sub(r"<[^>]+>", "", r)) for r in rows]
        columns = {p.index("--") for p in plain}
        self.assertEqual(len(columns), 1, plain)
        self.assertGreater(len(plain), 2)
        self.assertTrue(all(p[1:].strip().startswith("--") for p in plain[2:]))

    def test_long_unchanged_runs_are_folded(self):
        t = {"name": "wide", "status": "changed", "columns": [{"name": f"c{i}", "status": "unchanged", "type": "int"} for i in range(12)]}
        t["columns"].append({"name": "added_one", "status": "added", "type": "int"})
        out = build.code_diff(build.table_sql_lines(t), "sql")
        self.assertIn('<summary>10 unchanged lines</summary>', out)

    def test_payload_is_a_json_like_diff_with_comments(self):
        endpoint = next(e for e in merged()["endpoints"] if e["direction"] == "server")
        lines = self.text(build.payload_lines(endpoint["request"]["fields"], endpoint["request"]["unchanged_fields"]))
        self.assertIn('-   "priority": string', lines)
        self.assertIn('+   "priority": enum [STANDARD, EXPRESS]', lines)
        self.assertIn('    "items": [{', lines)
        self.assertIn('-     "weightGrams": integer', lines)
        self.assertIn('-     "quantity": integer  -- optional', lines)
        self.assertIn('+     "quantity": integer  -- required', lines)
        self.assertIn('+   "deliveryWindow": {  -- optional', lines)
        self.assertIn('+     "from": string(date-time)  -- required', lines)
        self.assertIn("    …  -- 3 more unchanged fields", lines)

    def test_meaning_change_without_a_shape_change_is_marked(self):
        endpoint = next(e for e in merged()["endpoints"] if e["direction"] == "server")
        lines = build.payload_lines(endpoint["responses"][0]["fields"])
        status = next(x for x in lines if '"status"' in x.code)
        self.assertEqual(status.sign, "!")
        self.assertTrue(status.comment.startswith("meaning changed"))

    def test_payload_comments_use_slashes(self):
        out = build.code_diff([build.Line("+", '  "a": string', "required")], "json")
        self.assertIn("// required", out)


class GeneratedDiagramTest(unittest.TestCase):
    def setUp(self):
        self.diagrams = {d[0]: d[2] for d in build.generated_diagrams(merged())}

    def test_one_flow_per_entry_point_plus_services_and_tables(self):
        self.assertEqual(sorted(self.diagrams), [
            "database-er",
            "flow-consumer-remindermaillistener",
            "flow-endpoint-post-orders-orderid-shipments",
            "flow-scheduled-job-invoicereminderscheduler",
            "services",
        ])

    def test_boxes_are_coloured_by_status_and_link_to_their_card(self):
        flow = self.diagrams["flow-scheduled-job-invoicereminderscheduler"]
        self.assertIn('n3[("+\u00a0invoice_reminder")]', flow)
        self.assertIn("class n3 added", flow)
        self.assertIn('click n3 href "#table-invoice-reminder"', flow)
        self.assertIn('click n1 href "#boundary-scheduled-job-billing-reminders-cron"', flow)
        self.assertIn("class n2 accessed", flow)

    def test_consumer_edge_points_from_the_message(self):
        self.assertIn('n2 -->|"+ consumes"| n1', self.diagrams["flow-consumer-remindermaillistener"])

    def test_services_diagram_needs_more_than_one_service(self):
        self.assertIn('-->|"+ HTTP GET /v2/customers/{id}/credit-limit"|', self.diagrams["services"])
        contracts = merged()
        contracts["services"] = [{"name": "billing", "status": "changed"}]
        del contracts["service_links"]
        self.assertNotIn("services", {d[0] for d in build.generated_diagrams(contracts)})

    def test_missing_foreign_key_is_a_dashed_edge(self):
        self.assertIn('n1 -.->|"customer_id, no foreign key"| n5', self.diagrams["database-er"])

    def test_labels_are_escaped_for_mermaid(self):
        self.assertEqual(build.mlabel('a "b" <c><br>d'), '"a #quot;b#quot; #lt;c#gt;<br>d"')

    def test_cli_writes_the_sources(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "contracts.json").write_text(json.dumps(merged()))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = build.main(["diagrams", str(tmp / "contracts.json"), "--out-dir", str(tmp / "d")])
            self.assertEqual(code, 0)
            self.assertIn("generated services", out.getvalue())
            self.assertTrue((tmp / "d" / "database-er.mmd").is_file())
        finally:
            shutil.rmtree(tmp)

    @unittest.skipUnless(shutil.which("mmdc"), "mmdc is not installed")
    def test_mmdc_keeps_the_links(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "er.mmd").write_text(self.diagrams["database-er"])
            subprocess.run(["mmdc", "-q", "-i", str(tmp / "er.mmd"), "-o", str(tmp / "er.svg"), "-I", "explain-t"], check=True, capture_output=True, timeout=120)
            self.assertIn('xlink:href="#table-invoice-reminder"', (tmp / "er.svg").read_text())
        finally:
            shutil.rmtree(tmp)


class RefCheckTest(unittest.TestCase):
    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        (self.tree / "src").mkdir()
        (self.tree / "src" / "A.kt").write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n")

    def tearDown(self):
        shutil.rmtree(self.tree)

    def test_missing_files_and_lines_past_the_end_are_reported(self):
        value = {"a": {"ref": "src/A.kt:10"}, "b": [{"ref": "src/A.kt:76"}], "c": {"ref": "src/Gone.kt:3"}, "d": {"ref": "src/A.kt:9-12"}}
        problems = build.check_refs(value, "frag", self.tree, None)
        self.assertEqual(len(problems), 3, problems)
        self.assertIn("frag.b[0].ref: src/A.kt:76: the file has 10 lines", problems)
        self.assertIn("frag.c.ref: src/Gone.kt:3: the file does not exist at the head", problems)

    def test_base_refs_are_read_from_git(self):
        env = build.git_env()
        git = lambda *a: subprocess.run(["git", "-C", str(self.tree), *a], check=True, capture_output=True, env=env, text=True)
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", "commit", "-qm", "base")
        sha = git("rev-parse", "HEAD").stdout.strip()
        problems = build.check_refs({"ref": "base:src/A.kt:11", "x": {"ref": "base:src/A.kt:2"}}, "f", self.tree, sha)
        self.assertEqual(problems, ["f.ref: base:src/A.kt:11: the file has 10 lines"])

    def test_merge_prints_bad_refs(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            build.main(["merge", *map(str, sorted(FIXTURES.glob("subdomain-*.json"))), "--out", str(self.tree / "c.json"), "--code-tree", str(self.tree)])
        self.assertIn("ref subdomain-invoicing.json.contracts.tables[0].ref:", out.getvalue())


class SkillTextTest(unittest.TestCase):
    """The rules the skill's prose must keep: time-only budgets that each subagent keeps itself, and the
    read-only rule for other services' clones in every subagent prompt."""

    SKILL = HERE.parent / "SKILL.md"
    REFS = HERE.parent / "references"

    def texts(self) -> dict[str, str]:
        files = [self.SKILL, *sorted(self.REFS.glob("*.md")), HERE.parents[2] / "DESIGN.md", HERE.parents[2] / "README.md"]
        return {f.name: f.read_text(encoding="utf-8") for f in files}

    def test_no_budget_counts_tool_calls(self):
        for name, text in self.texts().items():
            self.assertIsNone(re.search(r"\d+\s+tool calls|tool-call budget|budget in tool calls", text), name)

    def test_every_subagent_keeps_its_time_with_date(self):
        for name in ("surface.md", "deep-dive.md", "render.md"):
            text = (self.REFS / name).read_text(encoding="utf-8")
            self.assertIn("date +%s", text, name)
            self.assertRegex(text, r"\d+(\.\d+)? minutes", name)
        prompts = re.findall(r"```\n(First read .*?)```", self.SKILL.read_text(encoding="utf-8"), re.S)
        self.assertEqual(len(prompts), 3)
        for prompt in prompts:
            self.assertRegex(prompt, r"Budget: [\d.]+ minutes")

    def test_every_subagent_prompt_carries_the_clone_rule(self):
        prompts = re.findall(r"```\n(First read .*?)```", self.SKILL.read_text(encoding="utf-8"), re.S)
        for prompt in prompts:
            self.assertIn("Other services' clones:", prompt)


if __name__ == "__main__":
    unittest.main()
