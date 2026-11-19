"""Native figures and data-driven diagrams; standard library only."""
import base64
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NATIVE_KINDS = {"figure", "graph", "explorer"}


def registry(data, key):
    return {entry["id"]: entry for entry in data.get(key, [])}


def validate_extensions(data):
    if isinstance(data.get('schemaVersion'), bool) or data.get("schemaVersion", 1) not in (1, 2):
        raise ValueError("schemaVersion 仅支持 1 或 2")
    if data.get("defaultView", "full") not in ("brief", "full"):
        raise ValueError("defaultView 应为 brief 或 full")
    for key in ("components", "graphs", "scenarios"):
        values = data.get(key, [])
        if not isinstance(values, list):
            raise ValueError(key + " 必须是数组")
        ids = set()
        for entry in values:
            if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not re.fullmatch(r"[\w-]+", entry.get("id", "")) or entry["id"] in ids:
                raise ValueError(key + " 的 id 必须非空且唯一")
            ids.add(entry["id"])
            if not isinstance(entry.get("title"), str) or not entry["title"].strip():
                raise ValueError(key + " 必须有 title")
    components = registry(data, "components")
    graphs = registry(data, "graphs")
    scenarios = registry(data, "scenarios")
    for graph in graphs.values():
        nodes, edges = graph.get("nodes"), graph.get("edges", [])
        if not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
            raise ValueError("图必须有非空 nodes 和 edges 数组")
        ids = set()
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not re.fullmatch(r"[\w-]+", node.get("id", "")) or node["id"] in ids:
                raise ValueError("图节点 id 必须非空且唯一")
            ids.add(node["id"])
            if node.get("component") not in components:
                raise ValueError("图节点引用了不存在的 component")
        for edge in edges:
            if not isinstance(edge, dict) or edge.get("from") not in ids or edge.get("to") not in ids or not isinstance(edge.get("label"), str) or not edge["label"].strip():
                raise ValueError("图的每条边需要有效 from、to 和调用机制 label")
            if edge.get("state", "current") not in ("current", "planned", "unverified"):
                raise ValueError("边状态应为 current、planned 或 unverified")
    for scenario in scenarios.values():
        if scenario.get("graphId") not in graphs:
            raise ValueError("场景引用了不存在的 graphId")
        if scenario.get("state", "current") not in ("current", "planned", "unverified"):
            raise ValueError("场景状态应为 current、planned 或 unverified")
        steps = scenario.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("场景 steps 必须是数组")
        node_ids = {n["id"] for n in graphs[scenario["graphId"]]["nodes"]}
        for step in steps:
            if not isinstance(step, dict) or step.get("node") not in node_ids or not isinstance(step.get("body"), str) or not step["body"].strip():
                raise ValueError("每个场景步骤需要当前图中的 node 和非空 body")
    def walk(section):
        if "detailOnly" in section and not isinstance(section["detailOnly"], bool):
            raise ValueError("detailOnly 必须为布尔值")
        kind = section.get("kind")
        if kind == "graph" and section.get("graphId") not in graphs:
            raise ValueError("章节引用了不存在的 graphId")
        if kind == "explorer":
            refs = section.get("scenarioIds")
            if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)) or any(x not in scenarios for x in refs):
                raise ValueError("explorer 需要不重复且有效的 scenarioIds")
        if kind == "figure":
            figure = section.get("figure")
            if not isinstance(figure, dict) or any(not isinstance(figure.get(k), str) or not figure[k].strip() for k in ("src", "alt")):
                raise ValueError("figure 需要本地 src 和非空 alt")
        for fold in section.get("folds", []):
            walk(fold)
    for section in data.get("sections", []):
        walk(section)


def unknown_fields(data):
    """Warn on unrendered fields while preserving older inputs."""
    warnings = []
    rich = {"paragraphs", "bullets", "links", "evidence"}
    def check(value, allowed, where):
        for key in value.keys() - allowed:
            warnings.append(where + "." + key + "：未识别字段，不保证显示在正文")
    check(data, {"schemaVersion", "defaultView", "readingMode", "title", "generatedAt", "subtitle", "audience", "scope", "reportType", "verdict", "findings", "evidence", "metrics", "sections", "responsibilities", "modules", "appendices", "sources", "glossary", "evidenceLayers", "statusLabels", "factLabels", "requiredTerms", "components", "graphs", "scenarios", "diagrams", "highlights"}, "报告")
    for i, item in enumerate(data.get('highlights', [])):
        check(item, {'label','value','target'}, f'highlights[{i}]')
    check(data['verdict'], {'label', 'summary', 'text', 'impact', 'next', 'blocker', 'diagramId', 'topics', 'progress'} | rich, 'verdict')
    for i, item in enumerate(data['verdict'].get('progress', [])):
        check(item, {'title','status','summary','evidence'}, f'verdict.progress[{i}]')
    common = {"id", "title", "subtitle", "navTitle", "summary", "kind", "outcome", "foldLabel", "collapsed", "open", "detailOnly", "folds"} | rich
    fields = {"cards": {"items"}, "checklist": {"items"}, "comparison": {"items"}, "table": {"columns", "rows"}, "flow": {"steps"}, "figure": {"figure"}, "graph": {"graphId"}, "explorer": {"scenarioIds"}, "diagram": {"diagramId"}}
    def section(value, path):
        check(value, common | fields.get(value.get("kind", "cards"), set()), path)
        if isinstance(value.get('figure'), dict):
            check(value['figure'], {'src', 'alt', 'caption', 'evidence'}, path+'.figure')
        for i, item in enumerate(value.get('items', [])):
            if isinstance(item, dict):
                check(item, {'title', 'name', 'group', 'body', 'summary', 'mission', 'gap', 'status', 'owner', 'priority', 'meta', 'scope', 'dependency', 'acceptance', 'outcome', 'category', 'modules'} | rich, f'{path}.items[{i}]')
        for i, step in enumerate(value.get('steps', [])):
            check(step, {'title','body','edge'} | rich, f'{path}.steps[{i}]')
        for i, fold in enumerate(value.get("folds", [])):
            section(fold, f"{path}.folds[{i}]")
    for i, value in enumerate(data.get("sections", [])):
        section(value, f"sections[{i}]")
    for i, value in enumerate(data.get("components", [])):
        check(value, {"id", "title", "body", "artifact", "owner", "scope", "acceptance"} | rich, f"components[{i}]")
    for i, graph in enumerate(data.get('graphs', [])):
        check(graph, {'id', 'title', 'nodes', 'edges', 'evidence'}, f'graphs[{i}]')
        for j, node in enumerate(graph['nodes']):
            check(node, {'id', 'component'}, f'graphs[{i}].nodes[{j}]')
        for j, edge in enumerate(graph.get('edges', [])):
            check(edge, {'from', 'to', 'label', 'state', 'evidence'}, f'graphs[{i}].edges[{j}]')
    for i, scenario in enumerate(data.get('scenarios', [])):
        check(scenario, {'id', 'title', 'summary', 'graphId', 'state', 'steps'} | rich, f'scenarios[{i}]')
        for j, step in enumerate(scenario.get('steps', [])):
            check(step, {'node', 'body'}, f'scenarios[{i}].steps[{j}]')
    return warnings


def image_data(path):
    if not path.is_file() or path.suffix.lower() not in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("配图需为存在的本地 SVG、PNG、JPEG 或 WebP：" + str(path))
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("单张配图不能超过 5 MB")
    if path.suffix.lower() == ".svg":
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("SVG 不允许外部实体")
        root = ET.fromstring(raw)
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1].lower() in ("script", "foreignobject"):
                raise ValueError("SVG 不能包含脚本或 foreignObject")
            for key, value in element.attrib.items():
                local = key.rsplit("}", 1)[-1].lower()
                if local.startswith("on") or (local in ("href", "src") and not value.startswith("#")) or re.search(r"url\(\s*['\"]?(?!#)", value, re.I):
                    raise ValueError("SVG 不能包含外部资源或事件处理")
    mime = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[path.suffix.lower()]
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode()


def graph_html(r, graph_id):
    graph = registry(r.data, "graphs")[graph_id]
    components = registry(r.data, "components")
    nodes = graph["nodes"]
    positions = {node["id"]: (32 + (i % 3) * 300, 65 + (i // 3) * 205) for i, node in enumerate(nodes)}
    height = 65 + ((len(nodes) - 1) // 3) * 205 + 155
    marker = r.unique_id("graph-arrow")
    esc = lambda value: html.escape(str(value), quote=True)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 {height}" font-family="sans-serif" role="group" aria-label="{esc(graph["title"])}"><defs><marker id="{marker}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#64748b"/></marker></defs>'
    relations = []
    for edge in graph.get("edges", []):
        x, y = positions[edge["from"]]; tx, ty = positions[edge["to"]]
        if y == ty:
            x1, y1, x2, y2 = x + (240 if tx > x else 0), y + 60, tx + (0 if tx > x else 240), ty + 60
        else:
            x1, y1, x2, y2 = x + 120, y + 120, tx + 120, ty
        planned = edge.get("state", "current") != "current"
        dash = ' stroke-dasharray="7 5"' if planned else ''
        label_y = y - 14 if y == ty else (y1+y2)/2
        svg += f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#64748b" fill="none" stroke-width="2"{dash} marker-end="url(#{marker})"/><text x="{(x1+x2)/2}" y="{label_y}" text-anchor="middle" font-size="14" fill="#334155" style="paint-order:stroke;stroke:white;stroke-width:5px">{esc(edge["label"])}</text>'
        a = next(n for n in nodes if n['id'] == edge['from']); b = next(n for n in nodes if n['id'] == edge['to'])
        state = {"planned": "（未来方案）", "unverified": "（待验证）"}.get(edge.get("state"), "")
        relations.append(r.text(components[a['component']]['title'] + ' → ' + components[b['component']]['title'] + '：' + edge['label'] + state) + r.refs(edge.get('evidence', [])))
    details = []
    for node in nodes:
        c = components[node["component"]]; x, y = positions[node["id"]]
        label = c['title']; chunks = [label[i:i+15] for i in range(0, len(label), 15)]
        svg += f'<g data-component="{esc(c["id"])}" data-node="{esc(node["id"])}" role="button" tabindex="0" aria-label="查看{esc(label)}职责"><rect x="{x}" y="{y}" width="240" height="120" rx="12" fill="#fff" stroke="#94a3b8" stroke-width="2"/>'
        for index, chunk in enumerate(chunks):
            svg += f'<text x="{x+14}" y="{y+30+index*24}" font-size="19" fill="#0f172a">{esc(chunk)}</text>'
        svg += f'<text x="{x+14}" y="{y+101}" font-size="13" fill="#64748b">点击查看职责与依据</text></g>'
        detail = r.card(c)
        if c.get("artifact"):
            detail += '<p><strong>引入形式：</strong>' + r.text(c['artifact']) + '</p>'
        details.append(detail)
    svg += '</svg>'
    preview = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
    return '<figure class="report-figure"><div class="diagram-scroll">' + svg + '</div><figcaption>' + r.text(graph['title']) + r.refs(graph.get('evidence', [])) + '</figcaption><button class="js-only" data-image-src="' + preview + '">放大架构图</button></figure><details class="node-index"><summary>查看全部节点职责与调用关系</summary>' + ''.join(details) + '<ul>' + ''.join('<li>'+v+'</li>' for v in relations) + '</ul></details>'


def render_native(r, section):
    kind = section['kind']
    if kind == 'figure':
        f = section['figure']; path = Path(f['src'])
        if not path.is_absolute():
            path = r.source_dir / path
        src = image_data(path)
        return f'<figure class="report-figure"><img src="{src}" alt="{html.escape(f["alt"], quote=True)}" tabindex="0" role="button"><figcaption>{r.text(f.get("caption", f["alt"]))}{r.refs(f.get("evidence", []))}</figcaption></figure>'
    if kind == 'graph':
        return graph_html(r, section['graphId'])
    scenarios = registry(r.data, 'scenarios')
    options, cards = [], []
    for sid in section['scenarioIds']:
        s = scenarios[sid]
        note = {'planned': '未来方案，尚不可作为可运行能力', 'unverified': '待验证方案'}.get(s.get('state'), '当前说明；不代表目标业务已接入')
        options.append(f'<option value="{html.escape(sid, quote=True)}">{html.escape(s["title"])}</option>')
        steps = ''.join('<li data-trace-node="'+html.escape(t['node'], quote=True)+'">'+r.text(t['body'])+'</li>' for t in s.get('steps', []))
        cards.append(f'<article data-scenario="{html.escape(sid, quote=True)}"><h3>{r.text(s["title"])}</h3><p class="scenario-state">{note}</p>{r.rich(s.get("summary", ""))}{r.rich(s)}{graph_html(r,s["graphId"])}<ol class="trace-list">{steps}</ol>' + ('<button class="js-only" data-trace-next>下一步讲解</button><span class="trace-state js-only" role="status">这是说明演示，不发送业务请求。</span>' if steps else '') + '</article>')
    return '<div class="scenario-explorer"><label class="js-only">选择说明场景 <select data-scenario-select>' + ''.join(options) + '</select></label>' + ''.join(cards) + '</div>'
