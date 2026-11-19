# 证据型 HTML 报告

`evidence-html-report` 是一个 Codex Skill，适合把技术方案、审计或交接整理成一份可离线打开的 HTML。读者先看结论和下一步，再按主题看理由，需要核对时从正文编号找到出处。

## 安装

<!-- icarus-release-fact: dynamic -->
从 [GitHub 最新正式版](https://github.com/boomkalakasha/evidence-html-report-skill/releases/latest) 下载 ZIP，把解压后的 `evidence-html-report` 目录放进 Codex 用户技能目录 `~/.codex/skills/`，然后打开一个新会话。已有自定义版本时，先备份再合并。所有版本见[发布记录](https://github.com/boomkalakasha/evidence-html-report-skill/releases)。

## 使用

在 Codex 中说：

> 用 evidence-html-report 把这次技术方案写成离线 HTML。先给推荐做法和关键限制，再按主题解释怎么做，并给每个重要判断附上依据。

想直接试生成器，可以在 Skill 目录运行下面的命令。生成器只用 Python 标准库，生成后双击 `output-focus.html` 即可打开。

```text
python scripts/build_report.py examples/focus-changes.json output-focus.html --strict
```

在示例中，用左侧目录切换主题，在变化图里看改前、变更、改后，再点正文编号查来源。长步骤或补充材料按需展开；关闭 JavaScript 仍可读，打印会保留全篇内容和依据。

## 文档和示例

- [写作规则](SKILL.md)和[呈现原则](references/report-design.md)说明怎样组织结论、主题和细节。
- [内容字段](references/content-model.md)和[图解说明](references/diagram-model.md)提供编写输入所需的格式。旧输入和连续阅读模式仍受支持。
- [示例目录](examples/)包含虚构的技术简报、审计和术语说明，可用来试生成，不包含真实业务证据。
- [版本变化](CHANGELOG.md)记录各版差异和回退提示。

## 验证与贡献

```text
python -m unittest discover -s tests -v
python scripts/build_report.py --self-test
```

跑浏览器检查前，安装 `requirements-dev.txt` 中的依赖，再运行 `python -m playwright install chromium`（已有 Chrome 也可运行）。`python tests/focus_browser_checks.py --output <输出目录>` 检查默认阅读模式；`python tests/browser_checks.py` 检查连续阅读模式。

欢迎通过 GitHub Issues 或 PR 提建议。公开示例请使用虚构数据；涉及漏洞请按[安全说明](SECURITY.md)报告。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
