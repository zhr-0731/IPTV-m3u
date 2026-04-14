#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import concurrent.futures
import os
import sys

# ================== 配置 ==================
M3U_URL = "https://live.zbds.top/tv/iptv4.m3u"
INDEX_FILE = "index.m3u"
TIMEOUT = 5                # 单个流检测超时（秒）
MAX_WORKERS = 20           # 并发检测线程数
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 仅保留这三个 group-title 值（精确匹配，忽略首尾空格）
TARGET_GROUPS = {"央视频道", "卫视频道", "地方频道"}

# ================== 工具函数 ==================
def fetch_m3u_content(url):
    """下载 M3U 文件内容"""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"[错误] 无法获取 M3U 文件: {e}")
        return None

def parse_m3u(content):
    """
    解析 M3U 内容，返回条目列表，每个条目为字典：
    {
        "extinf": 原始 EXTINF 行（完整保留，含 group-title）,
        "name": 频道名称（用于去重）,
        "url": 流地址,
        "group": 解析出的 group-title 值（已 strip）
    }
    """
    entries = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            extinf = line
            # 提取 group-title
            group_match = re.search(r'group-title="([^"]*)"', extinf)
            group = group_match.group(1).strip() if group_match else ""
            
            # 提取频道名称（用于去重）
            name_match = re.search(r'tvg-name="([^"]+)"', extinf)
            if not name_match:
                parts = extinf.split(',', 1)
                name = parts[1].strip() if len(parts) > 1 else "未知频道"
            else:
                name = name_match.group(1).strip()
            
            # 获取下一行的 URL
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    entries.append({
                        "extinf": extinf,
                        "name": name,
                        "url": url,
                        "group": group
                    })
            i += 2
        else:
            i += 1
    return entries

def check_stream(url):
    """检测单个流是否可用（返回 True/False）"""
    try:
        resp = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code < 400:
            return True
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True)
        if resp.status_code < 400:
            for _ in resp.iter_content(1024):
                break
            return True
    except Exception:
        pass
    return False

def load_existing_names(index_path):
    """从现有 index.m3u 读取所有频道名称（用于去重）"""
    names = set()
    if not os.path.exists(index_path):
        return names
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        entries = parse_m3u(content)
        for e in entries:
            names.add(e["name"])
    except Exception as e:
        print(f"[警告] 读取现有 index.m3u 失败: {e}")
    return names

def write_m3u(index_path, entries, mode='a'):
    """
    将条目列表写入 M3U 文件
    mode='a' 追加写入（用于增量更新）
    """
    with open(index_path, mode, encoding='utf-8') as f:
        if mode == 'w':
            f.write("#EXTM3U\n")
        for e in entries:
            f.write(e["extinf"] + "\n")
            f.write(e["url"] + "\n")
    print(f"[完成] 已写入 {len(entries)} 个新条目到 {index_path}")

def main():
    print(f"[开始] 获取远程 M3U 文件: {M3U_URL}")
    content = fetch_m3u_content(M3U_URL)
    if not content:
        sys.exit(1)
    
    print("[解析] 解析 M3U 条目...")
    all_entries = parse_m3u(content)
    print(f"[解析] 共 {len(all_entries)} 个频道")
    
    # 仅保留 group-title 属于目标三类的频道
    target_entries = [e for e in all_entries if e["group"] in TARGET_GROUPS]
    print(f"[筛选] 符合 group-title 要求的频道: {len(target_entries)} 个")
    
    if not target_entries:
        print("[结束] 没有符合条件的频道，退出。")
        return
    
    # 并发检测流可用性
    print("[检测] 正在并发测试流可用性...")
    valid_entries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_entry = {executor.submit(check_stream, e["url"]): e for e in target_entries}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                if future.result():
                    valid_entries.append(entry)
                    print(f"  ✓ {entry['name']} [{entry['group']}]")
                else:
                    print(f"  ✗ {entry['name']} (不可用)")
            except Exception as e:
                print(f"  ✗ {entry['name']} (检测异常: {e})")
    
    print(f"[检测] 可用频道: {len(valid_entries)} 个")
    
    if not valid_entries:
        print("[结束] 没有可用的新频道，退出。")
        return
    
    # 去重（基于频道名称）
    existing_names = load_existing_names(INDEX_FILE)
    new_entries = [e for e in valid_entries if e["name"] not in existing_names]
    print(f"[去重] 需要新增的频道: {len(new_entries)} 个")
    
    if new_entries:
        if not os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
        write_m3u(INDEX_FILE, new_entries, mode='a')
    else:
        print("[结束] 没有新频道需要添加。")

if __name__ == "__main__":
    main()