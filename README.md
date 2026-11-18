# Learning Hub

日常学习推送平台。Phase 1 先做 **Daily English**：每天北京时间凌晨触发，用 DeepSeek 生成一份雅思词汇学习内容（B2–C1），发到邮箱，并归档到 GitHub Pages。内容按 **讲解日 → 复习日 → 讲解日** 交替：讲解日学 5 个新词，复习日巩固上一讲的 5 个词。

仓库按任务拆分：每个任务一个顶层目录 `daily-<task>/`，公共流水线在 `scripts/`。以后加资讯、AI 基础、历史等任务时，不需要改公共逻辑。

Phase 1 只做一件事：跑通 **定时 → 生成 → 发送 → 归档** 的最小闭环。先不接搜索和反馈系统，等内容质量稳定后再加。

## 流水线

```
GitHub Actions（cron 18:00 UTC / 北京次日 02:00）
  └─ scripts/generate.py --task english --mode auto
       DeepSeek API + JSON Schema（lesson / review）
       → daily-english/content/YYYY-MM-DD.json
  └─ scripts/make_audio.py --task english
       edge-tts 中英双音色 → daily-english/audio/YYYY-MM-DD.mp3
       （不进 git，用 actions/cache 在运行之间保留最近 7 天）
  └─ scripts/send_email.py --task english
       SMTP 或 Resend → 邮箱
       → daily-english/state/sent.json 记录已发送
  └─ scripts/build_site.py --task english
       → site/english/ + site/index.html → GitHub Pages
  └─ 任一步失败 → scripts/alert.py 发告警邮件
```

内容按天分为两种模式，由 `mode` 字段区分（旧内容没有 `mode` 时按讲解日处理）：

**讲解日 `lesson`**

- 5 个雅思高频词：美/英音标、多词性释义、考点提示、同义替换（含辨析和搭配）、高频搭配、词形变化、2 个雅思风格例句
- 1 段 6–8 轮情景对话
- 2 道选择题（词义辨析 / 同义替换 / 搭配，含答案解析）
- 0–2 个间隔复习项：从 3 / 7 / 14 天前首次出现的词里选
- 音频讲解：5 个单词卡 + 情景对话，英文用英文音色、中文释义和考点用中文音色，约 5 分钟；练习和答案不读，避免剧透

**复习日 `review`**

- 只复习上一讲讲解日的 5 个词，不学新词（复习日暂时没有音频）
- 每个词：核心释义、考点/易错点、1 个全新例句、翻译和提示
- 1 段 4–8 轮情景对话，至少用到 3 个复习词
- 3 道选择题（词义辨析 / 固定搭配 / 语境填空，含答案解析）

模式默认按上一篇自动切换：上一篇是讲解日，今天就生成复习日；上一篇是复习日，今天回到讲解日。漏跑一天也不会打乱顺序，需要时可用 `--mode lesson|review` 强制指定。

考频只用 high / medium / low 标签，不写具体出现次数，也不冒充剑桥真题原句。

字段定义见 `daily-english/schema.json`（讲解日）和 `daily-english/review-schema.json`（复习日），示例见 `daily-english/fixture.json` 和 `daily-english/fixture-review.json`。

## 目录

```
daily-english/            一个任务 = 一个顶层目录
  config.yml              任务配置（时区、模型、prompt、站点文案）
  prompts/v3-lesson.md    讲解日 prompt（可版本化迭代）
  prompts/v3-review.md    复习日 prompt
  schema.json             讲解日 JSON Schema
  review-schema.json      复习日 JSON Schema
  fixture.json            讲解日本地预览样例
  fixture-review.json     复习日本地预览样例
  render.py               任务专用渲染（邮件正文 + 站点 CSS + 朗读稿）
  content/                每天生成的内容（工作流自动提交）
  audio/                  每天生成的 mp3（不进 git，本地和 CI 缓存保留 7 天）
  state/sent.json         已发送日期，防止重复发送
scripts/                  公共流水线，不写死具体任务
  common.py               任务路径解析、配置、日期、内容读写、校验
  generate.py             调用 DeepSeek 生成内容
  make_audio.py           edge-tts 生成讲解音频，并清理 7 天前的文件
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
# 讲解日样例
python scripts/generate.py --task english --fixture --date 2026-11-09 --mode lesson
python scripts/send_email.py --task english --date 2026-11-09 --dry-run
open preview/english/2026-11-09/email.html

# 复习日样例（需要仓库里已有历史讲解内容；没有历史时先跑一次讲解日）
python scripts/generate.py --task english --fixture --date 2026-11-19 --mode review
python scripts/send_email.py --task english --date 2026-11-19 --dry-run
open preview/english/2026-11-19/email.html

# 讲解日音频（会调用免费的 edge-tts，不需要密钥；约 2–3 分钟）
python scripts/make_audio.py --task english --date 2026-11-09 --dry-run   # 先看朗读稿
python scripts/make_audio.py --task english --date 2026-11-09
open daily-english/audio/2026-11-09.mp3

python scripts/build_site.py --task english
open site/english/index.html
open site/index.html
```

> 注意：fixture 写入的是样例内容，只用于预览。预览完把 `daily-english/content/<date>.json` 删掉，避免工作流把样例当成真实内容发送。

真正生成一天内容（`--mode auto` 会按上一篇自动选择讲解 / 复习；也可以显式写 `--mode lesson` 或 `--mode review`）：

```bash
python scripts/generate.py --task english --date 2026-11-09 --mode auto
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
3. `render.py` 提供这几个接口：
   - `content_to_body_html(content) -> str`：邮件和站点共用的正文 HTML
   - `render_content(content, config, site_url="", audio_url="") -> email_layout.RenderedContent`：邮件主题、preheader、HTML、纯文本
   - `SITE_CSS: str`：任务归档站的样式
   - 需要音频时再加 `content_to_audio_segments(content, name) -> list[tuple[str, str]]`，返回 `(语言, 文本)` 列表，`make_audio.py` 会按语言选音色并拼接
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
- 只有默认分支上的 `schedule` 会生效；GitHub 的 cron 可能延迟几分钟到几小时。本项目实测常见延迟是 3–5 小时，所以 cron 设在 UTC 18:00（北京次日 02:00），邮件通常在北京时间 05:00–07:00 到达。
- 极端情况下：邮件已发出但提交 state 失败，重跑会再发一次。重跑前先看一眼 `daily-english/state/sent.json` 和邮箱。
- 音频不进 git：workflow 用 `actions/cache` 在两次运行之间传递 `daily-english/audio/`，每次生成后清理 `audio.retention_days`（默认 7）天前的文件，站点只带最近一周的 mp3。音频步骤失败不影响当天的文字推送。
- 音频生成会调用免费的 edge-tts，不需要密钥；34 段左右、5–6 分钟的内容大约耗时 2–3 分钟。

## 候选方案与当前选择

Phase 1 的选择与备选，方便以后调整：

| 部分 | 当前选择 | 备选 | 说明 |
| --- | --- | --- | --- |
| 调度 | GitHub Actions cron | 本地 launchd / cron；Cloudflare Workers Cron；云函数定时触发 | Actions 免费额度够用、零服务器；本地方案要求电脑开机；云函数省调度代码但会把运行绑定到平台 |
| 模型 | `deepseek-flash` | `deepseek-v4-pro` | 先用 flash 控制成本；需要更细的语义辨析时切 v4-pro，改 `config.yml` 一行即可 |
| 内容格式 | 结构化 JSON | Markdown | JSON 便于稳定渲染、复习追踪和以后做 App |
| 存储 | 仓库内 JSON 文件 | SQLite、外部数据库 | Phase 1 不需要数据库，Git 本身就是版本记录 |
| 投递 | 邮件 + GitHub Pages | Telegram Bot、RSS、微信 | 邮件适合每天固定阅读；Pages 负责归档和分享 |
| 音频 | edge-tts（中英双音色）+ Pages 托管 | Cloudflare R2；不做音频 | 只在讲解日生成；mp3 不进 git，靠 actions/cache 保留 7 天，避免仓库历史膨胀 |
| 反馈 | 手动记录 | 邮件一键评分、每周 meta 任务 | Phase 2 再做闭环 |
| 失败告警 | 邮件（已内置） | — | 避免像早期 tech-digest 一样静默失败 |

成本量级：每天一次模型调用，输入输出各几千 token，具体以 DeepSeek 官方价格为准；公开仓库的 Actions 标准 runner 免费，私有仓库每月 2000 分钟免费额度，本工作流每天约 2–4 分钟，远低于额度。

## Prompt 迭代

- 当前讲解日 prompt 在 `daily-english/prompts/v3-lesson.md`，复习日在 `daily-english/prompts/v3-review.md`；每篇内容会记录 `prompt_version`。
- 修改方式：复制成 `v4-lesson.md` / `v4-review.md` → 改 `daily-english/config.yml` 的 `prompt`、`prompt_review` 和 `prompt_version` → 提交。下一班任务自动使用新版本，历史内容仍可追溯是哪个版本生成的。
- 不要在多天内容之间直接静默改 `v3-*.md`，否则出问题时无法判断是 prompt 还是模型波动。

## 下一步（Phase 2）

1. 反馈入口：邮件底部加“今天难度如何 / 哪个部分最有用”，或每周发一封简短问卷。
2. 每周 meta 任务：读最近 7 天内容和反馈，提出 prompt 修改建议（先输出 diff，人工确认后合并）。
3. 站点阅读模式：章节和单词卡折叠、顶部目录大纲、记住展开状态；邮件保持线性，不做折叠（客户端兼容性差）。
4. 复习日音频：目前只有讲解日有音频，复习日要看需求再补。
5. 第二类任务（AI 基础、资讯、历史）接入同一套生成/发送/归档流程，`site/` 入口页会自动聚合。
6. 查看与定制化学习：在 Pages 之上做 PWA / App。
