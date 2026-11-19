"""Small offline change diagrams. One model supplies before, change and after views."""
from __future__ import annotations

import html
import re
import unicodedata
from collections import defaultdict, deque


SHAPES = {"process": "处理／组件", "decision": "判断／分支", "terminator": "开始／结束", "store": "数据存储", "data": "输入／输出"}
CHANGES = {"unchanged": "保留", "added": "＋ 新增", "removed": "－ 移除", "modified": "↻ 修改"}
STATES = {"before": "改前", "change": "变更", "after": "改后"}
COLORS = {"unchanged": "#64748b", "added": "#15803d", "removed": "#b42318", "modified": "#b45309"}
EDGE_SYMBOLS = {"unchanged": "", "added": "+ ", "removed": "− ", "modified": "↻ "}
NODE_WIDTH, GAP_X, GAP_Y, MARGIN = 132, 88, 60, 22


def _esc(value):
    return html.escape(str(value), quote=True)


def _valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"[\w-]+", value)


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _ranks(nodes, edges):
    outgoing, indegree = defaultdict(list), {n["id"]: 0 for n in nodes}
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    queue = deque(n["id"] for n in nodes if not indegree[n["id"]])
    ranks, visited = {n["id"]: 0 for n in nodes}, 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in outgoing[current]:
            ranks[target] = max(ranks[target], ranks[current] + 1)
            indegree[target] -= 1
            if not indegree[target]:
                queue.append(target)
    return ranks, visited == len(nodes)


def validate_diagrams(data):
    diagrams = data.get("diagrams", [])
    if not isinstance(diagrams, list):
        raise ValueError("diagrams 必须是数组")
    diagram_ids = set()
    evidence_ids = {entry["id"] for entry in data.get("evidence", []) if isinstance(entry, dict) and "id" in entry}

    def evidence_refs(item, where):
        refs = item.get("evidence", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ValueError(where + ".evidence 必须是文本数组")
        if any(ref not in evidence_ids for ref in refs):
            raise ValueError(where + " 引用了不存在的证据")

    for diagram in diagrams:
        if not isinstance(diagram, dict) or not _valid_id(diagram.get("id")) or diagram["id"] in diagram_ids:
            raise ValueError("diagram.id 必须唯一且仅含字母、数字、中文、下划线或短横线")
        diagram_ids.add(diagram["id"])
        if not _nonempty(diagram.get("title")):
            raise ValueError("diagram.title 必须是非空文本")
        if diagram.get("kind", "architecture") not in ("architecture", "flow", "tree"):
            raise ValueError("diagram.kind 应为 architecture、flow 或 tree")
        if diagram.get("direction", "LR") not in ("LR", "TB"):
            raise ValueError("diagram.direction 应为 LR 或 TB")
        if "note" in diagram and not isinstance(diagram["note"], str):
            raise ValueError("diagram.note 必须是文本")
        evidence_refs(diagram, "diagram")
        nodes, edges, groups = diagram.get("nodes"), diagram.get("edges", []), diagram.get("groups", [])
        if not isinstance(nodes, list) or not nodes or not isinstance(edges, list) or not isinstance(groups, list):
            raise ValueError("diagram 需要非空 nodes；edges、groups 必须是数组")
        node_ids, cells = set(), set()
        for node in nodes:
            if not isinstance(node, dict) or not _valid_id(node.get("id")) or node["id"] in node_ids:
                raise ValueError("diagram 节点 id 必须非空且唯一")
            node_ids.add(node["id"])
            if not _nonempty(node.get("label")):
                raise ValueError("diagram 节点 label 必须是非空文本")
            if node.get("shape", "process") not in SHAPES or node.get("change", "unchanged") not in CHANGES:
                raise ValueError("diagram 节点 shape 或 change 无效")
            if "beforeLabel" in node and not _nonempty(node["beforeLabel"]):
                raise ValueError("diagram 节点 beforeLabel 必须是非空文本")
            if node.get("beforeLabel", node["label"]) != node["label"] and node.get("change", "unchanged") != "modified":
                raise ValueError("前后标签不同的节点必须标记 change: modified")
            if "column" in node or "row" in node:
                for key in ("column", "row"):
                    if type(node.get(key)) is not int or node[key] < 0 or node[key] > 30:
                        raise ValueError("显式布局需同时填写 0–30 的整数 column、row")
                cell = (node["column"], node["row"])
                if cell in cells:
                    raise ValueError("diagram 显式布局不能让两个节点占同一格")
                cells.add(cell)
            evidence_refs(node, "diagram 节点")
        if "outcomes" in diagram:
            outcomes = diagram["outcomes"]
            where = f"diagram {diagram['id']}.outcomes"
            if not isinstance(outcomes, dict) or outcomes.keys() != {"before", "after"}:
                raise ValueError(where + " 必须同时填写 before、after 的结果节点 ID")
            changes = {node["id"]: node.get("change", "unchanged") for node in nodes}
            for state, node_id in outcomes.items():
                if not isinstance(node_id, str) or node_id not in changes:
                    raise ValueError(f"{where}.{state} 必须引用存在的结果节点")
                if not _visible(changes[node_id], state):
                    raise ValueError(f"{where}.{state} 的结果节点 {node_id} 在{STATES[state]}视图不可见")
        for edge in edges:
            if not isinstance(edge, dict) or edge.get("from") not in node_ids or edge.get("to") not in node_ids:
                raise ValueError("diagram 边必须引用存在的 from、to 节点")
            if edge["from"] == edge["to"]:
                raise ValueError("diagram 暂不支持自环；请拆为可读步骤")
            if not _nonempty(edge.get("label")):
                raise ValueError("diagram 边 label 必须解释关系或调用机制")
            if edge.get("change", "unchanged") not in CHANGES or edge.get("style", "solid") not in ("solid", "dashed"):
                raise ValueError("diagram 边 change 或 style 无效")
            evidence_refs(edge, "diagram 边")
        _, acyclic = _ranks(nodes, edges)
        if not acyclic and not all("column" in node for node in nodes):
            raise ValueError("含循环的 diagram 需为每个节点提供 column、row；自动布局仅支持小型有向无环图")
        if any("column" in node for node in nodes) and not all("column" in node for node in nodes):
            raise ValueError("显式布局时每个节点都需填写 column、row")
        group_ids, grouped = set(), set()
        for group in groups:
            if not isinstance(group, dict) or not _valid_id(group.get("id")) or group["id"] in group_ids or not _nonempty(group.get("label")):
                raise ValueError("diagram 分组需唯一 id 和非空 label")
            group_ids.add(group["id"])
            members = group.get("nodes")
            if not isinstance(members, list) or not members or any(not isinstance(member, str) for member in members) or len(members) != len(set(members)) or any(member not in node_ids for member in members):
                raise ValueError("diagram 分组 nodes 需不重复且引用存在的节点")
            if grouped.intersection(members):
                raise ValueError("diagram 节点只能属于一个分组")
            grouped.update(members)
        # A boundary must not accidentally contain an unrelated node.
        if groups:
            _, slots, _, _, _, _ = _layout(diagram)
            for group in groups:
                cells = [slots[key] for key in group["nodes"]]
                left, right = min(c[0] for c in cells), max(c[0] for c in cells)
                top, bottom = min(c[1] for c in cells), max(c[1] for c in cells)
                if any(left <= cell[0] <= right and top <= cell[1] <= bottom for key, cell in slots.items() if key not in group["nodes"]):
                    raise ValueError("diagram 分组背景会包住未登记的节点；请调整分组或显式布局")

    def sections(value):
        if isinstance(value, dict):
            if value.get("kind") == "diagram" and value.get("diagramId") not in diagram_ids:
                raise ValueError("章节引用了不存在的 diagramId")
            for fold in value.get("folds", []):
                sections(fold)
    for section in data.get("sections", []):
        sections(section)
    verdict_id = data.get("verdict", {}).get("diagramId")
    if verdict_id is not None and verdict_id not in diagram_ids:
        raise ValueError("verdict 引用了不存在的 diagramId")


def diagram_unknown_fields(data):
    warnings = []
    def check(item, allowed, where):
        for key in item.keys() - allowed:
            warnings.append(where + "." + key + "：未识别字段，不保证显示在正文")
    for i, diagram in enumerate(data.get("diagrams", [])):
        path = f"diagrams[{i}]"
        check(diagram, {"id", "title", "kind", "direction", "nodes", "edges", "groups", "note", "evidence", "outcomes"}, path)
        for j, node in enumerate(diagram["nodes"]):
            check(node, {"id", "label", "shape", "change", "beforeLabel", "evidence", "column", "row"}, f"{path}.nodes[{j}]")
        for j, edge in enumerate(diagram.get("edges", [])):
            check(edge, {"from", "to", "label", "change", "style", "evidence"}, f"{path}.edges[{j}]")
        for j, group in enumerate(diagram.get("groups", [])):
            check(group, {"id", "label", "nodes"}, f"{path}.groups[{j}]")
    return warnings


def _wrap(value, units):
    lines, line, length = [], "", 0
    for char in value:
        if char == "\n":
            lines.append(line)
            line, length = "", 0
            continue
        size = 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
        if line and length + size > units:
            lines.append(line)
            line, length = "", 0
        line += char
        length += size
    if line or not lines:
        lines.append(line)
    return lines


def _parallel_offsets(diagram, slots):
    """Separate two requests between the same adjacent, horizontal units."""
    pairs = defaultdict(list)
    for index, edge in enumerate(diagram.get('edges', [])):
        pairs[(edge['from'], edge['to'])].append(index)
    offsets = {}
    for (source, target), indices in pairs.items():
        a, b = slots[source], slots[target]
        if len(indices) == 2 and a[1] == b[1] and abs(a[0] - b[0]) == 1:
            offsets.update(zip(indices, (-18, 18)))
    return offsets


def _layout(diagram):
    nodes, edges = diagram["nodes"], diagram.get("edges", [])
    tb = diagram.get("direction", "LR") == "TB"
    ranks, _ = _ranks(nodes, edges)
    slots, rank_sizes = {}, defaultdict(int)
    for node in nodes:
        rank = ranks[node["id"]]
        if "column" in node:
            cell = node["column"], node["row"]
        else:
            cell = (rank_sizes[rank], rank) if tb else (rank, rank_sizes[rank])
            rank_sizes[rank] += 1
        slots[node["id"]] = cell
    height = 44
    for node in nodes:
        diamond = node.get("shape", "process") == "decision"
        count = max(len(_wrap(label, 14 if diamond else 18)) for label in (node["label"], node.get("beforeLabel", node["label"])))
        height = max(height, 64 if diamond else 44, count * 15 * (2 if diamond else 1) + 20)
    # Long or return edges use a perimeter lane, never a line through a node.
    perimeter_indices = []
    for index, edge in enumerate(edges):
        a, b = slots[edge["from"]], slots[edge["to"]]
        if (a[0] == b[0] and abs(a[1]-b[1]) == 1) or (a[1] == b[1] and abs(a[0]-b[0]) == 1):
            continue  # Adjacent branch exits can connect directly in either orientation.
        if (b[1] - a[1] if tb else b[0] - a[0]) != 1:
            perimeter_indices.append(index)
    perimeter = {}
    cursor = 24
    if not tb:
        for index in perimeter_indices:
            edge = edges[index]
            label = CHANGES.get(edge.get("change", "unchanged"), "") + "：" + edge["label"]
            band = max(48, len(_wrap(label, 16)) * 14 + 22)
            perimeter[index] = cursor + band/2
            cursor += band
    parallel = _parallel_offsets(diagram, slots)
    parallel_pad = max((len(_wrap(EDGE_SYMBOLS[edges[index].get('change', 'unchanged')] + edges[index]['label'], 12)) * 14 + 8 for index in parallel), default=0)
    top = (38 if tb or not perimeter else cursor + 28) + parallel_pad
    positions = {key: (MARGIN + column * (NODE_WIDTH + GAP_X), top + row * (height + GAP_Y)) for key, (column, row) in slots.items()}
    width = max(x for x, _ in positions.values()) + NODE_WIDTH + MARGIN
    if tb:
        for index in perimeter_indices:
            perimeter[index] = width + 56
            width += 128
    canvas_height = max(y for _, y in positions.values()) + height + 24 + parallel_pad
    return positions, slots, height, width, canvas_height, perimeter


def _shape(shape, x, y, width, height):
    if shape == "decision":
        return f'<polygon points="{x+width/2},{y} {x+width},{y+height/2} {x+width/2},{y+height} {x},{y+height/2}"/>'
    if shape == "data":
        return f'<polygon points="{x+18},{y} {x+width},{y} {x+width-18},{y+height} {x},{y+height}"/>'
    if shape == "store":
        cap = min(12, height/5)
        return f'<path d="M{x} {y+cap}a{width/2} {cap} 0 0 1 {width} 0v{height-2*cap}a{width/2} {cap} 0 0 1 -{width} 0Z"/><ellipse class="store-top" cx="{x+width/2}" cy="{y+cap}" rx="{width/2}" ry="{cap}"/>'
    radius = min(height / 2, width / 2) if shape == "terminator" else 6
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}"/>'


def _node_label(node, state):
    return node.get("beforeLabel", node["label"]) if state == "before" else node["label"]


def _visible(change, state):
    return not (state == "before" and change == "added" or state == "after" and change == "removed")


def _svg_scene(r, diagram, state, prefix, layout, scene_title=None):
    positions, slots, node_height, width, height, perimeter = layout
    parallel = _parallel_offsets(diagram, slots)
    tb = diagram.get("direction", "LR") == "TB"
    nodes = [node for node in diagram["nodes"] if _visible(node.get("change", "unchanged"), state)]
    node_ids = {node["id"] for node in nodes}
    title_id = r.unique_id(prefix + "-title")
    description_id = r.unique_id(prefix + "-description")
    markers = {change: r.unique_id(prefix + "-" + change) for change in COLORS}
    comparison = any(item.get('change','unchanged') != 'unchanged' for item in [*diagram['nodes'],*diagram.get('edges',[])])
    description = (diagram['note'].rstrip('。')+'。' if diagram.get('note') else '') + "节点：" + "、".join(_node_label(node, state) for node in nodes)
    descriptions = [edge for edge in diagram.get("edges", []) if edge["from"] in node_ids and edge["to"] in node_ids and _visible(edge.get("change", "unchanged"), state)]
    labels = {node["id"]: _node_label(node, state) for node in nodes}
    if descriptions:
        description += "。关系：" + "；".join(labels[edge["from"]] + " → " + labels[edge["to"]] + "（" + edge["label"] + "）" for edge in descriptions)
    result = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="{title_id}" aria-describedby="{description_id}" style="--diagram-width:{width}px"><title id="{title_id}">{_esc(diagram["title"])} · {_esc(scene_title or STATES[state])}</title><desc id="{description_id}">{_esc(description)}</desc><defs>']
    for change, color in COLORS.items():
        result.append(f'<marker id="{markers[change]}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L8 4L0 8Z" fill="{color}"/></marker>')
    result.append("</defs>")
    for group in diagram.get("groups", []):
        if not node_ids.intersection(group["nodes"]):
            continue
        points = [positions[key] for key in group["nodes"]]
        x, y = min(p[0] for p in points) - 18, min(p[1] for p in points) - 34
        box_width, box_height = max(p[0] for p in points) + NODE_WIDTH + 18 - x, max(p[1] for p in points) + node_height + 18 - y
        result.append(f'<g class="change-diagram-group"><rect x="{x}" y="{y}" width="{box_width}" height="{box_height}" rx="8"/><text x="{x+12}" y="{y+20}">{_esc(group["label"])}</text></g>')
    for index, edge in enumerate(diagram.get("edges", [])):
        if edge["from"] not in node_ids or edge["to"] not in node_ids or not _visible(edge.get("change", "unchanged"), state):
            continue
        ax, ay = positions[edge["from"]]
        bx, by = positions[edge["to"]]
        change = edge.get("change", "unchanged")
        appearance = change if state == "change" else "unchanged"
        special = index in perimeter
        a, b = slots[edge['from']], slots[edge['to']]
        if index in parallel:
            sy = ty = ay + node_height / 2
            sx, tx = (ax+NODE_WIDTH, bx) if b[0] > a[0] else (ax, bx+NODE_WIDTH)
            offset = parallel[index]
            label_x = (sx + tx) / 2
            path = f'M{sx} {sy}Q{label_x} {sy+offset*2} {tx} {ty}'
            label_y = sy + offset + (-8 if offset < 0 else 18)
        elif a[0] == b[0] and abs(a[1]-b[1]) == 1:
            sx = tx = ax + NODE_WIDTH/2
            sy, ty = (ay+node_height, by) if b[1] > a[1] else (ay, by+node_height)
            path = f'M{sx} {sy}V{ty}'
            label_x, label_y = sx + 62, (sy+ty)/2
        elif a[1] == b[1] and abs(a[0]-b[0]) == 1:
            sy = ty = ay+node_height/2
            sx, tx = (ax+NODE_WIDTH, bx) if b[0] > a[0] else (ax, bx+NODE_WIDTH)
            path = f'M{sx} {sy}H{tx}'
            label_x, label_y = (sx+tx)/2, sy-13
        elif tb:
            sx, sy, tx, ty = ax + NODE_WIDTH/2, ay + node_height, bx + NODE_WIDTH/2, by
            if special:
                lane = perimeter[index]
                path = f"M{sx} {sy}V{sy+24}H{lane}V{ty-24}H{tx}V{ty}"
                label_x, label_y = lane, (sy + ty) / 2
            else:
                middle = (sy + ty) / 2
                path = f"M{sx} {sy}V{middle}H{tx}V{ty}"
                label_x, label_y = (sx + tx)/2, middle - 13
        else:
            sx, sy, tx, ty = ax + NODE_WIDTH, ay + node_height/2, bx, by + node_height/2
            if special:
                lane = perimeter[index]
                path = f"M{sx} {sy}H{sx+22}V{lane}H{tx-22}V{ty}H{tx}"
                label_x, label_y = (sx + tx) / 2, lane - 7
            else:
                middle = (sx + tx) / 2
                path = f"M{sx} {sy}H{middle}V{ty}H{tx}"
                label_x, label_y = middle, (sy + ty)/2 - 13
        label = (EDGE_SYMBOLS[change] if state == "change" else "") + edge["label"]
        label_lines = _wrap(label, 16 if special else 12)
        label_width = max(sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in line) for line in label_lines) * 6.1 + 10
        label_y -= (len(label_lines)-1) * 7
        result.append(f'<g class="change-diagram-edge state-{appearance} edge-{edge.get("style", "solid")}" data-edge-from="{_esc(edge["from"])}" data-edge-to="{_esc(edge["to"])}" data-change="{change}"><title>{_esc(label)}</title><path d="{path}" marker-end="url(#{markers[appearance]})"/><rect class="edge-label-bg" x="{label_x-label_width/2}" y="{label_y-12}" width="{label_width}" height="{len(label_lines)*14+5}" rx="3"/><text x="{label_x}" y="{label_y}" text-anchor="middle">')
        result.extend(f'<tspan x="{label_x}" dy="{0 if i == 0 else 14}">{_esc(line)}</tspan>' for i, line in enumerate(label_lines))
        result.append("</text></g>")
    for node in nodes:
        x, y = positions[node["id"]]
        shape, change = node.get("shape", "process"), node.get("change", "unchanged")
        appearance = change if state == "change" else "unchanged"
        label = _node_label(node, state)
        lines = _wrap(label, 14 if shape == "decision" else 18)
        change_note = node.get('beforeLabel', label) + ' → ' + node['label'] if change == 'modified' else label
        state_note = '；'+CHANGES[change] if comparison else ''
        result.append(f'<g class="change-diagram-node state-{appearance}" data-node-id="{_esc(node["id"])}" data-change="{change}" data-shape="{shape}"><title>{_esc(change_note)}；{SHAPES[shape]}{state_note}</title>')
        result.append(_shape(shape, x, y, NODE_WIDTH, node_height))
        first_y = y + node_height/2 - (len(lines)-1)*7.5 + 4.5
        result.append(f'<text x="{x+NODE_WIDTH/2}" y="{first_y}" text-anchor="middle">')
        result.extend(f'<tspan x="{x+NODE_WIDTH/2}" dy="{0 if i == 0 else 15}">{_esc(line)}</tspan>' for i, line in enumerate(lines))
        result.append("</text>")
        if state == "change" and change != "unchanged":
            badge = {'added':'+','removed':'−','modified':'↻'}[change]
            result.append(f'<g class="node-change-badge"><rect x="{x+NODE_WIDTH-9}" y="{y-8}" width="16" height="16" rx="8"/><text x="{x+NODE_WIDTH-1}" y="{y+4}" text-anchor="middle">{badge}</text></g>')
        result.append("</g>")
    if not nodes:
        message = "改前尚无此结构" if state == "before" else "改后不再保留此结构"
        result.append(f'<text class="diagram-empty" x="{width/2}" y="{height/2}" text-anchor="middle">{message}</text>')
    result.append("</svg>")
    return "".join(result)


def _legend(diagram):
    used_shapes = {node.get("shape", "process") for node in diagram["nodes"]}
    used_changes = {entry.get("change", "unchanged") for entry in [*diagram["nodes"], *diagram.get("edges", [])]}
    if used_changes == {'unchanged'}:
        used_changes = set()  # A static or planned structure has no comparison status.
    used_styles = {edge.get("style", "solid") for edge in diagram.get("edges", [])}
    items = []
    for shape, label in SHAPES.items():
        if shape in used_shapes:
            icon = _shape(shape, 2, 2, 28, 18)
            items.append(f'<span data-legend-shape="{shape}"><svg viewBox="0 0 32 24" width="32" height="24" aria-hidden="true">{icon}</svg>{label}</span>')
    for change, label in CHANGES.items():
        if change in used_changes:
            items.append(f'<span class="state-key state-{change}" data-legend-change="{change}">{label}</span>')
    for style in ("solid", "dashed"):
        if style in used_styles:
            dash = ' stroke-dasharray="4 3"' if style == "dashed" else ""
            label = "虚线箭头：具体关系见边标签" if style == "dashed" else "实线箭头：关系／调用方向"
            items.append(f'<span data-legend-edge="{style}"><svg viewBox="0 0 32 24" width="32" height="24" aria-hidden="true"><path d="M2 12H29M23 7L29 12L23 17" fill="none"{dash}/></svg>{label}</span>')
    if diagram.get("groups"):
        items.append('<span data-legend-group><svg viewBox="0 0 32 24" width="32" height="24" aria-hidden="true"><rect class="legend-group" x="2" y="3" width="28" height="18" rx="3"/></svg>背景框：同一边界／分组</span>')
    return '<details class="change-diagram-legend" open><summary>图例</summary><div>' + "".join(items) + '</div></details>'


def render_diagram(r, diagram_id):
    diagram = next(item for item in r.data.get("diagrams", []) if item["id"] == diagram_id)
    changed = any(item.get('change', 'unchanged') != 'unchanged' for item in [*diagram['nodes'], *diagram.get('edges', [])])
    states = STATES if changed else {'after': '结构'}
    instance = r.unique_id("change-diagram-" + diagram_id)
    title_id = r.unique_id(instance + "-heading")
    scene_ids = {state: r.unique_id(instance + "-" + state) for state in states}
    cited = list(dict.fromkeys(ref for entry in [diagram, *diagram['nodes'], *diagram.get('edges', [])] for ref in entry.get('evidence', [])))
    result = [f'<figure class="change-diagram" id="{instance}" aria-labelledby="{title_id}" data-change-diagram><header class="change-diagram-header"><strong id="{title_id}">{r.text(diagram["title"])}{r.refs(cited)}</strong>']
    if changed:
        used = {item.get('change') for item in [*diagram['nodes'], *diagram.get('edges', [])]}
        key = ' · '.join(CHANGES[state] for state in ('added','removed','modified') if state in used)
        result.append('<span class="diagram-change-key">'+_esc(key)+'</span>')
        result.append('<div class="diagram-state-controls" role="group" aria-label="选择变化视图">')
        for state, title in states.items():
            result.append(f'<button type="button" data-diagram-view="{state}" aria-pressed="{"true" if state == "change" else "false"}" aria-controls="{scene_ids[state]}">{title}</button>')
        result.append('</div>')
    result.append('</header>')
    if diagram.get("note"):
        result.append('<p class="diagram-note">' + r.text(diagram["note"]) + '</p>')
    result.append('<p class="diagram-scroll-hint">图较宽时可在图内左右滚动。</p>')
    layout = _layout(diagram)
    for state, title in states.items():
        result.append(f'<section class="diagram-scene" id="{scene_ids[state]}" data-diagram-state="{state}" aria-label="{title}"><h4>{title}</h4><div class="change-diagram-canvas" tabindex="0" role="region" aria-label="{_esc(diagram["title"])} · {title}">')
        result.append(_svg_scene(r, diagram, state, instance + "-" + state, layout, title))
        result.append("</div></section>")
    result.append(_legend(diagram))
    result.append('</figure>')
    return "".join(result)
