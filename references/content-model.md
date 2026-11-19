# 内容模型

生成器仍兼容旧字段。左栏放报告主题、短目录与可选全局重点，主区切换所选主题，第一块是“核心结论”。范围、背景和完整来源统一归“附录”。无脚本和打印保留全部内容。变化图见[图解模型](diagram-model.md)，图片、共享组件和场景探索见[原生模型](native-model.md)。

生成器只依赖 Python 标准库，输入为 UTF-8 JSON，输出为一个内联样式和脚本的 HTML。内部字段名保持英文，正文和界面默认中文。旧版数据无需改名即可生成。

## 基本字段

| 字段 | 要求／用途 |
| --- | --- |
| `title`、`generatedAt` | 必填非空字符串；标题和生成时间 |
| `subtitle`、`audience`、`scope` | 可选；副标题、读者、固定版本／环境等范围数组 |
| `reportType` | `audit`（默认）、`brief` 或 `handoff`；展示为“审计评估”“技术方案简报”“场景交接” |
| `readingMode` | `focus`（默认）：目录切换主区；`continuous`：旧连续正文与章节浮层。仅屏幕且脚本可用时隐藏其他内容块；打印始终全部显示 |
| `verdict` | 必填 `label`、`summary`；可选 `impact`、`next`、`blocker` 和 `diagramId`（图优先）。结论、影响、下一步与限制应短且不重复；阅读逻辑可用 `text` 或 `bullets` 简述 |
| `findings`、`evidence` | 必填数组，允许为空；简报与交接不必制造问题 |
| `metrics` | 可选 `{label,value,note}` 数组；只放有意义的实测统计，不自动制造完成率 |
| `highlights` | 可选 `{label,value,target?}` 数组；左栏常驻的少量高价值重点，通常不超过 3 项。target 是实际正文主题 ID 或 overview；不是状态推断，不用它填满空白 |

核心结论需要条理时，`verdict.topics: ["integration","effort"]` 按顺序引用有非空 `summary` 的正文主题；生成器复用标题和一句话 summary，提供跳转，不另维护副本。先把每个 summary 写成简短结论；只有一个简单主题时无需此字段。

进度报告可用 `verdict.progress: [{"title":"正式接入","status":"待实施","summary":"先完成第一条验收链。","evidence":["证据一"]}]`。title 与 status 必填，summary 和 evidence 可选。观察状态清楚保留“历史通过、待实施、待验收、未知”等含义，不从文件、HTTP200或测试总数猜完成；列表是事实陈述，不提供可随手勾选成“完成”的控件。总判断、模块摘要、进度与下一步互相补充，不重复写四遍相同意思。

```json
{"verdict":{"label":"推荐保留单进程接入","summary":"现有入口可继续使用，不需要新增服务。","impact":"现场只维护一个进程，升级和排障路径更短。","next":"先固定依赖版本，再跑成功和失败场景。","blocker":"中断恢复尚未真实验证。"}}
```

## 问题与证据

`findings[]`：`id`、`title`、`status`、`summary` 必填，`priority`、`owner`、`assessment[]`、`actions[]` 可选。`evidence[]` 为证据编号数组；没有证据时必须写非空 `evidenceGap`。`factKind` 可标 `current`、`historical`、`inference`、`unverified` 或 `planned`，显示中文。

`evidence[]`：`id`、`level`、`source`、`summary` 必填；`label` 可提供简短来源名，原 source 保留完整出处。`date`、`scope`、`limitation`、`factKind` 可选。编号不得重复，悬空引用阻止生成。

原项入口可选字段：`href` 是安全的文档／网页链接，`locator` 是文件行、记录号、方法名、日期等具体定位；`accessNote` 说明权限或无法跳转的原因。没有 `href` 时清单显示来源、定位及访问说明，旧数据仍可用。`items[]` 支持字符串或普通条目对象（含 `body`、`status`、`links` 等），用于列出一组验证的具体项目和结果。不要用总数替代逐项凭证。

正文可写 `"权限撤回后拒绝调用。[[证据一]]"`，角标紧跟具体断言；反引号代码和 URL 原文不解析。也兼容 `evidence: ["证据一"]`，在条目末尾引用。编号按登记顺序稳定，显示右上 `[1]`，悬停或聚焦简述，点击到本节底部。focus 的来源区只列编号和 label／source 链接，不重复摘要、定位、日期和限制；完整登记表及 items 在附录保留一份。有 href 直达原项，否则转向附录详情。同一来源跨节编号相同。continuous 仍指向旧核验清单。

focus 中仅登记 evidence 不自动增加四层证据章节；显式 `evidenceLayers` 才生成。`evidenceLayers[].evidence[]` 可选择同层记录，省略则列出该层全部记录，不能借用其他层通过结果。缺失编号或跨层引用阻止生成。复杂证据清单仍可显式使用，不能把“已登记”当成“已验证”。

```json
{"id":"证据一","level":"SOURCE_BUILD","source":"固定版本测试记录","summary":"入口校验的两项测试通过","href":"./test-results.txt","locator":"记录中的成功与无效输入检查","items":[{"title":"成功路径","body":"结果字段与输入一致","status":"verified"},{"title":"无效输入","body":"拒绝缺失字段","status":"verified"}],"limitation":"不证明业务数据已经入库"}
```

证据层：`SOURCE_BUILD` → 源码与构建，`RUNTIME_UI` → 运行与交互，`DATA_BUSINESS` → 数据与业务，`RELEASE_CUTOVER` → 发布与切流。支持旧版自定义 `level`，建议用中文；未知英文层名显示“其他证据”，原始值在资料 JSON 保留。

`evidenceLayers[]` 可显式写 `{level,status,reason}`；`status` 支持 `verified`、`not_run`、`not_applicable`、`unknown` 或中文。只有分层本身会改变判断时才填写；普通简报可用描述性核验链接。登记证据不等于验收通过。

兼容状态：`implemented`／`complete` → 已实现／已完成，`partial` → 部分实现，`drift` → 存在偏离，`missing` → 未实现，`unverified` → 待验证；中文状态原样保留。未知英文状态显示“待说明”，可通过 `statusLabels` 对象提供中文含义。证据类型同理，通过 `factLabels` 覆盖自定义分类；不要猜含义。

## 正文章节

`sections[]`：`id`、短主标题 `title`、可选问题式 `subtitle`、一句话结论 `summary` 和 `kind`。focus 的副标题在主区标题下常显，用较小字号和弱色；同一 subtitle 同时放在对应目录项旁提示，悬停、聚焦或轻触可看，不另维护副本。提示按钮和导航链接并列，不能嵌套。气泡保持在视口内，不被侧栏裁切；主标题没有问号控件。无脚本、打印及 continuous 同样保留弱副标题行。目录仅列顶层 title，旧长标题可用 navTitle 指定短名；不要手写编号。

例如 `{"id":"effort","title":"工时","subtitle":"分几步、要多久？","summary":"先接通主链，再展开迁移。"}`。类型包括：

- `cards`（默认）／`checklist`：`items[]` 为字符串，或 `{title,body,meta,status,owner,acceptance,dependency,modules,outcome,scope}`。责任与验收字段完整展示。
- `table`：`columns[]` 为非空中文表头数组，`rows[]` 为等长单元格数组。单元格支持字符串、数字或下述段落列表对象；避免长段落。
- `flow`：`steps[]` 为 `{title,body,edge}`。`edge` 为到下一步的调用方式；最后一步不应带出口标签。步骤顺序与原始契约一致。
- `comparison`：`items[]` 为 2 至 4 组同维度内容，结构同普通条目；可用 `outcome` 描述它们的共同结果或取舍。这是并列关系图，不生成评分。
- `diagram`：`diagramId` 指向全局 `diagrams[]`；架构、流程与目录关系及变化规范见[图解模型](diagram-model.md)。

### 段落、列表与链接

条目、步骤、结论、章节与附录都可添加 `paragraphs[]`、`bullets[]`、`links[]`。`body` 仍支持字符串；单换行保留停顿，双换行分段。表格单元格也可写为 `{text,paragraphs,bullets,links}`，替代长字符串。所有内容安全转义，不支持原始 HTML。

```json
{"paragraphs": ["先说明结果。", "再说明限制。"], "bullets": ["逐项核对。"], "links": [{"label": "打开原始报告", "href": "../original.html"}]}
```

显式链接必须包含非空 `label`、`href`。允许不带凭据的 HTTP／HTTPS、章节锚点、本地文档相对路径及本地 `file` URI；相对路径与 file 路径仅支持 HTML、PDF、Markdown、文本、JSON、常见图片等文档后缀。禁止命令协议、脚本 URL、协议相对地址和可执行文件。文件不会被生成器读取，存在性及分享后的可达性由报告作者核对。公开示例不要包含本机路径。

正文中的裸 HTTP／HTTPS 地址自动生成链接；末尾中文标点不计入地址。外部网页在新标签页打开，附带 `noopener noreferrer`；离线阅读正文不需要访问这些网址。`sources[]` 可额外带 `href`，配合 `label` 生成描述性材料入口。

链接检查覆盖用户信息和常见敏感参数，例如 `access_token`、`password`、`api_key`；无法猜测任意参数的业务含义。被排除的裸网址保持纯文本，显式链接报错。报告内容仍需在输入前脱敏，此检查不能替代完整的公开内容审查。

### 正文内折叠

`sections[].folds[]` 复用同样的 `title`、`summary`、`kind` 和内容字段，放在本章节主体之后。`open: true` 可默认展开，否则收起；详情嵌套最多两层。章节 `collapsed: true` 将主体整体收起，可用 `foldLabel` 说明内容；该章标题和摘要仍可见，适用于补充清单而非核心结论。

```json
{"id":"contracts","title":"职责与契约","summary":"先看职责摘要。","items":[{"title":"集成组","body":"关联请求与结果。"}],"folds":[{"title":"查看字段与验收明细","kind":"table","columns":["字段","含义"],"rows":[["taskId","关联请求与回调"]]}]}
```

无脚本时原生折叠仍可用。导航展开该章主体，不展开全部补充块；打印统一展开并恢复开闭状态。continuous 的摘要／完整视图可提供全局详情控制；focus 主区呈现对应范围，不用全局摘要隐藏该章内容。完整例子见[专注阅读示例](../examples/focus-changes.json)。

`sections` 按输入顺序显示在台账之前，无问题不生成台账。focus 的目录只列顶层；continuous 保留各层链接与 detailOnly 摘要视图。统一编号章与详情，正文和打印编号相同，锚点避开用户章节 ID。深链接打开所属章节及必要父级，浏览器返回可恢复位置；章节序号不表示阅读完成。

其他兼容字段：

- `responsibilities[]`：`{group,mission,modules,acceptance,owner}`，生成“职责与验收”。
- `modules[]`：`{name,category,priority,owner,gap,outcome,acceptance,dependency}`；`required`／`本次必做` 与 `future`／`后续预留` 分组，其余显示“其他模块”。
- `appendices[]`：`{title,body,items}`，默认折叠，打印展开。
- `sources[]`：`{label,ref,note}`，生成来源索引。
- `glossary[]`：`{term,full?,explanation,aliases?,original?,source?,scopeNote?,evidence?,matchMode?}`。`explanation` 是通俗解释，`original` 是忠实原文摘录，填写原文必须有非空 `source`；`scopeNote` 说明归纳命名或时效等边界。`evidence` 引用同一证据清单并通向原项。所有字段是纯文本，不支持 HTML。
- `requiredTerms[]`：明确承诺原文释义的关键项，以 `glossary[].term` 精确名称列出。每项须有非空 `full`（中文名称）、`original`、`source`；缺定义或没有在正文、表格／详情实际注释时阻止生成。术语表自身不计覆盖；没有列入本清单的旧术语继续兼容。这个门禁不能自动发现作者未登记的约定，作者仍须从用户请求逐项建立清单。

单字母代号必须显式设置 `matchMode: "code"`，区分大小写，排除盘符 `C:/`／`C:\\`、带连字符或下划线的编号 `D-001`／`D_001`，一般边界也排除 `E01` 等证据编号。仍需核对同字母在不同语境中的含义；同一代号有冲突时改用完整名称／明确别名或定制就地说明，不把多种定义合并成一个术语。默认 `word` 模式保留普通术语及别名的完整单词匹配。

```json
{"requiredTerms":["A"],"glossary":[{"term":"A","full":"入口携带公共包","matchMode":"code","original":"A：入口启动时加载公共包。","explanation":"只启动入口进程，公共能力随入口加载。","source":"虚构设计说明第1项","scopeNote":"示例归纳的方案代号；不是正式版本。","evidence":["证据一"]}]}
```

原词下划线支持悬停、键盘聚焦和点击；短浮层提供预览，长内容可在释义弹窗完整阅读。弹窗可打开依据清单，关闭回到原词；无脚本点击原词跳到完整释义表。正文首次出现仍需常显中文名称及一句话关系。原文详情在打印展开，不能依赖悬停。完整虚构示例见 [关键代号释义示例](../examples/annotated-options.json)。

## 安全与兼容

### 正文重点样式

正文字符串支持三种受限行内样式；所有原文先安全转义，不接受原始 HTML，也不是完整 Markdown 解析器。

| 输入方式 | 呈现 | 使用场景 |
| --- | --- | --- |
| `**关键短语**` | 加粗蓝色 | 需要读者优先注意的结论、责任或动作 |
| `==关键边界==` | 浅暖色底、深色文字 | 必须保留的条件、范围或限制；不自动表示风险级别 |
| 反引号包围原文 | 等宽、浅灰底 | 参数、命令、比较表达式和代码原文；内部不再解释格式或术语 |

样式可用在 `body`、`text`、`paragraphs`、`bullets`、表格说明和核心结论中，也保留重点短语内部的术语与安全链接。URL 原文不会被其中的星号或等号格式化。样式标记不嵌套，不加到正式标题、章节 ID、证据 ID、契约值或图节点名称。

```json
{"body":"先确认**当前责任方**，并保留==尚未验收==这一边界。","bullets":["先读取可信身份，再执行操作。","退出后清理旧状态；结果未知先查询。"],"paragraphs":["参数与命令使用反引号标注，避免把原文当格式。"]}
```

长文字的分段和列表已有原生支持：按论点写 `paragraphs`，并列事项写 `bullets`，单换行为有意停顿，双换行为新段落。先整理输入的语义结构，生成器不擅自重写事实或按字数拆句。避免用整段高亮、窄表格或大量 `<br>` 代替信息组织。打印保留粗体、边线和文字含义。

值作为纯文本转义，不支持任意 HTML 或脚本。非 URL 的 `sources[].ref` 和证据来源仍是引用文本，不自动执行路径；文档入口显式用 `href`。JSON 嵌入转义 `</script>`；页面不加载外部资源。

旧字段、旧状态和四层键继续支持；新版本加强内容核验。旧数据缺少问题标题、结论或没有证据也没有 `evidenceGap` 时会报错，按错误补齐即可。严格核验不能替代事实审查和真实浏览器验收。
