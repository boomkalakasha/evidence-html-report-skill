# Evidence HTML Report · 证据型 HTML 报告

**先让团队看懂结论，需要追问时，每个重要判断都有出处。**

这是一个面向 Codex 的 Skill。它把技术方案、审计复盘或团队交接整理成一份离线 HTML：读者先看「核心结论」和下一步，再按主题查详情，或沿正文编号回到依据。收件人用浏览器打开即可，无需安装 Codex 或运行服务。

[看报告示例](#看一份报告) · [安装到 Codex](#安装到-codex) · [写第一份报告](#写第一份报告) · [从-json-生成](#从-json-生成) · [常见问题](#常见问题)

## 看一份报告

比如团队要决定：**把新的处理能力并入现有服务，还是另起一个服务？** 汇报人需要先给推荐，开发要看接入边界，验收人则要知道哪些场景还没跑。用同一份报告，就能把这三件事放到各自该看的位置。

![虚构接入方案的报告首屏：左边是主题目录，右边是核心结论、接法变化图、下一步和带编号的来源。](docs/images/report-preview.png)

*截图由公开的[接入方案样例](examples/focus-changes.json)实际生成。图里的「待实施」是虚构方案的状态。「变更」视图高亮新增和修改的部分；可以切到「改前」或「改后」单独查看。*

| 读者想知道 | 可以看哪里 |
| --- | --- |
| 现在怎么判断，下一步要做什么？ | 首屏的总判断、各主题一句话和必要的状态清单。 |
| 到底改了哪些地方？ | 打开对应主题，比较改前、变更和改后。遇到需要执行的任务，就地展开步骤或验收细节。 |
| 这句话有依据吗？ | 在句子旁看数字角标，点击到本节来源，再打开原材料或附录记录。 |
| 还有哪些问题要处理？ | 多问题报告可搜索、筛状态，点开单项查看影响、责任和建议行动。 |

材料简单、一段话或一张表就能讲清时，用普通 Markdown 即可。这个 Skill 更适合既有人只想看结论、也有人需要逐项核对的报告。

## 安装到 Codex

<!-- icarus-release-fact: dynamic -->
1. 从 [GitHub 最新正式版](https://github.com/boomkalakasha/evidence-html-report-skill/releases/latest) 下载 `evidence-html-report-v*.zip` 安装包。要让团队使用同一版，从[发布记录](https://github.com/boomkalakasha/evidence-html-report-skill/releases)选定版本，并保存对应的校验文件。
2. 解压，把含 `SKILL.md` 的整个 `evidence-html-report/` 放进 Codex 技能目录。只给当前项目用，放在项目的 `.agents/skills/` 下；给当前用户的多个项目用，放在 `~/.agents/skills/` 下。如果已经在 `~/.codex/skills/` 使用过旧版，备份自定义文件后更新原来的目录，避免并存两份同名 Skill。
3. 在能访问报告材料的项目中打开新会话，输入 `$evidence-html-report` 选择技能。生成端需要能运行 Python 3；阅读端只需要浏览器。

## 写第一份报告

先给 Codex 三样东西：**谁要看、要判断什么、哪些材料能支持判断**。例如：

> 用 $evidence-html-report，根据这份设计稿和本地测试记录，为评审组做一份接入方案报告。先给推荐做法和最大限制，再用图说明改前与改后，按主题写职责和验收。区分本地已测、尚未验收和待实施，把重要判断连到具体出处。输出离线 HTML，并保留可重生成的 JSON。

打开报告后，先读「核心结论」，再挑一句关键判断，顺着编号走到原项或附录。确认正文没有把计划当成已实施、没有把局部测试当成正式验收。转发前核对对方能否打开材料；不能共享原件时，在附录写明定位和访问限制。

| 要做的报告 | 正文优先写什么 | 可运行的输入样例 |
| --- | --- | --- |
| 技术方案或变化说明 | 推荐做法、改动边界、如何验收 | [接入方案](examples/focus-changes.json) |
| 审计与问题复盘 | 发现、影响、证据和责任 | [发布准备核验](examples/audit.json) |
| 工作交接 | 当前状态、谁来接手、下一步怎样算完成 | [任务交接](examples/reading-layout.json) |

## 从 JSON 生成

不使用 Codex 也可以生成。在解压后的 Skill 目录运行以下命令，打开 `output-focus.html`。生成器只用 Python 标准库；`--strict` 会拒绝生成器不认识的字段。

```text
python scripts/build_report.py --strict examples/focus-changes.json output-focus.html
```

要做自己的报告，可以先复制一个样例，保存为 UTF-8 编码的 JSON，再按这个顺序替换内容：

1. 写 `verdict` 的一句总判断和必要限制。正文 `sections` 按读者要了解的问题拆开，不用为了填模板凑章节。
2. 在 `evidence` 登记依据和定位。在某句判断后写 `[[E1]]`（这里假设该来源的 ID 是 `E1`），让引用跟着具体句子走，不用在每节重复抄一遍材料。
3. 需要对比才加变化图，需要筛选才加问题清单。流程、表格、折叠和术语提示的写法见[内容模型](references/content-model.md)和[图解模型](references/diagram-model.md)。
4. 换一个新的 HTML 输出文件名生成，打开检查目录、图、来源和打印。保留 JSON，更新报告时可从同一份输入重生成。

## 常见问题

<details>
<summary>单文件离线阅读，为什么有些链接还是打不开？</summary>

正文、样式、脚本和已内嵌图片在 HTML 里。链接指向的原文件不一定在里面，可能需要网络、共享目录或项目权限。分享前要用接收方能访问的入口，或者写清材料名称、版本和定位。不要把凭据或不能公开的资料放进报告。

</details>

<details>
<summary>表格或图里的结果，可以当成已验收吗？</summary>

生成器能检查字段和引用，不能替你查明事实。例如，变化图可以检查已登记的结果节点是否在对应视图可见，但不会判断两条流程是不是同一种结果，也不会证明方案已经实施。交付前仍需核对材料、状态和比较范围。

</details>

<details>
<summary>能保留旧布局，或打印整份报告吗？</summary>

默认点击目录切换主题。需要连续滚动时设 `readingMode: "continuous"`。无脚本时正文仍可连续阅读；使用「打印完整报告」可打印各主题和已登记的详情，不受当前选中主题限制。

</details>

## 文档、验证与贡献

- [Skill 写作规则](SKILL.md)和[组织与呈现原则](references/report-design.md)：适合报告作者。[内容模型](references/content-model.md)、[图解模型](references/diagram-model.md)与[原生组件模型](references/native-model.md)：适合直接编辑 JSON 的人。
- [变更记录](CHANGELOG.md)保留各版差异和回退信息。提交公开示例请用虚构材料；漏洞按[安全说明](SECURITY.md)报告。
- 本地验证：`python -m unittest discover -s tests -v`、`python scripts/build_report.py --self-test`。浏览器回归先按 `requirements-dev.txt` 安装依赖，再运行 `python tests/focus_browser_checks.py --output <输出目录>`（默认阅读）和 `python tests/browser_checks.py`（连续阅读）。可使用预装 Chrome，或运行 `python -m playwright install chromium`。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
