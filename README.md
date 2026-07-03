# Ark API Auto Request & Snapshot

一个自动调用 Ark（火山引擎）LLM 接口、抓取「请求 + 响应」为本地 JSON 快照、并可选择通过 Telegram 推送执行结果的项目。

提供 **两套运行方式**，任选其一即可：

| 方式 | 适合谁 | 是否需要服务器 | 快照存放位置 |
|------|--------|:------------:|------------|
| **GitHub Actions** | 想用 GitHub 免费跑定时任务 | 否 | 仓库的 `snapshot` 分支 |
| **青龙面板 (QingLong)** | 已经在用青龙跑脚本 | 否（用青龙所在机器） | 脚本同级的 `snapshots/` 目录 |

两者共享同一套配置约定：

- **必填**：`ARK_API_KEY`
- **可选**：`API_URL`（默认 `https://ark.cn-beijing.volces.com/api/coding/v1/messages`）、`MODEL`（默认 `ark-code-latest`）
- **可选**：`TG_TOKEN` / `TG_CHAT_ID`（Telegram 推送，缺一则静默跳过）

---

## 方式一：GitHub Actions

### 1. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**：

| Name | Required | 说明 |
|------|:--------:|------|
| `ARK_API_KEY` | **是** | 火山引擎 Ark 的 API Key |
| `API_URL` | 否 | 留空使用默认值 |
| `MODEL` | 否 | 留空使用默认值 |
| `TG_TOKEN` | 否 | Telegram Bot Token |
| `TG_CHAT_ID` | 否 | Telegram 会话 ID |

### 2. 推送代码并启用 Actions

```bash
git add .
git commit -m "feat: add auto request & snapshot"
git push
```

**Settings → Actions → General** 设置：

- **Actions permissions**：`Allow all actions and reusable workflows`
- **Workflow permissions**：`Read and write permissions`（workflow 需要把快照 push 到 `snapshot` 分支）

### 3. 验证

- **Actions → Auto API Request & Snapshot → Run workflow** 手动触发一次。
- 成功后，仓库的 **`snapshot` 分支** 会出现 `snapshots/snapshot_YYYYMMDD_HHMMSS.json`。

### 4. 之后就可以不管了

定时触发按计划跑，新快照自动提交到 `snapshot` 分支，**主分支保持干净**。

### Schedule 计划

北京时间 (UTC+8)  |  UTC Cron
-------------------|-----------
每天 06:00         | `0 22 * * *`
每天 11:01         | `1 3 * * *`
每天 16:02         | `2 8 * * *`

> GitHub Actions 的 `schedule` 使用 **UTC** 时间，且只在默认分支生效。

### 分支策略

快照提交到独立的 **`snapshot` 分支**：

- 首次运行时基于默认分支 HEAD 创建 `snapshot` 分支。
- 之后所有运行产生的快照 append 到该分支。
- 主分支只保留工作代码，不会出现 `snapshots/` 的提交。

---

## 方式二：青龙面板 (QingLong)

### 1. 安装依赖

在青龙面板的「依赖管理」里添加 Python 依赖：

```
requests
pytz
```

或在宿主机执行：

```bash
pip install requests pytz --break-system-packages
```

### 2. 拉脚本

把 `qinglong_main.py` 放到青龙的脚本目录（例如 `/ql/data/scripts/ark_snapshot/`）。

### 3. 配置环境变量

在「环境变量」tab 新建：

| 名称 | 必填 | 值 |
|------|:---:|---|
| `ARK_API_KEY` | ✅ | 火山引擎 Ark 的 API Key |
| `API_URL` | ❌ | 留空使用默认值 |
| `MODEL` | ❌ | 留空使用默认值 |
| `TG_TOKEN` | ❌ | Telegram Bot Token |
| `TG_CHAT_ID` | ❌ | Telegram 会话 ID |

### 4. 添加定时任务

在「定时任务」tab 新建任务：

- **名称**：`Ark API 快照`
- **命令**：`task qinglong_main.py`（或 `task /ql/data/scripts/ark_snapshot/qinglong_main.py`，视你的脚本路径而定）
- **定时**：分别添加三条 cron

```
0 6 * * *      # 北京时间 06:00
0 11 * * *     # 北京时间 11:01
2 16 * * *     # 北京时间 16:02
```

> 青龙面板的 cron 默认就是**北京时间**，无需像 GitHub Actions 那样换算成 UTC。

### 5. 验证

手动「运行」一次，检查：

- 脚本同级出现 `snapshots/snapshot_YYYYMMDD_HHMMSS.json`
- 收到青龙通知（或 Telegram 推送）

### 通知机制

青龙版的通知是**双通道降级**的：

1. 优先使用青龙自带的 `notify.send`（你在「通知设置」里配了什么渠道，就用什么渠道）
2. 如果 `notify` 不可用（例如本地调试），降级到直接调用 Telegram Bot API
3. 如果连 `TG_TOKEN` / `TG_CHAT_ID` 也没配，静默跳过，**不会导致任务失败**

---

## 项目结构

```
.
├── main.py                        # GitHub Actions 版核心脚本
├── qinglong_main.py               # 青龙面板版核心脚本
├── requirements.txt               # Python 依赖（requests、pytz）
├── snapshots/                     # 自动生成的快照目录
├── .github/workflows/
│   └── auto_request.yml           # GitHub Actions 定时 / 手动触发配置
└── README.md
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

## 配置参考：全部环境变量一览

| Name | Required | Default / 行为 |
|------|:--------:|----------------|
| `ARK_API_KEY` | ✅ | 缺失则脚本退出并失败 |
| `API_URL` | ❌ | `https://ark.cn-beijing.volces.com/api/coding/v1/messages` |
| `MODEL` | ❌ | `ark-code-latest` |
| `TG_TOKEN` | ❌ | 与 `TG_CHAT_ID` 同时缺失则跳过推送 |
| `TG_CHAT_ID` | ❌ | 与 `TG_TOKEN` 同时缺失则跳过推送 |

> 注意：GitHub Actions 版 workflow 里把 `API_URL` 映射为 `secrets.BASE_URL`，青龙版直接用 `API_URL`。两者默认值相同。

## Telegram 推送配置（可选）

1. **找 @BotFather 创建 Bot**
   - 给 [@BotFather](https://t.me/BotFather) 发送 `/newbot`
   - 拿到形如 `123456:ABC-DEF...` 的 token → 这就是 `TG_TOKEN`

2. **获取 Chat ID**
   - 给 Bot 发一条消息（或把 Bot 拉进一个群）
   - 浏览器打开 `https://api.telegram.org/bot<TG_TOKEN>/getUpdates`
   - 返回的 JSON 里找 `chat.id`（个人 ID 是数字，群组 ID 是负数）→ 这就是 `TG_CHAT_ID`

> 个人推送和群组推送都支持。

## 常见问题

- **Q: GitHub Actions 定时任务没跑？**
  A: `schedule` 只在默认分支生效，且 GitHub 对长时间不活跃的仓库可能暂停 schedule。手动 `Run workflow` 一次通常能恢复。cron 有少量延迟（几分钟），不是精确触发。

- **Q: GitHub Actions 快照没被提交回来？**
  A: 检查 Workflow permissions 是否开启 `Read and write permissions`；确认 `ARK_API_KEY` 已填满；查看 workflow run 日志中 "Commit and push snapshot to snapshot branch" 步骤。

- **Q: 青龙版运行报 `ModuleNotFoundError: No module named 'requests'`？**
  A: 在「依赖管理」里添加 `requests` 和 `pytz`，或 `pip install requests pytz --break-system-packages`。

- **Q: 青龙版运行报 `ModuleNotFoundError: No module named 'notify'`？**
  A: 正常现象。脚本会自动降级到 Telegram 直连 API（需要 `TG_TOKEN` + `TG_CHAT_ID`），或静默跳过通知。

- **Q: 任务报错 `未配置必填环境变量: ARK_API_KEY`？**
  A: 环境变量名称必须**完全匹配**大小写，`ARK_API_KEY`，不是 `Ark_Api_Key` 也不是 `ARK_TOKEN`。

## License

MIT
