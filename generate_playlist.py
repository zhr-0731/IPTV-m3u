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

# 输出文件名
OUTPUT_FILE = "playlist.m3u"

# 请求超时（秒）
TIMEOUT = 30

def fetch_text(url: str) -> Optional[str]:
    """获取URL文本内容，失败返回None"""
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        # 尝试正确解码（有时xml头可能不是utf-8）
        if 'charset' in resp.headers.get('content-type', ''):
            return resp.text
        # 手动检测：先用utf-8，失败则用latin1
        try:
            return resp.content.decode('utf-8')
        except UnicodeDecodeError:
            return resp.content.decode('latin1')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_m3u(content: str) -> List[str]:
    """解析m3u文件，返回所有行（保留原格式）"""
    lines = content.splitlines()
    # 如果存在#EXTM3U头部，后面保留（但我们会重新添加头部，所以这里可忽略）
    # 直接返回所有行，后续构建时会跳过自身的头部
    return lines

def parse_podcast_xml(content: str) -> List[Dict]:
    """
    解析喜马拉雅播客XML，返回条目列表，每个条目包含：
    - title: 标题
    - url: 音频URL (enclosure的url属性)
    - pubDate: datetime对象（可能为None）
    """
    items = []
    try:
        root = ET.fromstring(content)
        # 查找所有item
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
    """随机选择count个条目，如果总数小于count则全部返回"""
    if not items:
        return []
    return random.sample(items, min(count, len(items)))

def select_latest_item(items: List[Dict]) -> Optional[Dict]:
    """选择pubDate最新的条目，如果没有日期则随机"""
    if not items:
        return None
    # 过滤掉没有pubDate的条目
    dated_items = [it for it in items if it['pubDate'] is not None]
    if dated_items:
        return max(dated_items, key=lambda it: it['pubDate'])
    else:
        return random.choice(items)

def build_m3u(orig_lines: List[str],
              fourth_item: Optional[Dict],
              second_items: List[Dict],
              third_item: Optional[Dict]) -> str:
    """
    构建最终m3u内容
    - 先写#EXTM3U
    - 然后第四项（如果有）
    - 接着原始m3u内容（跳过它自己的#EXTM3U行）
    - 然后第二项（4条）
    - 最后第三项（最新）
    """
    lines = ['#EXTM3U']

    # 第四项（随机，放在最前）
    if fourth_item:
        lines.append(f'#EXTINF:-1,{fourth_item["title"]}')
        lines.append(fourth_item['url'])

    # 原始m3u内容，跳过可能的第一行#EXTM3U
    start_idx = 0
    if orig_lines and orig_lines[0].startswith('#EXTM3U'):
        start_idx = 1
    for line in orig_lines[start_idx:]:
        if line.strip():  # 保留非空行
            lines.append(line)

    # 第二项（随机4条）
    for item in second_items:
        lines.append(f'#EXTINF:-1,{item["title"]}')
        lines.append(item['url'])

    # 第三项（最新）
    if third_item:
        lines.append(f'#EXTINF:-1,{third_item["title"]}')
        lines.append(third_item['url'])

    return '\n'.join(lines)

def main():
    print("开始获取源数据...")

    # 1. 获取第一个链接（music.m3u）
    m3u_content = fetch_text(URLS[0])
    if m3u_content is None:
        print("警告：无法获取第一个链接，将使用空列表")
        orig_lines = []
    else:
        orig_lines = parse_m3u(m3u_content)
        print(f"第一个链接获取到 {len(orig_lines)} 行")

    # 2. 获取第二个链接（XML）
    xml2_content = fetch_text(URLS[1])
    items2 = parse_podcast_xml(xml2_content) if xml2_content else []
    print(f"第二个链接解析到 {len(items2)} 个条目")
    second_items = select_random_items(items2, 4)  # 随机选4条

    # 3. 获取第三个链接（XML）
    xml3_content = fetch_text(URLS[2])
    items3 = parse_podcast_xml(xml3_content) if xml3_content else []
    print(f"第三个链接解析到 {len(items3)} 个条目")
    third_item = select_latest_item(items3)

    # 4. 获取第四个链接（XML）
    xml4_content = fetch_text(URLS[3])
    items4 = parse_podcast_xml(xml4_content) if xml4_content else []
    print(f"第四个链接解析到 {len(items4)} 个条目")
    fourth_item = random.choice(items4) if items4 else None

    # 构建最终m3u
    final_m3u = build_m3u(orig_lines, fourth_item, second_items, third_item)

    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_m3u)

    print(f"播放列表已生成：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
