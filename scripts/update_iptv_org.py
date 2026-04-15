#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import concurrent.futures
import os
import sys

M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"
INDEX_FILE = "iptv-org.m3u"
TIMEOUT = 5
MAX_WORKERS = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

stats = {
    "total": 0,
    "valid": 0,
    "new": 0
}

def fetch_m3u_content(url):
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"[错误] 无法获取 M3U 文件: {e}")
        return None

def parse_m3u(content):
    entries = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            extinf = line
            
            name_match = re.search(r'tvg-name="([^"]+)"', extinf)
            if not name_match:
                parts = extinf.split(',', 1)
                name = parts[1].strip() if len(parts) > 1 else "未知频道"
            else:
                name = name_match.group(1).strip()
            
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    entries.append({
                        "extinf": extinf,
                        "name": name,
                        "url": url
                    })
            i += 2
        else:
            i += 1
    return entries

def check_stream(url):
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
        print(f"[警告] 读取现有 {index_path} 失败: {e}")
    return names

def write_m3u(index_path, entries, mode='a'):
    with open(index_path, mode, encoding='utf-8') as f:
        if mode == 'w':
            f.write("#EXTM3U\n")
        for e in entries:
            f.write(e["extinf"] + "\n")
            f.write(e["url"] + "\n")
    print(f"[完成] 已写入 {len(entries)} 个新条目到 {index_path}")

def main():
    global stats
    print(f"[源2] 获取远程 M3U 文件: {M3U_URL}")
    content = fetch_m3u_content(M3U_URL)
    if not content:
        sys.exit(1)
    
    print("[源2] 解析 M3U 条目...")
    all_entries = parse_m3u(content)
    stats["total"] = len(all_entries)
    print(f"[源2] 共 {stats['total']} 个频道")
    
    if not all_entries:
        print("[源2] 没有频道，退出。")
        with open(".stats_iptv_org.txt", "w", encoding="utf-8") as f:
            f.write("0\n0\n0")
        return
    
    print("[源2] 正在并发测试流可用性...")
    valid_entries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_entry = {executor.submit(check_stream, e["url"]): e for e in all_entries}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                if future.result():
                    valid_entries.append(entry)
            except Exception:
                pass
    
    stats["valid"] = len(valid_entries)
    print(f"[源2] 可用频道: {stats['valid']} 个")
    
    if not valid_entries:
        print("[源2] 没有可用的新频道，退出。")
        with open(".stats_iptv_org.txt", "w", encoding="utf-8") as f:
            f.write(f"{stats['total']}\n0\n0")
        return
    
    existing_names = load_existing_names(INDEX_FILE)
    new_entries = [e for e in valid_entries if e["name"] not in existing_names]
    stats["new"] = len(new_entries)
    print(f"[源2] 需要新增的频道: {stats['new']} 个")
    
    if new_entries:
        if not os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
        write_m3u(INDEX_FILE, new_entries, mode='a')
    
    with open(".stats_iptv_org.txt", "w", encoding="utf-8") as f:
        f.write(f"{stats['total']}\n{stats['valid']}\n{stats['new']}")

if __name__ == "__main__":
    main()