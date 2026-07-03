#!/usr/bin/env python3
"""
Ark API Auto Request & Snapshot — 青龙面板 (QingLong) 版本。

功能：
- 调用 Ark（火山引擎）LLM 接口
- 将「请求 + 响应」抓取为本地 JSON 快照，存到脚本同级 snapshots/ 目录
- 通过青龙 notify 推送执行结果（失败时也会推送）

配置（在「环境变量」tab 添加）：
- ARK_API_KEY  【必填】
- API_URL      【可选】默认 https://ark.cn-beijing.volces.com/api/coding/v1/messages
- MODEL        【可选】默认 ark-code-latest
- TG_TOKEN     【可选】Telegram Bot Token
- TG_CHAT_ID   【可选】Telegram 会话 ID

时间计划请在青龙「定时任务」tab 添加 cron：
  0 6 * * *     0 11 * * *     2 16 * * *
分别对应北京时间的 06:00、11:01、16:02。
"""

import json
import os
import sys
import traceback
from datetime import datetime

import pytz
import requests




def notify(title: str, content: str) -> None:
  
    """统一对外推送入口：优先使用青龙 notify，否则走 Telegram 直连 API。"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    print(f"[notify] 进入配置通知。{tg_token} , {tg_chat_id}")

    # 降级：直接走 Telegram Bot API（要求 TG_TOKEN 与 TG_CHAT_ID 同时存在）
    if tg_token and tg_chat_id:
        _send_telegram(tg_token, tg_chat_id, f"<b>{title}</b>\n\n{content}")
    else:
        print("[notify] 未配置青龙 notify 且 TG_TOKEN/TG_CHAT_ID 缺失，跳过通知。")


def _send_telegram(tg_token: str, tg_chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {"chat_id": tg_chat_id, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        print("[notify] Telegram 已送达。")
    except Exception as e:
        print(f"[notify] Telegram 推送失败: {e}")


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------
def get_env(name: str, default: str = None, required: bool = False):
    value = os.environ.get(name)
    if not value:
        if required:
            raise SystemExit(f"【错误】未配置必填环境变量: {name}")
        if default is not None:
            print(f"[config] {name} 未设置，使用默认值: {default}")
            return default
        return None
    return value


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def call_api(base_url: str, api_key: str, model: str):
    """调用 Ark API，返回 (success: bool, response_data: Any, request_payload: dict)。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    }
    payload = {
        "model": model,
        "max_tokens": 1024,
        "stream": False,
        "messages": [{"role": "user", "content": "Hello"}],
    }

    try:
        resp = requests.post(base_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return True, resp.json(), payload
    except requests.exceptions.Timeout:
        return False, "Request timed out after 60s", payload
    except requests.exceptions.HTTPError:
        return False, f"HTTP {resp.status_code}: {resp.text[:500]}", payload
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {e}", payload
    except json.JSONDecodeError:
        return False, f"Invalid JSON (status {resp.status_code}): {resp.text[:500]}", payload


def extract_reply_text(response_data) -> str:
    if not isinstance(response_data, dict):
        return str(response_data)
    try:
        for choice in response_data.get("choices", []) or []:
            content = (choice.get("message") or {}).get("content")
            if content:
                return content
        return json.dumps(response_data, ensure_ascii=False)
    except Exception:
        return str(response_data)




def main():
    print("=== Ark API 定时快照（青龙面板版）===")

    # 加载配置
    base_url = get_env(
        "API_URL", default="https://ark.cn-beijing.volces.com/api/coding/v1/messages"
    )
    api_key = get_env("ARK_API_KEY", required=True)  # 必填；缺失直接退出
    model = get_env("MODEL", default="ark-code-latest")

    print(f"[config] MODEL={model}")
    print(f"[config] API_URL={base_url}")

    # 调用 API
    success, response_data, request_payload = call_api(base_url, api_key, model)
    reply_text = extract_reply_text(response_data) if success else str(response_data)
    print(f"[result] {'成功' if success else '失败'}: {reply_text[:200]}...")

    # 汇总推送内容
    now_bj = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    title = "Ark 快照 ✅" if success else "Ark 快照 ❌"
    content = (
        f"模型: {model}\n"
        f"状态: {'成功' if success else '失败'}\n"
        f"时间: {now_bj}\n\n"
        f"回复:\n{reply_text}"
    )
    notify(title, content)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        # 兜底：顶层异常也推一份，防止青龙面板看不到原因
        traceback.print_exc()
        notify("Ark 快照 💥", f"脚本异常退出:\n{traceback.format_exc()[-3500:]}")
        sys.exit(1)
