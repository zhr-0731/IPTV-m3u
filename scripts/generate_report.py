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
    if len(lines) >= 4:
        return {
            "total": int(lines[0]),
            "target": int(lines[1]),
            "valid": int(lines[2]),
            "new": int(lines[3])
        }
    return None

def read_stats_iptv_org():
    stats_file = ".stats_iptv_org.txt"
    if not os.path.exists(stats_file):
        return None
    with open(stats_file, "r", encoding="utf-8") as f:
        lines = f.read().strip().split("\n")
    if len(lines) >= 3:
        return {
            "total": int(lines[0]),
            "valid": int(lines[1]),
            "new": int(lines[2])
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

## 📊 本次更新报告

**更新时间**: {update_time} (UTC+8)

### 源 1: iptv4.m3u（央视频道/卫视频道/地方频道）→ `index.m3u`

| 项目 | 数量 |
|------|------|
| 总频道数 | {stats1['total'] if stats1 else 'N/A'} |
| 符合分类条件的频道 | {stats1['target'] if stats1 else 'N/A'} |
| 可用频道 | {stats1['valid'] if stats1 else 'N/A'} |
| 本次新增 | {stats1['new'] if stats1 else 'N/A'} |
| **当前累计频道数** | **{count1}** |

### 源 2: iptv-org（全量频道）→ `iptv-org.m3u`

| 项目 | 数量 |
|------|------|
| 总频道数 | {stats2['total'] if stats2 else 'N/A'} |
| 可用频道 | {stats2['valid'] if stats2 else 'N/A'} |
| 本次新增 | {stats2['new'] if stats2 else 'N/A'} |
| **当前累计频道数** | **{count2}** |

## 🔗 播放列表链接

- **央视频道/卫视频道/地方频道**: [`index.m3u`](./index.m3u)
- **全量频道（无分类）**: [`iptv-org.m3u`](./iptv-org.m3u)

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