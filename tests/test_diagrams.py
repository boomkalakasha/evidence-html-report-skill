import copy
import html
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from report_diagrams import validate_diagrams, diagram_unknown_fields, render_diagram


def sample():
    return {
        "evidence": [{"id": "E1"}],
        "verdict": {"diagramId": "delivery"},
        "sections": [{"kind": "diagram", "diagramId": "delivery"}],
        "diagrams": [{
            "id": "delivery", "title": "产品接入变化", "kind": "architecture", "direction": "LR",
            "nodes": [
                {"id": "start", "label": "入口", "shape": "terminator"},
                {"id": "frontend", "label": "原页面与管理页", "beforeLabel": "原页面", "shape": "process", "change": "modified", "evidence": ["E1"]},
                {"id": "legacy", "label": "旧维护入口", "shape": "process", "change": "removed"},
                {"id": "module", "label": "共享能力", "shape": "process", "change": "added"},
                {"id": "db", "label": "业务数据", "shape": "store"},
            ],
            "edges": [
                {"from": "start", "to": "frontend", "label": "请求"},
                {"from": "frontend", "to": "legacy", "label": "旧接法", "change": "removed"},
                {"from": "frontend", "to": "module", "label": "进程内调用", "change": "added", "style": "dashed"},
                {"from": "module", "to": "db", "label": "按原契约访问", "change": "added"},
            ],
            "groups": [{"id": "runtime", "label": "同一产品进程", "nodes": ["frontend", "legacy", "module"]}],
            "note": "计划接法，尚待实施。",
        }],
    }


class RendererStub:
    def __init__(self, data):
        self.data = data
        self.ids = set()

    def unique_id(self, preferred):
        current, number = preferred, 2
        while current in self.ids:
            current = f"{preferred}-{number}"
            number += 1
        self.ids.add(current)
        return current

    def text(self, value, focusable=True):
        return html.escape(str(value), quote=True)

    def refs(self, refs):
        return "".join('<sup class="test-ref">' + html.escape(ref) + '</sup>' for ref in refs)


class DiagramParser(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.state = None
        self.scenes = {}
        self.ids = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "section" and "data-diagram-state" in attrs:
            self.state = attrs["data-diagram-state"]
            self.scenes[self.state] = {"nodes": set(), "edges": set()}
        if self.state and "data-node-id" in attrs:
            self.scenes[self.state]["nodes"].add(attrs["data-node-id"])
        if self.state and "data-edge-from" in attrs:
            self.scenes[self.state]["edges"].add((attrs["data-edge-from"], attrs["data-edge-to"]))

    def handle_endtag(self, tag):
        if tag == "section":
            self.state = None


class DiagramTests(unittest.TestCase):
    def test_declared_outcomes_can_be_retained_or_replaced(self):
        data = sample()
        diagram = data["diagrams"][0]
        for before, after in (("frontend", "frontend"), ("legacy", "module")):
            with self.subTest(before=before, after=after):
                diagram["outcomes"] = {"before": before, "after": after}
                validate_diagrams(data)
                self.assertEqual(diagram_unknown_fields(data), [])
                scenes = DiagramParser(render_diagram(RendererStub(data), "delivery")).scenes
                self.assertIn(before, scenes["before"]["nodes"])
                self.assertIn(after, scenes["after"]["nodes"])

    def test_declared_outcomes_cannot_be_missing_or_hidden_in_their_view(self):
        for declaration, message in (
            ({"before": "legacy"}, "同时填写"),
            ({"before": "legacy", "after": "missing"}, "引用存在"),
            ({"before": "module", "after": "module"}, "改前视图不可见"),
            ({"before": "legacy", "after": "legacy"}, "改后视图不可见"),
        ):
            with self.subTest(declaration=declaration):
                data = sample()
                data["diagrams"][0]["outcomes"] = declaration
                with self.assertRaisesRegex(ValueError, message):
                    validate_diagrams(data)

    def test_parallel_requests_keep_both_labels_and_stable_distinct_paths(self):
        data = {'evidence': [], 'diagrams': [{
            'id': 'requests', 'title': '提交与查询',
            'nodes': [{'id': 'page', 'label': '页面', 'column': 0, 'row': 0},
                      {'id': 'api', 'label': '接口', 'column': 1, 'row': 0}],
            'edges': [{'from': 'page', 'to': 'api', 'label': '提交导出'},
                      {'from': 'page', 'to': 'api', 'label': '查询状态', 'change': 'added'}]
        }]}
        validate_diagrams(data)
        markup = render_diagram(RendererStub(data), 'requests')
        ns = {'s': 'http://www.w3.org/2000/svg'}
        svgs = [ET.fromstring(svg) for svg in re.findall(r'<svg\b.*?</svg>', markup, re.S)[:3]]
        scenes = [[g for g in svg.findall('s:g', ns) if g.get('data-edge-from')] for svg in svgs]
        self.assertEqual([len(scene) for scene in scenes], [1, 2, 2])
        paths = [g.find('s:path', ns).get('d') for g in scenes[1]]
        self.assertEqual(len(set(paths)), 2)
        self.assertEqual(scenes[0][0].find('s:path', ns).get('d'), paths[0])
        boxes = [g.find('s:rect', ns) for g in scenes[1]]
        upper_bottom = float(boxes[0].get('y')) + float(boxes[0].get('height'))
        self.assertLess(upper_bottom, float(boxes[1].get('y')))
        for box in boxes:
            self.assertGreaterEqual(float(box.get('y')), 0)
            self.assertLessEqual(float(box.get('y')) + float(box.get('height')), float(svgs[1].get('viewBox').split()[3]))

    def test_unchanged_diagram_does_not_repeat_identical_scenes(self):
        data = sample()
        diagram = data['diagrams'][0]
        for item in [*diagram['nodes'], *diagram['edges']]:
            item.pop('beforeLabel', None)
            item['change'] = 'unchanged'
        validate_diagrams(data)
        markup = render_diagram(RendererStub(data), 'delivery')
        parser = DiagramParser(markup)
        self.assertEqual(set(parser.scenes), {'after'})
        self.assertNotIn('data-diagram-view=', markup)
        self.assertNotIn('data-legend-change=',markup)
        self.assertNotIn('；保留</title>',markup)

    def test_three_views_filter_nodes_edges_and_keep_static_content(self):
        data = sample()
        validate_diagrams(data)
        markup = render_diagram(RendererStub(data), "delivery")
        scenes = DiagramParser(markup).scenes
        self.assertEqual(set(scenes), {"before", "change", "after"})
        self.assertEqual(scenes["before"]["nodes"], {"start", "frontend", "legacy", "db"})
        self.assertEqual(scenes["after"]["nodes"], {"start", "frontend", "module", "db"})
        self.assertIn(("frontend", "legacy"), scenes["before"]["edges"])
        self.assertNotIn(("frontend", "module"), scenes["before"]["edges"])
        self.assertIn(("frontend", "module"), scenes["after"]["edges"])
        self.assertNotIn(("frontend", "legacy"), scenes["after"]["edges"])
        self.assertEqual(len(scenes["change"]["nodes"]), 5)
        self.assertNotIn(" hidden", markup)

    def test_modified_label_is_old_in_before_new_in_after_and_summary(self):
        data = sample()
        markup = render_diagram(RendererStub(data), "delivery")
        svgs = [ET.fromstring(svg) for svg in re.findall(r"<svg\b.*?</svg>", markup, re.S)[:3]]
        namespace = {"s": "http://www.w3.org/2000/svg"}
        labels = []
        for svg in svgs:
            node = next(node for node in svg.findall("s:g", namespace) if node.get("data-node-id") == "frontend")
            labels.append("".join(node.find("s:text", namespace).itertext()))
        self.assertEqual(labels, ["原页面", "原页面与管理页", "原页面与管理页"])
        self.assertIn("原页面 → 原页面与管理页", markup)

    def test_legend_uses_only_actual_shapes_changes_edges(self):
        data = sample()
        markup = render_diagram(RendererStub(data), "delivery")
        self.assertIn('<details class="change-diagram-legend" open>', markup)
        self.assertEqual(set(re.findall(r'data-legend-shape="(.*?)"', markup)), {"process", "terminator", "store"})
        self.assertEqual(set(re.findall(r'data-legend-change="(.*?)"', markup)), {"unchanged", "added", "removed", "modified"})
        self.assertEqual(set(re.findall(r'data-legend-edge="(.*?)"', markup)), {"solid", "dashed"})
        self.assertIn("＋ 新增", markup)
        self.assertIn("－ 移除", markup)
        self.assertIn("↻ 修改", markup)

    def test_unknown_fields_and_references_do_not_silently_disappear(self):
        data = sample()
        self.assertEqual(diagram_unknown_fields(data), [])
        data["diagrams"][0]["nodes"][0]["typo"] = "missing"
        self.assertIn("nodes[0].typo", diagram_unknown_fields(data)[0])
        data["diagrams"][0]["nodes"][0]["evidence"] = ["MISSING"]
        with self.assertRaisesRegex(ValueError, "不存在的证据"):
            validate_diagrams(data)

    def test_bad_shape_change_edge_group_and_position_fail(self):
        mutators = [
            lambda d: d["nodes"][0].update(shape="pentagon"),
            lambda d: d["nodes"][0].update(change="insert"),
            lambda d: d["nodes"][0].update(beforeLabel="旧入口"),
            lambda d: d["nodes"][0].update(column=True, row=0),
            lambda d: d["edges"][0].update(to="missing"),
            lambda d: d["edges"][0].update(label=""),
            lambda d: d["groups"][0].update(nodes=["missing"]),
            lambda d: d["groups"][0].update(nodes=["frontend", "module"]),
            lambda d: d["groups"].append({"id": "other", "label": "other", "nodes": ["frontend"]}),
        ]
        for mutate in mutators:
            with self.subTest(mutate=mutate):
                data = sample()
                mutate(data["diagrams"][0])
                with self.assertRaises(ValueError):
                    validate_diagrams(data)

    def test_cycle_needs_complete_explicit_layout(self):
        data = sample()
        data["diagrams"][0]["edges"].append({"from": "db", "to": "start", "label": "回调"})
        with self.assertRaisesRegex(ValueError, "循环"):
            validate_diagrams(data)
        for index, node in enumerate(data["diagrams"][0]["nodes"]):
            node.update(column=index % 3, row=index // 3)
        data["diagrams"][0]["groups"] = []
        validate_diagrams(data)
        self.assertIn("回调", render_diagram(RendererStub(data), "delivery"))

    def test_duplicate_ids_and_dangling_diagram_reference_fail(self):
        data = sample()
        data["diagrams"].append(copy.deepcopy(data["diagrams"][0]))
        with self.assertRaises(ValueError):
            validate_diagrams(data)
        data = sample()
        data["verdict"]["diagramId"] = "no-such-diagram"
        with self.assertRaisesRegex(ValueError, "diagramId"):
            validate_diagrams(data)

    def test_labels_are_escaped_and_each_render_allocates_unique_ids(self):
        data = sample()
        data["diagrams"][0]["nodes"][0]["label"] = '<script>alert("x")</script>'
        data["diagrams"][0]["title"] = '<img src="x" onerror="alert(1)">'
        data["diagrams"][0]["groups"][0]["label"] = '<script>bad()</script>'
        validate_diagrams(data)
        renderer = RendererStub(data)
        renderer.ids.add("change-diagram-delivery-before")
        markup = render_diagram(renderer, "delivery") + render_diagram(renderer, "delivery")
        parser = DiagramParser(markup)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertNotIn("<script>", markup)
        self.assertNotIn('<img src="x"', markup)
        self.assertIn("&lt;script&gt;", markup)
        for svg in re.findall(r"<svg\b.*?</svg>", markup, re.S):
            ET.fromstring(svg)

    def test_both_directions_and_all_shapes_generate_finite_geometry(self):
        for direction in ("LR", "TB"):
            with self.subTest(direction=direction):
                data = sample()
                diagram = data["diagrams"][0]
                diagram["direction"] = direction
                diagram["nodes"][1]["shape"] = "decision"
                diagram["nodes"][2]["shape"] = "data"
                diagram["edges"].append({"from": "start", "to": "db", "label": "跳过中间节点的关系", "change": "added"})
                validate_diagrams(data)
                markup = render_diagram(RendererStub(data), "delivery")
                self.assertNotIn("NaN", markup)
                self.assertNotIn("undefined", markup)
                self.assertIn('data-legend-shape="decision"', markup)
                self.assertIn('data-legend-shape="data"', markup)
                svg = ET.fromstring(re.findall(r"<svg\b.*?</svg>", markup, re.S)[1])
                self.assertGreater(float(svg.get("viewBox").split()[2]), 300)

    def test_all_added_or_all_removed_explains_the_empty_view(self):
        data = sample()
        data["diagrams"][0]["groups"] = []
        for change, message in (("added", "改前尚无此结构"), ("removed", "改后不再保留此结构")):
            for node in data["diagrams"][0]["nodes"]:
                node["change"] = change
                node.pop("beforeLabel", None)
            for edge in data["diagrams"][0]["edges"]:
                edge["change"] = change
            validate_diagrams(data)
            self.assertIn(message, render_diagram(RendererStub(data), "delivery"))


if __name__ == "__main__":
    unittest.main()
