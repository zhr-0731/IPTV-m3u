#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import json
import os
from urllib.parse import quote

# 配置
API_BASE = "https://de1.api.radio-browser.info/json/stations"
HEADERS = {"User-Agent": "M3UGenerator/1.0 (https://github.com/your-repo)"}
LIMIT = 1000          # 单次最大数量
OUTPUT_FILES = {
    "global": "radio-global.m3u",
    "CN": "radio-CN.m3u",
    "US": "radio-US.m3u",
    "GB": "radio-UK.m3u"   # 英国代码是 GB，但文件名用 UK
}

def fetch_all_stations():
    """分页获取所有电台"""
    stations = []
    offset = 0
    while True:
        url = f"{API_BASE}?limit={LIMIT}&offset={offset}"
        print(f"Fetching offset {offset}...")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            break
        data = resp.json()
        if not data:
            break
        stations.extend(data)
        offset += LIMIT
        time.sleep(0.5)  # 避免频率限制
    return stations

def escape_m3u_text(text):
    """转义M3U中的特殊字符（逗号）"""
    if text is None:
        return ""
    return text.replace(",", "\\,")

def generate_m3u_content(stations):
    """生成M3U内容（与之前相同）"""
    lines = ["#EXTM3U"]
    for s in stations:
        name = s.get("name", "Unknown").strip()
        url = s.get("url_resolved") or s.get("url")
        if not url:
            continue

        # 构建扩展属性
        extinf_parts = ["-1"]
        if s.get("favicon"):
            extinf_parts.append(f'tvg-logo="{s["favicon"]}"')
        if name:
            extinf_parts.append(f'tvg-name="{escape_m3u_text(name)}"')
        tags = s.get("tags", "").split(",") if s.get("tags") else []
        group = tags[0].strip() if tags else s.get("country", "Unknown")
        if group:
            extinf_parts.append(f'group-title="{escape_m3u_text(group)}"')
        if s.get("country"):
            extinf_parts.append(f'country="{escape_m3u_text(s["country"])}"')
        if s.get("language"):
            extinf_parts.append(f'language="{escape_m3u_text(s["language"])}"')
        if s.get("bitrate"):
            extinf_parts.append(f'bitrate="{s["bitrate"]}"')
        if s.get("codec"):
            extinf_parts.append(f'codec="{escape_m3u_text(s["codec"])}"')

        title_parts = [name]
        if s.get("country"):
            title_parts.append(s["country"])
        if s.get("bitrate"):
            title_parts.append(f"{s['bitrate']}kbps")
        title = " - ".join(title_parts)

        extinf_line = "#EXTINF:" + " ".join(extinf_parts) + f",{escape_m3u_text(title)}"
        lines.append(extinf_line)
        lines.append(url)
    return "\n".join(lines)

def main():
    print("Fetching all stations...")
    stations = fetch_all_stations()
    print(f"Total stations: {len(stations)}")
    if not stations:
        print("No stations fetched.")
        return

    # 生成全局
    print("Generating global M3U...")
    with open(OUTPUT_FILES["global"], "w", encoding="utf-8") as f:
        f.write(generate_m3u_content(stations))

    # 按国家过滤
    for code, filename in OUTPUT_FILES.items():
        if code == "global":
            continue
        filtered = [s for s in stations if s.get("countrycode") == code]
        print(f"Generating {filename} with {len(filtered)} stations (code {code})")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(generate_m3u_content(filtered))

    print("All M3U files generated successfully.")

if __name__ == "__main__":
    main()