import requests
import time
import json
import os
from urllib.parse import quote

# 配置
API_BASE = "https://de1.api.radio-browser.info/json/stations"
HEADERS = {"User-Agent": "M3UGenerator/1.0 (https://github.com/your-repo)"}
LIMIT = 1000          # 单次最大数量
OUTPUT_FILE = "radio-2.m3u"

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

def generate_m3u(stations):
    """生成M3U内容"""
    lines = ["#EXTM3U"]
    for s in stations:
        name = s.get("name", "Unknown").strip()
        url = s.get("url_resolved") or s.get("url")
        if not url:
            continue

        # 构建扩展属性
        extinf_parts = ["-1"]  # 时长，-1表示未知
        # tvg-logo
        if s.get("favicon"):
            extinf_parts.append(f'tvg-logo="{s["favicon"]}"')
        # tvg-name
        if name:
            extinf_parts.append(f'tvg-name="{escape_m3u_text(name)}"')
        # group-title（取第一个标签，若无则用国家）
        tags = s.get("tags", "").split(",") if s.get("tags") else []
        group = tags[0].strip() if tags else s.get("country", "Unknown")
        if group:
            extinf_parts.append(f'group-title="{escape_m3u_text(group)}"')
        # 自定义属性：国家、语言、比特率、编码
        if s.get("country"):
            extinf_parts.append(f'country="{escape_m3u_text(s["country"])}"')
        if s.get("language"):
            extinf_parts.append(f'language="{escape_m3u_text(s["language"])}"')
        if s.get("bitrate"):
            extinf_parts.append(f'bitrate="{s["bitrate"]}"')
        if s.get("codec"):
            extinf_parts.append(f'codec="{escape_m3u_text(s["codec"])}"')
        # 也可添加其他字段如 countrycode, state 等

        # 标题：显示名称、国家、比特率等（以便在没有扩展播放器时能看到）
        title_parts = [name]
        if s.get("country"):
            title_parts.append(s["country"])
        if s.get("bitrate"):
            title_parts.append(f"{s['bitrate']}kbps")
        title = " - ".join(title_parts)

        # 组装 #EXTINF 行
        extinf_line = "#EXTINF:" + " ".join(extinf_parts) + f",{escape_m3u_text(title)}"
        lines.append(extinf_line)
        lines.append(url)  # URL单独一行
    return "\n".join(lines)

def main():
    print("Fetching all stations...")
    stations = fetch_all_stations()
    print(f"Total stations: {len(stations)}")
    if not stations:
        print("No stations fetched.")
        return
    m3u_content = generate_m3u(stations)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()