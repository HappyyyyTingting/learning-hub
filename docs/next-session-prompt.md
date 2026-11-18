# 新对话开场提示词

> 用法：在 `/Users/tingtingyu/tingting/learning-hub` 目录下开一个新对话，把下面的内容整段粘贴进去；或者直接对新对话说“读 `docs/next-session-prompt.md`，按里面的步骤继续”。

---

你在 `/Users/tingtingyu/tingting/learning-hub` 这个项目里继续工作。这是一个学习推送平台，Phase 1 是 **Daily English**：每天北京时间凌晨用 DeepSeek 生成雅思词汇学习内容（B2–C1），发到邮箱，并归档到 GitHub Pages。内容按“讲解日 → 复习日”交替。

先读这些文件，不要重新规划脚手架：

- `README.md`
- `docs/setup.md`
- `daily-english/config.yml`
- `daily-english/prompts/v3-lesson.md`
- `daily-english/prompts/v3-review.md`
- `daily-english/schema.json`
- `daily-english/review-schema.json`
- `.github/workflows/daily.yml`

当前状态（2026-11-18）：

- 脚手架已完成；讲解 / 复习交替 + 音频改动后本地 79 个单元测试通过。
- 本次改动前远端 `origin/main` 是 `16faeec`（`content: 2026-11-18`）；提交后以 `git log` 为准。`daily-english/content/` 有 2026-11-09 到 2026-11-18 的内容（11-15、11-16 缺失，属正常漏跑）。
- SMTP 加固 commit `4adad55` 已 push；2026-11-09 到 2026-11-18 的真实发送均成功，`daily-english/state/sent.json` 有记录。
- Pages 已启用（Source = GitHub Actions），站点地址 `https://happyyyytingting.github.io/learning-hub/`。
- 调度已从 `30 23 * * *`（北京 07:30）改为 `0 18 * * *`（北京次日 02:00）。GitHub 的 schedule 实测延迟 3–5 小时，所以邮件通常在北京时间 05:00–07:00 到达。
- 内容模式：
  - `lesson`：5 个新词 + 对话 + 2 道练习 + 0–2 个 3/7/14 天间隔复习项。
  - `review`：只复习上一讲讲解日的 5 个词，含 5 张复习卡 + 4–8 轮对话 + 3 道练习。
  - `generate.py --mode auto` 默认按上一篇的 `mode` 翻转；旧内容没有 `mode` 时按 `lesson` 处理。
  - 复习日会把这 5 个词记为已复习，后续间隔复习会跳过 3 天内刚复习过的词。
- 音频：仅讲解日，`scripts/make_audio.py` 用 edge-tts 生成，英文音色 + 中文音色按顺序拼接，读 5 个单词卡和情景对话（不读练习和答案），约 5–6 分钟。
  - mp3 写在 `daily-english/audio/`，**不提交进 git**（`.gitignore` 已排除），workflow 用 `actions/cache` 在运行之间保留，并清理 `audio.retention_days`（默认 7）天前的文件。
  - 邮件里给 Pages 链接，站点页面有 `<audio>` 播放器；音频步骤 `continue-on-error`，失败不影响当天文字推送。
  - 复习日没有音频。

已定方案：

- 调度：GitHub Actions，cron `0 18 * * *`（北京次日 02:00）。
- 模型：`deepseek-flash`（备选 `deepseek-v4-pro`），可在 `daily-english/config.yml` 切换。
- 投递：邮件 + GitHub Pages；Phase 1 不做音频。
- 目录：一个任务一个顶层目录 `daily-<task>/`；公共流水线在 `scripts/`，所有命令通过 `--task english` 指定任务。
- 内容：JSON 结构化存储；讲解日和复习日使用不同的 prompt 与 schema。
- 失败告警：`scripts/alert.py` 发邮件。

请按这个顺序继续：

1. 先跑 `python -m unittest discover -s tests -v`，确认 79 个测试通过。
2. 用 fixture 预览 2026-11-19 的复习日：
   `python scripts/generate.py --task english --date 2026-11-19 --mode auto --fixture`
   `python scripts/send_email.py --task english --date 2026-11-19 --dry-run`
   检查 `preview/english/2026-11-19/email.html`；预览完删掉 `daily-english/content/2026-11-19.json`，避免样例被真实发送。
3. 确认无误后提交并 push 讲解 / 复习交替改动；push 前先 `git fetch` 并 rebase。
4. 观察下一次定时运行，确认它按 `mode` 生成、发送、提交并部署；检查邮件、Pages 和 `daily-english/state/sent.json`。
5. 如果北京时间 02:00 触发后邮件到得太晚或太早，只改 `.github/workflows/daily.yml` 的 cron 和 `daily-english/config.yml` 的 `schedule_utc`，不要动内容逻辑。

约束：

- 不要重做脚手架，不要扩大 Phase 1 范围。
- 不要在没有我确认的情况下 push、发真实邮件或产生 API 费用。
- 需要账号、密钥、邮箱等信息时先问我。
- 中文沟通；改动尽量小；改完跑测试。
- 不要把密钥贴进对话。

开始前先用几句话复述你读到的当前状态和接下来要做的第一件事。
