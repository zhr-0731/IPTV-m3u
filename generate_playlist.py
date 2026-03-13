import requests
import xml.etree.ElementTree as ET
import random
from email.utils import parsedate_to_datetime
from datetime import datetime
import os
from typing import List, Dict, Optional, Tuple

# 源URL
URLS = [
    "http://zhr-0731.github.io/IPTV-m3u/music.m3u",
    "https://data.getpodcast.xyz/data/ximalaya/31903470.xml",
    "https://data.getpodcast.xyz/data/ximalaya/101474678.xml",
    "https://data.getpodcast.xyz/data/ximalaya/89148451.xml"
]

OUTPUT_FILE = "playlist.m3u"
TIMEOUT = 30

def fetch_text(url: str) -> Optional[str]:
    """获取URL文本内容，失败返回None"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers=headers)
        resp.raise_for_status()
        if 'charset' in resp.headers.get('content-type', ''):
            return resp.text
        try:
            return resp.content.decode('utf-8')
        except UnicodeDecodeError:
            return resp.content.decode('latin1')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_m3u(content: str) -> List[str]:
    lines = content.splitlines()
    return lines

def parse_podcast_xml(content: str) -> List[Dict]:
    items = []
    try:
        root = ET.fromstring(content)
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            enclosure = item.find('enclosure')
            pubDate_elem = item.find('pubDate')

            title = title_elem.text.strip() if title_elem is not None else "未知标题"
            url = enclosure.get('url') if enclosure is not None else None
            pubDate_str = pubDate_elem.text.strip() if pubDate_elem is not None else None

            if not url:
                continue

            pubDate = None
            if pubDate_str:
                try:
                    pubDate = parsedate_to_datetime(pubDate_str)
                except:
                    pass

            items.append({
                'title': title,
                'url': url,
                'pubDate': pubDate
            })
    except Exception as e:
        print(f"XML parse error: {e}")
    return items

def select_random_items(items: List[Dict], count: int) -> List[Dict]:
    if not items:
        return []
    return random.sample(items, min(count, len(items)))

def select_latest_item(items: List[Dict]) -> Optional[Dict]:
    if not items:
        return None
    dated_items = [it for it in items if it['pubDate'] is not None]
    if dated_items:
        return max(dated_items, key=lambda it: it['pubDate'])
    else:
        return random.choice(items)

def build_m3u(orig_lines: List[str],
              fourth_item: Optional[Dict],
              second_items: List[Dict],
              third_item: Optional[Dict]) -> str:
    lines = ['#EXTM3U']

    if fourth_item:
        lines.append(f'#EXTINF:-1,{fourth_item["title"]}')
        lines.append(fourth_item['url'])

    start_idx = 0
    if orig_lines and orig_lines[0].startswith('#EXTM3U'):
        start_idx = 1
    for line in orig_lines[start_idx:]:
        if line.strip():
            lines.append(line)

    for item in second_items:
        lines.append(f'#EXTINF:-1,{item["title"]}')
        lines.append(item['url'])

    if third_item:
        lines.append(f'#EXTINF:-1,{third_item["title"]}')
        lines.append(third_item['url'])

    return '\n'.join(lines)

def main():
    print("开始获取源数据...")

    m3u_content = fetch_text(URLS[0])
    if m3u_content is None:
        print("警告：无法获取第一个链接，将使用空列表")
        orig_lines = []
    else:
        orig_lines = parse_m3u(m3u_content)
        print(f"第一个链接获取到 {len(orig_lines)} 行")

    xml2_content = fetch_text(URLS[1])
    items2 = parse_podcast_xml(xml2_content) if xml2_content else []
    print(f"第二个链接解析到 {len(items2)} 个条目")
    second_items = select_random_items(items2, 4)

    xml3_content = fetch_text(URLS[2])
    items3 = parse_podcast_xml(xml3_content) if xml3_content else []
    print(f"第三个链接解析到 {len(items3)} 个条目")
    third_item = select_latest_item(items3)

    xml4_content = fetch_text(URLS[3])
    items4 = parse_podcast_xml(xml4_content) if xml4_content else []
    print(f"第四个链接解析到 {len(items4)} 个条目")
    fourth_item = random.choice(items4) if items4 else None

    final_m3u = build_m3u(orig_lines, fourth_item, second_items, third_item)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_m3u)

    print(f"播放列表已生成：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
