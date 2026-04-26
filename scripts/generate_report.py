#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timezone, timedelta

def read_stats_iptv4():
    stats_file = ".stats_iptv4.txt"
    if not os.path.exists(stats_file):
        return None
    with open(stats_file, "r", encoding="utf-8") as f:
        lines = f.read().strip().split("\n")
    if len(lines) >= 6:
        return {
            "remote_total": int(lines[0]),
            "remote_target": int(lines[1]),
            "active_before": int(lines[2]),
            "active_after": int(lines[3]),
            "dead_after": int(lines[4]),
            "new_added": int(lines[5])
        }
    return None

def read_stats_iptv_org():
    stats_file = ".stats_iptv_org.txt"
    if not os.path.exists(stats_file):
        return None
    with open(stats_file, "r", encoding="utf-8") as f:
        lines = f.read().strip().split("\n")
    if len(lines) >= 5:
        return {
            "remote_total": int(lines[0]),
            "active_before": int(lines[1]),
            "active_after": int(lines[2]),
            "dead_after": int(lines[3]),
            "new_added": int(lines[4])
        }
    return None

def count_channels_in_m3u(filepath):
    if not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("#EXTINF:"):
                count += 1
    return count

def generate_report():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    update_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    stats1 = read_stats_iptv4()
    stats2 = read_stats_iptv_org()
    count1 = count_channels_in_m3u("index.m3u")
    count2 = count_channels_in_m3u("iptv-org.m3u")
    
    report = f"""# IPTV M3U 播放列表

自动更新 IPTV 频道列表，每日检测可用性并去重汇总。  
**频道按字母顺序排列，失效频道自动移入 `*_dead.m3u`，恢复后自动回归。**

## 📊 本次更新报告

**更新时间**: {update_time} (UTC+8)

### 源 1: iptv4.m3u（央视频道/卫视频道/地方频道）→ `index.m3u`

| 项目 | 数量 |
|------|------|
| 远程总频道数 | {stats1['remote_total'] if stats1 else 'N/A'} |
| 符合分类条件的频道 | {stats1['remote_target'] if stats1 else 'N/A'} |
| 更新前活跃频道 | {stats1['active_before'] if stats1 else 'N/A'} |
| **更新后活跃频道** | **{stats1['active_after'] if stats1 else 'N/A'}** |
| 失效频道数 | {stats1['dead_after'] if stats1 else 'N/A'} |
| 本次净增 | {stats1['new_added'] if stats1 else 'N/A'} |
| **累计总数** | **{count1}** |

- 活跃列表：[`index.m3u`](./index.m3u)  
- 失效列表：[`index_dead.m3u`](./index_dead.m3u)

### 源 2: iptv-org（国际频道）→ `iptv-org.m3u`

| 项目 | 数量 |
|------|------|
| 远程总频道数 | {stats2['remote_total'] if stats2 else 'N/A'} |
| 更新前活跃频道 | {stats2['active_before'] if stats2 else 'N/A'} |
| **更新后活跃频道** | **{stats2['active_after'] if stats2 else 'N/A'}** |
| 失效频道数 | {stats2['dead_after'] if stats2 else 'N/A'} |
| 本次净增 | {stats2['new_added'] if stats2 else 'N/A'} |
| **累计总数** | **{count2}** |

- 活跃列表：[`iptv-org.m3u`](./iptv-org.m3u)  
- 失效列表：[`iptv-org_dead.m3u`](./iptv-org_dead.m3u)

## 🕐 更新频率

本仓库通过 GitHub Actions 每日自动更新（北京时间凌晨 2:00）。

---
*最后更新: {update_time}*

## 📸 仪表盘截图

![IPTV 仪表盘](img/dashboard.png)
"""
    return report, update_time, stats1, stats2, count1, count2

def send_feishu_message(stats1, stats2, update_time, count1, count2):
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if not webhook:
        print("[飞书] 未设置 FEISHU_WEBHOOK，跳过通知")
        return
    
    content = [
        [{"tag": "text", "text": "📡 IPTV 每日更新报告"}],
        [{"tag": "text", "text": f"⏱ 更新时间：{update_time}"}],
        [{"tag": "text", "text": "━━━━━━━━━━━━━━━"}],
        [{"tag": "text", "text": "📺 央视频道/卫视频道/地方频道"}],
        [{"tag": "text", "text": f"活跃：{stats1['active_after'] if stats1 else 'N/A'} | 失效：{stats1['dead_after'] if stats1 else 'N/A'} | 净增：{stats1['new_added'] if stats1 else 'N/A'}"}],
        [{"tag": "text", "text": f"累计总数：{count1}"}],
        [{"tag": "text", "text": "🌍 国际频道"}],
        [{"tag": "text", "text": f"活跃：{stats2['active_after'] if stats2 else 'N/A'} | 失效：{stats2['dead_after'] if stats2 else 'N/A'} | 净增：{stats2['new_added'] if stats2 else 'N/A'}"}],
        [{"tag": "text", "text": f"累计总数：{count2}"}],
        [{"tag": "text", "text": "🔗 链接：https://github.com/zhr-0731/IPTV-m3u"}]
    ]
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "IPTV M3U 每日更新"}
            },
            "elements": [
                {"tag": "div", "fields": [{"is_short": False, "text": {"tag": "lark_md", "content": "\n".join([c[0]["text"] for c in content])}}]}
            ]
        }
    }
    
    try:
        resp = requests.post(webhook, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[飞书] 通知发送成功")
        else:
            print(f"[飞书] 发送失败: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[飞书] 请求异常: {e}")

def generate_json(stats1, stats2, update_time, count1, count2):
    data = {
        "update_time": update_time,
        "source1": {
            "name": "iptv4 (央视频道/卫视频道/地方频道)",
            "remote_total": stats1["remote_total"] if stats1 else None,
            "remote_target": stats1["remote_target"] if stats1 else None,
            "active_before": stats1["active_before"] if stats1 else None,
            "active_after": stats1["active_after"] if stats1 else None,
            "dead": stats1["dead_after"] if stats1 else None,
            "new_added": stats1["new_added"] if stats1 else None,
            "total": count1
        },
        "source2": {
            "name": "iptv-org (国际频道)",
            "remote_total": stats2["remote_total"] if stats2 else None,
            "active_before": stats2["active_before"] if stats2 else None,
            "active_after": stats2["active_after"] if stats2 else None,
            "dead": stats2["dead_after"] if stats2 else None,
            "new_added": stats2["new_added"] if stats2 else None,
            "total": count2
        }
    }
    return data

def main():
    report, update_time, stats1, stats2, count1, count2 = generate_report()
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("[报告] README.md 已更新")
    
    json_data = generate_json(stats1, stats2, update_time, count1, count2)
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("[报告] report.json 已更新")
    
    send_feishu_message(stats1, stats2, update_time, count1, count2)
    
    for f in [".stats_iptv4.txt", ".stats_iptv_org.txt"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    main()