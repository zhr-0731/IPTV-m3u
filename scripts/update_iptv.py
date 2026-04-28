#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import concurrent.futures
import os
import sys
import time
import hashlib
import logging
import platform
from datetime import datetime
from collections import Counter

def natural_key(text):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', text)]

def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    start_time = datetime.now()
    start_timestamp = int(start_time.timestamp())
    
    operator = os.environ.get("GITHUB_ACTOR", "local-user")
    run_id = os.environ.get("GITHUB_RUN_ID", "manual")
    commit_sha = os.environ.get("GITHUB_SHA", "unknown")
    
    time_str = start_time.strftime("%y%m%d-%H%M%S")
    hash_input = f"{start_timestamp}-{operator}-{start_timestamp}"
    hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    log_filename = f"{time_str}-{operator}-{hash_value}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger()
    
    logger.info("=" * 60)
    logger.info(f"运行开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"操作者: {operator}")
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    logger.info(f"Python 版本: {platform.python_version()}")
    logger.info(f"GitHub Run ID: {run_id}")
    logger.info(f"Git Commit SHA: {commit_sha}")
    logger.info("=" * 60)
    
    return logger, start_time, log_path

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

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
    logger = logging.getLogger()
    try:
        logger.info("正在下载 M3U 文件...")
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        logger.info(f"下载完成，大小: {len(resp.text)} 字符")
        return resp.text
    except Exception as e:
        logger.error(f"无法获取 M3U 文件: {e}")
        return None

def parse_m3u(content):
    logger = logging.getLogger()
    logger.info("正在解析 M3U...")
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
    logger.info(f"解析完成，获得 {len(entries)} 个条目")
    return entries

def load_local_entries(filepath):
    logger = logging.getLogger()
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_m3u(content)
    except Exception as e:
        logger.warning(f"读取 {filepath} 失败: {e}")
        return []

def check_stream(url):
    try:
        resp = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code < 400:
            return True, None
        else:
            return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, f"ConnectionError: {str(e)[:50]}"
    except Exception as e:
        return False, f"Unknown: {type(e).__name__}"
    
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True)
        if resp.status_code < 400:
            for _ in resp.iter_content(1024):
                break
            return True, None
        else:
            return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, f"ConnectionError: {str(e)[:50]}"
    except Exception as e:
        return False, f"Unknown: {type(e).__name__}"

def write_m3u_sorted(filepath, entries):
    logger = logging.getLogger()
    sorted_entries = sorted(entries, key=lambda e: natural_key(e["name"]))
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U url-tvg="https://zhr-0731.github.io/IPTV-m3u/epg/epg.xml"\n')
        for e in sorted_entries:
            f.write(e["extinf"] + "\n")
            f.write(e["url"] + "\n")
    logger.info(f"已写入 {len(sorted_entries)} 个频道到 {filepath}")

def main():
    logger, start_time, log_path = setup_logging()
    logger.info("开始处理 iptv4.m3u (分类筛选)")
    logger.info("来源: iptv4")
    
    active_entries = load_local_entries(INDEX_FILE)
    dead_entries = load_local_entries(DEAD_FILE)
    all_local = active_entries + dead_entries
    local_names = {e["name"] for e in all_local}
    stats["active_before"] = len(active_entries)
    logger.info(f"本地原有活跃频道: {stats['active_before']} 个，失效频道: {len(dead_entries)} 个")
    
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
        logger.info(f"远程总频道 {stats['remote_total']}，符合分类 {stats['remote_target']}，本地新频道 {len(remote_entries)}")
    else:
        logger.warning("获取远程列表失败，仅检测本地频道")
    
    all_to_check = all_local + remote_entries
    total_check = len(all_to_check)
    logger.info(f"待检测频道总数: {total_check}")
    
    if total_check == 0:
        logger.info("没有频道需要检测，退出。")
        with open(".stats_iptv4.txt", "w", encoding="utf-8") as f:
            f.write(f"{stats['remote_total']}\n{stats['remote_target']}\n")
            f.write(f"{stats['active_before']}\n0\n0\n0")
        # 即使没有检测，也生成错误统计文件（空）
        with open(".stats_errors_iptv4.txt", "w", encoding="utf-8") as f:
            f.write("")
        return
    
    logger.info("正在并发检测流可用性...")
    active_checked = []
    dead_checked = []
    dead_details = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_entry = {executor.submit(check_stream, e["url"]): e for e in all_to_check}
        
        if TQDM_AVAILABLE:
            with tqdm(total=total_check, desc="检测进度", unit="个") as pbar:
                for future in concurrent.futures.as_completed(future_to_entry):
                    entry = future_to_entry[future]
                    try:
                        is_ok, error_info = future.result()
                        if is_ok:
                            active_checked.append(entry)
                        else:
                            dead_checked.append(entry)
                            dead_details.append({
                                "name": entry["name"],
                                "url": entry["url"],
                                "error": error_info or "Unknown"
                            })
                    except Exception as e:
                        dead_checked.append(entry)
                        dead_details.append({
                            "name": entry["name"],
                            "url": entry["url"],
                            "error": f"Future exception: {e}"
                        })
                    pbar.update(1)
                    pbar.set_postfix(active=len(active_checked), dead=len(dead_checked))
        else:
            completed = 0
            for future in concurrent.futures.as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    is_ok, error_info = future.result()
                    if is_ok:
                        active_checked.append(entry)
                    else:
                        dead_checked.append(entry)
                        dead_details.append({
                            "name": entry["name"],
                            "url": entry["url"],
                            "error": error_info or "Unknown"
                        })
                except Exception as e:
                    dead_checked.append(entry)
                    dead_details.append({
                        "name": entry["name"],
                        "url": entry["url"],
                        "error": f"Future exception: {e}"
                    })
                completed += 1
                if completed % 10 == 0 or completed == total_check:
                    logger.info(f"进度: {completed}/{total_check} (活跃: {len(active_checked)}, 失效: {len(dead_checked)})")
    
    if dead_details:
        logger.info("--- 失效频道详情 ---")
        for d in dead_details:
            logger.info(f"频道: {d['name']} | 错误: {d['error']} | URL: {d['url']}")
        logger.info("--- 失效频道详情结束 ---")
    
    # 统计错误类型
    error_counter = Counter()
    for d in dead_details:
        error_counter[d["error"]] += 1
    # 保存错误统计到临时文件
    with open(".stats_errors_iptv4.txt", "w", encoding="utf-8") as f:
        for error_type, count in error_counter.most_common():
            f.write(f"{error_type}:{count}\n")
    logger.info(f"错误统计已保存: {dict(error_counter)}")
    
    write_m3u_sorted(INDEX_FILE, active_checked)
    write_m3u_sorted(DEAD_FILE, dead_checked)
    
    stats["active_after"] = len(active_checked)
    stats["dead_after"] = len(dead_checked)
    stats["new_added"] = max(0, stats["active_after"] - stats["active_before"])
    
    logger.info(f"结果汇总: 活跃 {stats['active_after']}，失效 {stats['dead_after']}，净增 {stats['new_added']}")
    
    with open(".stats_iptv4.txt", "w", encoding="utf-8") as f:
        f.write(f"{stats['remote_total']}\n{stats['remote_target']}\n")
        f.write(f"{stats['active_before']}\n{stats['active_after']}\n{stats['dead_after']}\n{stats['new_added']}")
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    elapsed_str = f"{elapsed:.2f}s"
    new_log_filename = log_path.replace(".log", f"-{elapsed_str}.log")
    os.rename(log_path, new_log_filename)
    logger.info(f"处理完成，总运行时长: {elapsed_str}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()