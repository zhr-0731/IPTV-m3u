#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
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

def generate_report():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    update_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    stats1 = read_stats_iptv4()
    stats2 = read_stats_iptv_org()
    
    report = f"""# IPTV M3U 播放列表

自动更新 IPTV 频道列表，每日检测可用性并去重汇总。  
**频道按字母顺序排列，失效频道自动移入 `*_dead.m3u`，恢复后自动回归。**

## 📊 本次更新报告

**更新时间**: {update_time} (UTC+8)

### 源 1: iptv4.m3u（央视频道/卫视频道/地方频道）

| 项目 | 数量 |
|------|------|
| 远程总频道数 | {stats1['remote_total'] if stats1 else 'N/A'} |
| 符合分类条件的频道 | {stats1['remote_target'] if stats1 else 'N/A'} |
| 更新前活跃频道 | {stats1['active_before'] if stats1 else 'N/A'} |
| **更新后活跃频道** | **{stats1['active_after'] if stats1 else 'N/A'}** |
| 失效频道数 | {stats1['dead_after'] if stats1 else 'N/A'} |
| 本次净增 | {stats1['new_added'] if stats1 else 'N/A'} |

- 活跃列表：[`index.m3u`](./index.m3u)  
- 失效列表：[`index_dead.m3u`](./index_dead.m3u)

### 源 2: iptv-org（国际频道）

| 项目 | 数量 |
|------|------|
| 远程总频道数 | {stats2['remote_total'] if stats2 else 'N/A'} |
| 更新前活跃频道 | {stats2['active_before'] if stats2 else 'N/A'} |
| **更新后活跃频道** | **{stats2['active_after'] if stats2 else 'N/A'}** |
| 失效频道数 | {stats2['dead_after'] if stats2 else 'N/A'} |
| 本次净增 | {stats2['new_added'] if stats2 else 'N/A'} |

- 活跃列表：[`iptv-org.m3u`](./iptv-org.m3u)  
- 失效列表：[`iptv-org_dead.m3u`](./iptv-org_dead.m3u)

## 🕐 更新频率

本仓库通过 GitHub Actions 每日自动更新（北京时间凌晨 2:00）。

---
*最后更新: {update_time}*
"""
    return report

def main():
    report = generate_report()
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("[报告] README.md 已更新")
    
    for f in [".stats_iptv4.txt", ".stats_iptv_org.txt"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    main()