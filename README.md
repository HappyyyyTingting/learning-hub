# Learning Hub

日常学习推送平台。Phase 1 先做 **Daily English**：每天北京时间早上 7:30，用 Claude 生成一份 B1–B2 英语学习内容，发到邮箱，并归档到 GitHub Pages。

仓库名不绑定单一任务；以后加资讯、基础知识等任务时，继续用这一套生成、发送、归档流程。

Phase 1 只做一件事：跑通 **定时 → 生成 → 发送 → 归档** 的最小闭环。先不接搜索、音频和反馈系统，等内容质量稳定后再加。

## 流水线

```
GitHub Actions（cron 23:30 UTC / 北京 07:30）
  └─ scripts/generate.py
       Claude API + JSON Schema
       → content/english/YYYY-MM-DD.json
  └─ scripts/send_email.py
       SMTP 或 Resend → 邮箱
       → state/sent.json 记录已发送
  └─ scripts/build_site.py
       → site/index.html + site/YYYY-MM-DD.html → GitHub Pages
  └─ 任一步失败 → scripts/alert.py 发告警邮件
```

每天的内容结构固定：

- 5 个词或短语：音标、词性、英文释义、中文释义、例句
- 3 个额外例句
- 1 段 6–8 轮情景对话
- 2 道选择题（含答案解析）
- 0–2 个复习项：从 3 / 7 / 14 天前首次出现的词里选

字段定义见 `tasks/english/schema.json`，示例见 `tasks/english/fixture.json`。

## 目录

```
tasks/english/
  config.yml        任务配置（时区、模型、prompt、输出目录）
  prompts/v1.md     生成 prompt（可版本化迭代）
  schema.json       内容 JSON Schema
  fixture.json      本地预览用的样例内容
content/english/    每天生成的内容（工作流自动提交）
state/sent.json     已发送日期，防止重复发送
scripts/
  common.py         配置、日期、内容读写、校验
  generate.py       调用 Claude 生成内容
  render.py         渲染邮件 HTML / 纯文本
  send_email.py     发送邮件（SMTP / Resend）
  build_site.py     构建静态归档站
  alert.py          失败告警
tests/              单元测试
```

## 本地跑通

需要 Python 3.12。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

脚本不会自动读取 `.env`，本地可以这样加载：

```bash
cp .env.example .env
# 编辑 .env，至少填 ANTHROPIC_API_KEY、MAIL_TO、MAIL_FROM 和 SMTP / Resend 配置
set -a; source .env; set +a
```

先用 fixture 走一遍，不调用 API、不发邮件：

```bash
python scripts/generate.py --fixture --date 2026-11-09
python scripts/send_email.py --date 2026-11-09 --dry-run
open preview/2026-11-09/email.html

python scripts/build_site.py
open site/index.html
```

真正生成一天内容：

```bash
python scripts/generate.py --date 2026-11-09
```

想换模型可以临时覆盖，或直接改 `tasks/english/config.yml`：

```bash
python scripts/generate.py --date 2026-11-09 --model claude-sonnet-5-5
```

跑测试：

```bash
python -m unittest discover -s tests -v
```

清理本地预览产物：`rm -rf preview site content/english/*.json`（确认没有想保留的内容）。

## 部署到 GitHub

完整步骤见 [`docs/setup.md`](docs/setup.md)。最短路径：

1. 新建仓库并 push 本目录。
2. 在 **Settings → Secrets and variables → Actions** 配置 `ANTHROPIC_API_KEY` 和邮件相关 secrets。
3. 在 **Settings → Pages** 把 Source 设为 **GitHub Actions**。
4. 在 **Actions → Daily English push → Run workflow** 先跑一次 `dry_run = true`，下载 `email-preview` 检查排版。
5. 再跑一次 `dry_run = false`，确认收到邮件、Pages 有归档。

## 每天的运行与幂等

- `generate.py` 发现当天内容已存在就跳过；`--force` 可覆盖。
- `send_email.py` 发现 `state/sent.json` 里有当天日期就跳过；`--force` 可重发。
- 工作流会把 `content/english/*.json` 和 `state/sent.json` 提交回仓库，用 `GITHUB_TOKEN` push。**这类提交不会再次触发工作流**，所以不会循环。
- 只有默认分支上的 `schedule` 会生效；GitHub 的 cron 可能延迟几分钟到几十分钟，属正常现象。
- 极端情况下：邮件已发出但提交 state 失败，重跑会再发一次。重跑前先看一眼 `state/sent.json` 和邮箱。

## 候选方案与当前选择

Phase 1 的选择与备选，方便以后调整：

| 部分 | 当前选择 | 备选 | 说明 |
| --- | --- | --- | --- |
| 调度 | GitHub Actions cron | 本地 launchd / cron；Cloudflare Workers Cron；Anthropic Managed Agents scheduled deployments | Actions 免费额度够用、零服务器；本地方案要求电脑开机；Managed Agents 省调度代码但会把运行绑定到平台 |
| 模型 | `claude-opus-5-5` | `claude-sonnet-5-5`、`claude-haiku-5-5` | 先质量优先；稳定后可降级省钱，改 `config.yml` 一行即可 |
| 内容格式 | 结构化 JSON | Markdown | JSON 便于稳定渲染、复习追踪和以后做 App |
| 存储 | 仓库内 JSON 文件 | SQLite、外部数据库 | Phase 1 不需要数据库，Git 本身就是版本记录 |
| 投递 | 邮件 + GitHub Pages | Telegram Bot、RSS、微信 | 邮件适合每天固定阅读；Pages 负责归档和分享 |
| 音频 | 暂不开启 | edge-tts + Cloudflare R2 | Phase 2 再复用 tech-digest 的音频方案 |
| 反馈 | 手动记录 | 邮件一键评分、每周 meta 任务 | Phase 2 再做闭环 |
| 失败告警 | 邮件（已内置） | — | 避免像早期 tech-digest 一样静默失败 |

成本量级：每天一次模型调用，输入输出各几千 token，具体以 Anthropic 官方价格为准；GitHub Actions 私有仓库每月 2000 分钟免费额度，本工作流每天约 2–4 分钟，远低于额度。

## Prompt 迭代

- 当前 prompt 在 `tasks/english/prompts/v1.md`，每篇内容会记录 `prompt_version`。
- 修改方式：复制成 `v2.md` → 改 `config.yml` 的 `prompt` 和 `prompt_version` → 提交。下一班任务自动使用新版本，历史内容仍可追溯是哪个版本生成的。
- 不要在多天内容之间直接静默改 `v1.md`，否则出问题时无法判断是 prompt 还是模型波动。

## 下一步（Phase 2）

1. 反馈入口：邮件底部加“今天难度如何 / 哪个部分最有用”，或每周发一封简短问卷。
2. 每周 meta 任务：读最近 7 天内容和反馈，提出 prompt 修改建议（先输出 diff，人工确认后合并）。
3. 音频：edge-tts + R2，复用 tech-digest 的 `make_audio.py`。
4. 第二类任务（资讯、基础知识）接入同一套生成/发送/归档流程，再把公共部分抽成框架。
5. 查看与定制化学习：在 Pages 之上做 PWA / App。
