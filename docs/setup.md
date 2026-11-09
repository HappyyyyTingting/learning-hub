# 部署与配置

本文从零配置一个 `learning-hub` 仓库；当前只启用 Daily English 一个任务。

## 1. 建仓库

```bash
cd learning-hub
git init -b main
git add .
git commit -m "chore: scaffold daily english push"
git remote add origin git@github.com:<你的账号>/learning-hub.git
git push -u origin main
```

私有仓库即可。工作流需要写权限把当天内容和 `state/sent.json` 提交回仓库。

## 2. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**。

必填：

| Secret | 说明 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API key，需要能访问 `deepseek-flash` / `deepseek-v4-pro` |
| `MAIL_TO` | 收件人，多个用逗号分隔 |
| `MAIL_FROM` | 发件人，例如 `Daily English <daily@yourdomain.com>` |
| `EMAIL_PROVIDER` | `smtp` 或 `resend` |

SMTP 方式（`EMAIL_PROVIDER=smtp`）：

| Secret | 说明 |
| --- | --- |
| `SMTP_HOST` | 例如 `smtp.qq.com`、`smtp.resend.com` |
| `SMTP_PORT` | `465`（SSL）或 `587`（STARTTLS） |
| `SMTP_USER` | 登录账号 |
| `SMTP_PASSWORD` | 密码或授权码；QQ / Foxmail 必须用授权码 |
| `SMTP_SECURITY` | `ssl`、`starttls` 或 `none`，留空时按端口推断 |

Resend 方式（`EMAIL_PROVIDER=resend`）：

| Secret | 说明 |
| --- | --- |
| `RESEND_API_KEY` | Resend API key |

可选：

| Secret | 说明 |
| --- | --- |
| `MAIL_REPLY_TO` | 回复地址 |

发件地址必须与 SMTP / Resend 已验证的域名或邮箱匹配，否则会发送失败。

## 3. 开启 Pages

**Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。

站点地址默认是 `https://<owner>.github.io/<repo>/`。如果使用自定义域名，添加仓库变量或 secret `SITE_URL`（工作流里用 `vars.SITE_URL` 读取，如需 secret 请改工作流），邮件底部的“查看往期推送”会使用它。

## 4. 第一次运行

1. 打开 **Actions → Daily English push → Run workflow**。
2. `date` 留空，`dry_run` 勾选 **true**，运行。
3. 运行结束后在该次运行页面底部下载 `email-preview` artifact，打开 `email.html` 检查排版和内容。
4. 确认无误后，再运行一次，`dry_run` 不勾选。这次会真实发送邮件、提交内容、部署 Pages。
5. 检查邮箱和 `https://<owner>.github.io/<repo>/`。

之后每个 UTC 23:30（北京时间 07:30）自动运行。第一次定时可能不会立刻出现，GitHub 对新工作流的 schedule 有短暂延迟。

## 5. 工作流做什么

`daily.yml` 的 `daily` job：

1. 跑单元测试。
2. 按北京时间确定日期。
3. `generate.py` 生成内容；已存在则跳过。
4. `send_email.py` 发邮件；`state/sent.json` 已记录则跳过。
5. `build_site.py` 构建 `site/`。
6. 提交 `content/english/<date>.json` 和 `state/sent.json`。
7. 上传 Pages artifact。

`deploy` job 部署 Pages；`alert` job 在任一环节失败时发告警邮件。

## 6. 常见问题

**没有收到邮件**

- 看 Actions 日志里 `Send email` 这一步是否失败。
- SMTP 登录失败通常是授权码而不是登录密码；QQ 邮箱需要在设置里开启 SMTP 并生成授权码。
- Resend 需要先验证发件域名；测试阶段只能用 `onboarding@resend.dev` 发给自己的账号邮箱。
- 检查垃圾邮件目录。

**工作流没有按点运行**

- GitHub 的 schedule 只跑默认分支，且高峰期可能延迟。
- 仓库连续 60 天没有任何活动时，GitHub 可能暂停 schedule；本工作流每天提交内容，一般不会触发。
- 可以随时用 `workflow_dispatch` 手动补跑。

**同一天重复发送**

- 正常不会：发送成功后才写 `state/sent.json`。如果邮件已收到但日志显示提交失败，重跑前先手动确认。
- 确实要重发：`workflow_dispatch` 时无法直接传 `--force`，可以本地运行 `python scripts/send_email.py --date <date> --force`，或临时改工作流。

**想换模型**

改 `tasks/english/config.yml`：

```yaml
model: deepseek-v4-pro
```

或本地用 `--model` 覆盖。降级前建议先连续对比几天内容质量。

**想改发送时间**

改 `.github/workflows/daily.yml` 的 cron。注意 cron 是 UTC：

- 北京 07:30 → `30 23 * * *`（前一天 UTC）
- 北京 08:00 → `0 0 * * *`

**想先不部署 Pages**

删除或注释 `Upload Pages artifact` 和 `deploy` job 即可，邮件发送不受影响。

## 7. 安全与隐私

- API key、邮箱密码只放在 GitHub Secrets，不写进仓库。
- 内容会提交到仓库；如果仓库公开，每天的学习内容也会公开。介意的话用私有仓库。
- 邮件里的外链只有往期归档地址；内容本身由模型生成，渲染时全部做了 HTML 转义。
