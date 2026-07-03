# Ark API Auto Request & Snapshot

一个基于 **Python + GitHub Actions** 的自动化项目：每天定时调用 Ark（火山引擎）的 LLM 接口，把「请求 + 响应」抓取为本地 JSON 快照，并可选择性地通过 Telegram 推送执行结果。

- **定时触发**：北京时间每天 `06:00`、`11:01`、`16:02`
- **手动触发**：在 GitHub Actions 页面点击 `Run workflow` 即可
- **零服务器**：完全依赖 GitHub Actions，无需额外机器

## Quick Start

### 1. 配置 Secrets

进入你的仓库 **Settings → Secrets and variables → Actions → New repository secret**，至少填入必须项：

| Name | Required | 说明 |
|------|:--------:|------|
| `ARK_API_KEY` | **是** | 火山引擎 Ark 的 API Key（控制台获取） |
| `BASE_URL` | 否 | 留空则使用默认 `https://ark.cn-beijing.volces.com/api/coding/v1/messages` |
| `MODEL` | 否 | 留空则使用默认 `ark-code-latest` |
| `TG_TOKEN` | 否 | Telegram Bot Token，不填则静默跳过 Telegram 推送 |
| `TG_CHAT_ID` | 否 | Telegram 会话 ID，不填则静默跳过 Telegram 推送 |

> Telegram 推送是**完全可选**的。只要 `TG_TOKEN` 或 `TG_CHAT_ID` 中任意一个没填，脚本就会跳过推送并打印一条 INFO 日志，**不会导致任务失败**。只有 `ARK_API_KEY` 缺失会让脚本以非零状态退出。

### 2. 推送代码并启用 Actions

```bash
git add .
git commit -m "feat: add auto request & snapshot"
git push
```

确保仓库的 **Settings → Actions → General** 设置为：

- **Actions permissions**：`Allow all actions and reusable workflows`
- **Workflow permissions**：`Read and write permissions`（这样 workflow 才有权把快照 `git push` 回来）

### 3. 验证

- 进入 **Actions → Auto API Request & Snapshot → Run workflow** 手动触发一次。
- 成功后，仓库的 **`snapshot` 分支** 会出现 `snapshots/snapshot_YYYYMMDD_HHMMSS.json`，同时（如果配了 Telegram）Bot 会收到一条推送消息。

> 快照会被提交到独立的 `snapshot` 分支，**不会污染主分支**。

### 4. 之后就可以不管了

定时触发会自动按计划跑，新快照会被 workflow 自动提交到 `snapshot` 分支。

## 项目结构

```
.
├── main.py                        # 核心脚本：调用 API、存快照、发 Telegram
├── requirements.txt               # Python 依赖（requests、pytz）
├── snapshots/                     # 自动生成的快照目录（workflow 自动 commit）
└── .github/workflows/
    └── auto_request.yml           # GitHub Actions 定时 / 手动触发配置
```

## 快照格式示例

`snapshots/snapshot_20260703_060000.json`：

```json
{
  "timestamp": "2026-07-03T06:00:00+08:00",
  "success": true,
  "request": {
    "model": "ark-code-latest",
    "max_tokens": 1024,
    "stream": false,
    "messages": [{ "role": "user", "content": "Hello" }]
  },
  "response": {
    "choices": [{ "message": { "content": "Hello! How can I help you today?" } }]
  }
}
```

即使 API 调用失败，也会保存一份快照（`success: false`，`response` 字段为错误信息），方便排查。

## Schedule 计划

北京时间 (UTC+8)  |  UTC Cron
-------------------|-----------
每天 06:00         | `0 22 * * *`
每天 11:01         | `1 3 * * *`
每天 16:02         | `2 8 * * *`

> GitHub Actions 的 `schedule` 使用 **UTC** 时间，且只在默认分支上生效。

## 配置参考：全部 Secrets 一览

| Name | Required | Default / 行为 |
|------|:--------:|----------------|
| `ARK_API_KEY` | ✅ | 缺失则脚本退出并失败 |
| `BASE_URL` | ❌ | `https://ark.cn-beijing.volces.com/api/coding/v1/messages` |
| `MODEL` | ❌ | `ark-code-latest` |
| `TG_TOKEN` | ❌ | 与 `TG_CHAT_ID` 同时缺失则跳过推送 |
| `TG_CHAT_ID` | ❌ | 与 `TG_TOKEN` 同时缺失则跳过推送 |

## Telegram 推送配置（可选）

如果你需要 Telegram 通知，按下面两步拿到两个值：

1. **找 @BotFather 创建 Bot**
   - 给 [@BotFather](https://t.me/BotFather) 发送 `/newbot`
   - 按提示设置名称，拿到形如 `123456:ABC-DEF...` 的 token → 这就是 `TG_TOKEN`

2. **获取 Chat ID**
   - 给 Bot 发一条消息（或把 Bot 拉进一个群）
   - 浏览器打开 `https://api.telegram.org/bot<TG_TOKEN>/getUpdates`
   - 返回的 JSON 里找 `chat.id`，可能是个人 ID（数字）或群组 ID（负数）→ 这就是 `TG_CHAT_ID`

> 个人推送和群组推送都支持，只要把 `chat.id` 填进去即可。

## 分支策略

为了避免污染主分支，快照会被提交到独立的 **`snapshot` 分支**：

- 首次运行时，workflow 会基于默认分支 HEAD 创建 `snapshot` 分支。
- 之后所有定时/手动运行产生的快照都 append 到该分支。
- 主分支只保留工作代码（`main.py`、`requirements.txt`、workflow 等），完全不会出现 `snapshots/` 目录的提交。

你可以在仓库里切换到 `snapshot` 分支查看历史快照，默认分支不受影响。

- **Q: 定时任务没跑？**
  A: `schedule` 只在默认分支生效，且 GitHub 对长时间不活跃的仓库可能暂停 schedule。手动 `Run workflow` 一次通常能恢复。另外 GitHub 对 cron 有少量延迟（几分钟），不是精确触发。

- **Q: 快照没被提交回来？**
  A: 检查 Workflow permissions 是否开启 `Read and write permissions`（workflow 需要推送到 `snapshot` 分支）；确认 `ARK_API_KEY` 已填满；查看对应 workflow run 的日志中 "Commit and push snapshot to snapshot branch" 步骤。

- **Q: `snapshot` 分支没有被创建？**
  A: 首次运行会自动创建。如果是手动运行且创建失败，确认 `GITHUB_TOKEN` 有写权限（Workflow permissions = Read and write）。

- **Q: 任务报错 `Missing required environment variable: ARK_API_KEY`？**
  A: Secret 名字必须**完全匹配**大小写，`ARK_API_KEY`，不是 `Ark_Api_Key` 也不是 `ARK_TOKEN`。

## License

MIT
