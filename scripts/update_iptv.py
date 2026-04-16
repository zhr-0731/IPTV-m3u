#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import concurrent.futures
import os
import sys

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("[提示] tqdm 未安装，将使用简单计数器显示进度。")

M3U_URL = "https://live.zbds.top/tv/iptv4.m3u"
INDEX_FILE = "index.m3u"
DEAD_FILE = "index_dead.m3u"
TIMEOUT = 5
MAX_WORKERS = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

TARGET_GROUPS = {"央视频道", "卫视频道", "地方频道"}

stats = {
    "remote_total": 0,
    "remote_target": 0,
    "active_before": 0,
    "active_after": 0,
    "dead_after": 0,
    "new_added": 0
}

def fetch_m3u_content(url):
    try:
        print(f"[源1] 正在下载 M3U 文件...")
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        print(f"[源1] 下载完成，大小: {len(resp.text)} 字符")
        return resp.text
    except Exception as e:
        print(f"[错误] 无法获取 M3U 文件: {e}")
        return None

def parse_m3u(content):
    print("[源1] 正在解析 M3U...")
    entries = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            extinf = line
            group_match = re.search(r'group-title="([^"]*)"', extinf)
            group = group_match.group(1).strip() if group_match else ""
            
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
                        "url": url,
                        "group": group
                    })
            i += 2
        else:
            i += 1
    print(f"[源1] 解析完成，获得 {len(entries)} 个条目")
    return entries

def load_local_entries(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_m3u(content)
    except Exception as e:
        print(f"[警告] 读取 {filepath} 失败: {e}")
        return []

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

def write_m3u_sorted(filepath, entries):
    sorted_entries = sorted(entries, key=lambda e: e["name"].lower())
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for e in sorted_entries:
            f.write(e["extinf"] + "\n")
            f.write(e["url"] + "\n")
    print(f"[源1] 已写入 {len(sorted_entries)} 个频道到 {filepath}")

def main():
    global stats
    print("=" * 50)
    print("[源1] 开始处理 iptv4.m3u (分类筛选)")
    
    # 1. 读取本地已有频道
    active_entries = load_local_entries(INDEX_FILE)
    dead_entries = load_local_entries(DEAD_FILE)
    all_local = active_entries + dead_entries
    local_names = {e["name"] for e in all_local}
    stats["active_before"] = len(active_entries)
    print(f"[源1] 本地原有活跃频道: {stats['active_before']} 个，失效频道: {len(dead_entries)} 个")
    
    # 2. 获取远程新频道
    content = fetch_m3u_content(M3U_URL)
    remote_entries = []
    if content:
        all_remote = parse_m3u(content)
        stats["remote_total"] = len(all_remote)
        remote_target = [e for e in all_remote if e["group"] in TARGET_GROUPS]
        stats["remote_target"] = len(remote_target)
        for e in remote_target:
            if e["name"] not in local_names:
                remote_entries.append(e)
        print(f"[源1] 远程总频道 {stats['remote_total']}，符合分类 {stats['remote_target']}，本地新频道 {len(remote_entries)}")
    else:
        print("[源1] 获取远程列表失败，仅检测本地频道")
    
    all_to_check = all_local + remote_entries
    total_check = len(all_to_check)
    print(f"[源1] 待检测频道总数: {total_check}")
    
    if total_check == 0:
        print("[源1] 没有频道需要检测，退出。")
        with open(".stats_iptv4.txt", "w", encoding="utf-8") as f:
            f.write(f"{stats['remote_total']}\n{stats['remote_target']}\n")
            f.write(f"{stats['active_before']}\n0\n0\n0")
        return
    
    # 4. 并发检测，带进度显示
    print("[源1] 正在并发检测流可用性...")
    active_checked = []
    dead_checked = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_entry = {executor.submit(check_stream, e["url"]): e for e in all_to_check}
        
        if TQDM_AVAILABLE:
            with tqdm(total=total_check, desc="检测进度", unit="个") as pbar:
                for future in concurrent.futures.as_completed(future_to_entry):
                    entry = future_to_entry[future]
                    try:
                        if future.result():
                            active_checked.append(entry)
                        else:
                            dead_checked.append(entry)
                    except Exception:
                        dead_checked.append(entry)
                    pbar.update(1)
                    pbar.set_postfix(active=len(active_checked), dead=len(dead_checked))
        else:
            completed = 0
            for future in concurrent.futures.as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    if future.result():
                        active_checked.append(entry)
                    else:
                        dead_checked.append(entry)
                except Exception:
                    dead_checked.append(entry)
                completed += 1
                if completed % 10 == 0 or completed == total_check:
                    print(f"  进度: {completed}/{total_check} (活跃: {len(active_checked)}, 失效: {len(dead_checked)})")
    
    # 5. 写入排序文件
    write_m3u_sorted(INDEX_FILE, active_checked)
    write_m3u_sorted(DEAD_FILE, dead_checked)
    
    stats["active_after"] = len(active_checked)
    stats["dead_after"] = len(dead_checked)
    stats["new_added"] = max(0, stats["active_after"] - stats["active_before"])
    
    print(f"[源1] 结果: 活跃 {stats['active_after']}，失效 {stats['dead_after']}，净增 {stats['new_added']}")
    
    with open(".stats_iptv4.txt", "w", encoding="utf-8") as f:
        f.write(f"{stats['remote_total']}\n{stats['remote_target']}\n")
        f.write(f"{stats['active_before']}\n{stats['active_after']}\n{stats['dead_after']}\n{stats['new_added']}")
    
    print("[源1] 处理完成。")
    print("=" * 50)

if __name__ == "__main__":
    main()