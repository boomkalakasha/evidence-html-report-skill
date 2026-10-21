# 证据型 HTML 报告

> **已停止维护（2026-10-21）**：本项目今后不再更新，也不再承诺功能、缺陷或安全修复。新使用场景推荐独立项目 [answer-me-with-html](https://github.com/QingYunA/answer-me-with-html)。
>
> **No longer maintained** as of 2026-10-21. For new work, use [answer-me-with-html](https://github.com/QingYunA/answer-me-with-html). Existing source, versions and reports are retained for reference.

## 推荐迁移

- 按 [answer-me-with-html 的当前说明](https://github.com/QingYunA/answer-me-with-html#readme)安装和使用，在各 Agent 的技能管理工具中关闭 `evidence-html-report`。
- 将工作流中主动推荐 `evidence-html-report` 的入口改为 `answer-me-with-html`；不要继续同时默认加载两个报告 Skill。
- 已生成的 HTML 可以继续独立阅读，原始 JSON 和证据材料请保留。两者是独立项目，不承诺旧 JSON 可直接作为新项目输入。

以下内容记录本项目的历史能力和使用方式。

一个独立可安装的 Codex Skill：把复杂审计、技术方案和场景交接组织成中文、可追溯、可离线阅读的单文件 HTML。

架构优化评估按阅读收益选用报告，优先引用现有事实源并保留完整范围与分层证据；
简短比较复用 Markdown，复杂关系用 HTML 组织。见[呈现原则](references/report-design.md)。

- 中文结构标题、导航、状态和证据分层；保留专有名词、接口及路径。
- 按用途选结构：审计台账、技术调用链与对照表、交接检查清单。
- 重点常显、相关详情就近展开；并列对比图、分段列表和可点击材料入口。
- 章节与详情统一编号，完整目录可按节跳转，滚动时显示当前章节。
- 结论旁的凭证编号直达逐项清单；支持原项链接、具体定位和无法跳转时的清楚说明。
- 搜索、状态筛选、清空、可调整宽度的详情抽屉及术语解释。
- 关键代号下划线原文释义：悬停、键盘与手机点击，保留中文解释、原文、出处和依据；必需项缺失会阻止生成。
- 正文静态生成，关闭 JavaScript 仍可读；打印包含全部详情与证据。
- 生成器仅使用 Python 标准库，无 CDN、外部字体或运行依赖。

## 安装（历史版本）

将仓库克隆到 Codex 全局技能目录，目标目录应尚不存在：

```powershell
git clone https://github.com/boomkalakasha/evidence-html-report-skill.git "$env:USERPROFILE\.codex\skills\evidence-html-report"
```

其他支持 `SKILL.md` 的工具也可安装完整目录。已有旧版时先备份，再合并更新；不要覆盖自定义文件或在混合修改的目录中直接拉取。新会话可发现更新后的技能。

仓库名是 `evidence-html-report-skill`；技能调用名及安装目录仍为 `evidence-html-report`。

## 使用（历史版本）

在 Codex 中要求：

> 使用 evidence-html-report，把这次技术方案整理成中文 HTML，先说明真实入口和调用链，再列职责与验收，区分本次必做和后续预留。

也可以直接运行生成器：

```text
python scripts/build_report.py examples/technical-brief.json output-report.html
python scripts/build_report.py examples/audit.json output-audit.html
python scripts/build_report.py examples/reading-layout.json output-reading.html
python scripts/build_report.py examples/annotated-options.json output-options.html
```

生成的 HTML 可以直接双击打开。[技能规则](SKILL.md)、[内容模型](references/content-model.md) 和 [呈现原则](references/report-design.md) 说明字段与边界。示例是虚构设计，不包含内部报告或真实业务证据。

## 本版相对旧模板的变化

v1.3.0 增加关键代号的原文释义与必需覆盖门禁：悬停或聚焦预览，点击查看完整原文、解释、出处和依据；缺项阻止生成。单字母避免盘符和编号误注，手机、无脚本和打印保留全部定义。见 [关键代号示例](examples/annotated-options.json)。保留编号目录、逐项凭证、就近折叠与完整打印。

完整变化与回退说明见 [版本变化](CHANGELOG.md)。

移除固定英文结构词；旧状态键和证据层显示中文。增加章节导航、调用步骤、对照表、检查清单及按用途调整结构。补齐责任、验收、模块类别和证据限制的展示；拦截悬空证据、重复编号与错列表格；修复打印遗漏抽屉详情。

旧 JSON 字段与常见枚举继续支持；缺少问题内容、证据或 `evidenceGap` 的数据现在会被拒绝，需按提示补齐。该技能负责报告呈现，不代替研究、产品验收或部署。

## 历史验证命令

```text
python -m unittest discover -s tests -v
python scripts/build_report.py --self-test
node --check assets/report.js
```

可选浏览器回归：安装 `requirements-dev.txt` 并运行 `python -m playwright install chromium`，再执行 `python tests/browser_checks.py`。它检查桌面和 390 px、搜索筛选、抽屉焦点、术语、上下文折叠、链接、手机表头、打印恢复和静态阅读。

本项目不再安排 Issues／PR 的处理或后续发版。公开讨论时仍请移除内部业务、客户信息、机器路径和凭据；发现安全问题请参阅 [安全说明](SECURITY.md)。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
