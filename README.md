# Learning Hub

日常学习推送平台。Phase 1 先做 **Daily English**：每天北京时间早上 7:30，用 DeepSeek 生成一份雅思词汇学习内容（B2–C1），发到邮箱，并归档到 GitHub Pages。

仓库按任务拆分：每个任务一个顶层目录 `daily-<task>/`，公共流水线在 `scripts/`。以后加资讯、AI 基础、历史等任务时，不需要改公共逻辑。

Phase 1 只做一件事：跑通 **定时 → 生成 → 发送 → 归档** 的最小闭环。先不接搜索、音频和反馈系统，等内容质量稳定后再加。

## 流水线

```
GitHub Actions（cron 23:30 UTC / 北京 07:30）
  └─ scripts/generate.py --task english
       DeepSeek API + JSON Schema
       → daily-english/content/YYYY-MM-DD.json
  └─ scripts/send_email.py --task english
       SMTP 或 Resend → 邮箱
       → daily-english/state/sent.json 记录已发送
  └─ scripts/build_site.py --task english
       → site/english/ + site/index.html → GitHub Pages
  └─ 任一步失败 → scripts/alert.py 发告警邮件
```

每天的内容结构固定：

- 5 个雅思高频词：美/英音标、多词性释义、考点提示、同义替换（含辨析和搭配）、高频搭配、词形变化、2 个雅思风格例句
- 1 段 6–8 轮情景对话
- 2 道选择题（词义辨析 / 同义替换 / 搭配，含答案解析）
- 0–2 个复习项：从 3 / 7 / 14 天前首次出现的词里选
- 考频只用 high / medium / low 标签，不写具体出现次数，也不冒充剑桥真题原句

字段定义见 `daily-english/schema.json`，示例见 `daily-english/fixture.json`。

## 目录

```
daily-english/            一个任务 = 一个顶层目录
  config.yml              任务配置（时区、模型、prompt、站点文案）
  prompts/v2.md           生成 prompt（可版本化迭代）
  schema.json             内容 JSON Schema
  fixture.json            本地预览用的样例内容
  render.py               任务专用渲染（邮件正文 + 站点 CSS）
  content/                每天生成的内容（工作流自动提交）
  state/sent.json         已发送日期，防止重复发送
scripts/                  公共流水线，不写死具体任务
  common.py               任务路径解析、配置、日期、内容读写、校验
  generate.py             调用 DeepSeek 生成内容
  send_email.py           发送邮件（SMTP / Resend）
  email_layout.py         公共邮件外壳与预览输出
  build_site.py           构建任务归档站和 Learning Hub 入口
  alert.py                失败告警
tests/                    单元测试
docs/                     部署与交接文档
```

旧任务目录 `tasks/`、`content/`、`state/` 已合并进 `daily-english/`；新增任务照 `daily-english/` 的形状复制即可。

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
# 编辑 .env，至少填 DEEPSEEK_API_KEY、MAIL_TO、MAIL_FROM 和 SMTP / Resend 配置
set -a; source .env; set +a
```

先用 fixture 走一遍，不调用 API、不发邮件：

```bash
python scripts/generate.py --task english --fixture --date 2026-11-09
python scripts/send_email.py --task english --date 2026-11-09 --dry-run
open preview/english/2026-11-09/email.html

python scripts/build_site.py --task english
open site/english/index.html
open site/index.html
```

真正生成一天内容：

```bash
python scripts/generate.py --task english --date 2026-11-09
```

想换模型可以临时覆盖，或直接改 `daily-english/config.yml`：

```bash
python scripts/generate.py --task english --date 2026-11-09 --model deepseek-v4-pro
```

跑测试：

```bash
python -m unittest discover -s tests -v
```

清理本地预览产物：`rm -rf preview site daily-english/content/*.json`（确认没有想保留的内容）。

## 新增任务

1. 复制 `daily-english/` 为 `daily-<task>/`，改 `config.yml` 里的 `name`、`prompt`、`site_title`、`site_description` 和邮件文案。
2. 写该任务的 `schema.json`、`prompts/v1.md`、`fixture.json` 和 `render.py`。
3. `render.py` 至少提供三个东西：
   - `content_to_body_html(content) -> str`：邮件和站点共用的正文 HTML
   - `render_content(content, config, site_url="") -> email_layout.RenderedContent`：邮件主题、preheader、HTML、纯文本
   - `SITE_CSS: str`：任务归档站的样式
4. 在 workflow 里加一个 job（或复制一份 `daily.yml`），把命令里的 `--task` 换成新任务名。公共脚本不需要改。
5. 跑 `python scripts/build_site.py --task <task>`，任务会自动出现在 `site/index.html` 的入口页。

## 部署到 GitHub

完整步骤见 [`docs/setup.md`](docs/setup.md)。最短路径：

1. 新建仓库并 push 本目录。
2. 在 **Settings → Secrets and variables → Actions** 配置 `DEEPSEEK_API_KEY` 和邮件相关 secrets。
3. 在 **Settings → Pages** 把 Source 设为 **GitHub Actions**。
4. 在 **Actions → Daily English push → Run workflow** 先跑一次 `dry_run = true`，下载 `email-preview` 检查排版。
5. 再跑一次 `dry_run = false`，确认收到邮件、Pages 有归档。

## 每天的运行与幂等

- `generate.py` 发现 `daily-english/content/<date>.json` 已存在就跳过；`--force` 可覆盖。
- `send_email.py` 发现 `daily-english/state/sent.json` 里有当天日期就跳过；`--force` 可重发。
- 工作流会把 `daily-english/` 提交回仓库，用 `GITHUB_TOKEN` push。**这类提交不会再次触发工作流**，所以不会循环。
- 只有默认分支上的 `schedule` 会生效；GitHub 的 cron 可能延迟几分钟到几十分钟，属正常现象。
- 极端情况下：邮件已发出但提交 state 失败，重跑会再发一次。重跑前先看一眼 `daily-english/state/sent.json` 和邮箱。

## 候选方案与当前选择

Phase 1 的选择与备选，方便以后调整：

| 部分 | 当前选择 | 备选 | 说明 |
| --- | --- | --- | --- |
| 调度 | GitHub Actions cron | 本地 launchd / cron；Cloudflare Workers Cron；云函数定时触发 | Actions 免费额度够用、零服务器；本地方案要求电脑开机；云函数省调度代码但会把运行绑定到平台 |
| 模型 | `deepseek-flash` | `deepseek-v4-pro` | 先用 flash 控制成本；需要更细的语义辨析时切 v4-pro，改 `config.yml` 一行即可 |
| 内容格式 | 结构化 JSON | Markdown | JSON 便于稳定渲染、复习追踪和以后做 App |
| 存储 | 仓库内 JSON 文件 | SQLite、外部数据库 | Phase 1 不需要数据库，Git 本身就是版本记录 |
| 投递 | 邮件 + GitHub Pages | Telegram Bot、RSS、微信 | 邮件适合每天固定阅读；Pages 负责归档和分享 |
| 音频 | 暂不开启 | edge-tts + Cloudflare R2 | Phase 2 再复用 tech-digest 的音频方案 |
| 反馈 | 手动记录 | 邮件一键评分、每周 meta 任务 | Phase 2 再做闭环 |
| 失败告警 | 邮件（已内置） | — | 避免像早期 tech-digest 一样静默失败 |

成本量级：每天一次模型调用，输入输出各几千 token，具体以 DeepSeek 官方价格为准；公开仓库的 Actions 标准 runner 免费，私有仓库每月 2000 分钟免费额度，本工作流每天约 2–4 分钟，远低于额度。

## Prompt 迭代

- 当前 prompt 在 `daily-english/prompts/v2.md`，每篇内容会记录 `prompt_version`。
- 修改方式：复制成 `v3.md` → 改 `daily-english/config.yml` 的 `prompt` 和 `prompt_version` → 提交。下一班任务自动使用新版本，历史内容仍可追溯是哪个版本生成的。
- 不要在多天内容之间直接静默改 `v2.md`，否则出问题时无法判断是 prompt 还是模型波动。

## 下一步（Phase 2）

1. 反馈入口：邮件底部加“今天难度如何 / 哪个部分最有用”，或每周发一封简短问卷。
2. 每周 meta 任务：读最近 7 天内容和反馈，提出 prompt 修改建议（先输出 diff，人工确认后合并）。
3. 站点阅读模式：章节和单词卡折叠、顶部目录大纲、记住展开状态；邮件保持线性，不做折叠（客户端兼容性差）。
4. 音频：edge-tts + R2，复用 tech-digest 的 `make_audio.py`。
5. 第二类任务（AI 基础、资讯、历史）接入同一套生成/发送/归档流程，`site/` 入口页会自动聚合。
6. 查看与定制化学习：在 Pages 之上做 PWA / App。
