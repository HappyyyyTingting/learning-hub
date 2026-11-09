# 新对话开场提示词

> 用法：在 `/Users/tingtingyu/tingting/learning-hub` 目录下开一个新对话，把下面的内容整段粘贴进去；或者直接对新对话说“读 `docs/next-session-prompt.md`，按里面的步骤继续”。

---

你在 `/Users/tingtingyu/tingting/learning-hub` 这个项目里继续工作。这是一个学习推送平台，Phase 1 是 **Daily English**：每天北京时间 07:30 用 Claude 生成 B1–B2 英语内容，发到邮箱，并归档到 GitHub Pages。

先读这些文件，不要重新规划脚手架：

- `README.md`
- `docs/setup.md`
- `tasks/english/config.yml`
- `tasks/english/prompts/v1.md`
- `tasks/english/schema.json`
- `.github/workflows/daily.yml`

当前状态（2026-11-09）：

- 脚手架已完成，26 个单元测试通过。
- 本地 git 已初始化（分支 `main`），但还没有 commit、没有 remote、没有 push。
- 还没有创建 GitHub 仓库，没有配置 Secrets，没有启用 Pages。
- 没有调用过真实 Claude API，也没有发过真实邮件。
- `preview/2026-11-09/email.html` 是 fixture 生成的示例预览；`content/english/` 里的示例内容已删除，避免第一次真实运行误发 fixture。
- `.venv` 已存在；如果环境有问题，按 README 重建。

已定方案：

- 调度：GitHub Actions，cron `30 23 * * *`（北京 07:30）。
- 模型：`claude-opus-5-5`，可在 `config.yml` 切换。
- 投递：邮件 + GitHub Pages；Phase 1 不做音频。
- 内容：JSON 存在 `content/english/`，发送状态存在 `state/sent.json`。
- 失败告警：`scripts/alert.py` 发邮件。
- 仓库名是 `learning-hub`，当前邮件和站点的展示名仍是 `Daily English`，这是有意的。

请按这个顺序继续：

1. 先检查项目状态和测试，确认没有遗漏。
2. 帮我完成本地初始 commit；提交前先给我看 `git status` 和将要提交的文件。
3. 指导我在 GitHub 创建空仓库 `learning-hub` 并 push。如果需要我执行命令，先告诉我命令和影响；不要在未经我确认的情况下创建远端或 push。
4. 指导配置 GitHub Secrets：`ANTHROPIC_API_KEY`、`MAIL_TO`、`MAIL_FROM`、`EMAIL_PROVIDER`，以及 SMTP 或 Resend 对应字段。不要把密钥贴进对话。
5. 指导我把 Pages 的 Source 设为 GitHub Actions。
6. 先跑一次 `dry_run=true`，检查 `email-preview`；确认排版和内容后，再跑一次真实发送。
7. 检查邮件、Pages 和 `state/sent.json`，报告结果和下一步。

约束：

- 不要重做脚手架，不要扩大 Phase 1 范围。
- 不要在没有我确认的情况下创建远端仓库、push、发真实邮件或产生 API 费用。
- 需要账号、密钥、邮箱等信息时先问我。
- 中文沟通；改动尽量小；改完跑测试。

开始前先用几句话复述你读到的当前状态和接下来要做的第一件事。
