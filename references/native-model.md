# 原生组件与共享模型

在既有内容模型上增加以下可选字段；旧输入仍可生成。没有图或模式差异时不要建立空注册表。

- 默认 `readingMode: focus`，导航在主区切换，显示该章完整范围。`schemaVersion: 2` 保留为模型标识。
- `defaultView: brief | full` 仅作用于 `readingMode: continuous`。旧输入默认完整，schemaVersion 2 的 continuous 默认摘要。资料全部内嵌。
- `sections[].detailOnly: true` 只在 continuous 的摘要视图收起详细主体。focus、章节浮层、无脚本和打印保留主体。
- `components[]`：`{id,title,body,artifact?,owner?,scope?,acceptance?,evidence?}`。组件事实只维护一次，图节点与节点详情共享。
- `graphs[]`：`{id,title,nodes:[{id,component}],edges:[{from,to,label,state?}]}`。边的 `label` 说明调用机制；`state` 为 `current`、`planned` 或 `unverified`。节点和边引用必须存在。图使用三列基础网格，适合小型拓扑；复杂拓扑先生成静态 SVG 再引用。
- `scenarios[]`：`{id,title,summary,graphId,state?,steps?:[{node,body}],evidence?}`。每个场景引用已登记图，步骤只能引用该图节点。只有预先定义且通过引用校验的场景可以选择；需要复杂参数约束时先建立有效场景，不能用自由组合伪装已支持。

三种原生章节：

```json
{"id":"picture","title":"现有配图","kind":"figure","figure":{"src":"assets/diagram.svg","alt":"组件调用方向","caption":"已核验图形；仍需按来源判断范围。","evidence":["来源一"]}}
```

```json
{"id":"architecture","title":"运行关系","kind":"graph","graphId":"remote"}
```

```json
{"id":"modes","title":"选择场景","kind":"explorer","scenarioIds":["remote-use","local-use"]}
```

图片支持 SVG、PNG、JPEG 和 WebP，单张上限 5 MB，路径相对输入 JSON 解析，也可显式使用已获授权的本地绝对路径。生成器会读取并内嵌，不加载远程资源。SVG 不能带脚本、外部资源或 foreignObject。

正文中图节点支持鼠标、轻触和键盘打开职责及依据；图下完整节点与边清单支持静态阅读。场景切换仅改变说明，不执行业务。未来方案始终显示未实现边界。

continuous 在同一 HTML 中提供摘要／完整阅读，focus 直接切换完整主题，章节结构不变。打印展开全部场景和节点清单，不只打印当前选项。无脚本显示所有场景，隐藏不能使用的控件。不要在摘要中隐藏核心结论、阻断或必须执行的动作。

所有正文与新组件的证据仍引用同一登记表。`--strict` 拒绝未识别字段；默认仅警告以兼容旧输入。不要将新增字段仅写入 JSON 后就宣布已呈现。

当前不包含任意拓扑智能布线、自动事实采集、业务模拟执行或宿主自动验收。生成器版本、输入模型和浏览器观察应分别记录。
