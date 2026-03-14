import requests
import time
from pathlib import Path
import json

# ================== 配置区 ==================
API_URL = "https://api.zxki.cn/api/wyyrg"
REQUESTS_COUNT = 10          # 每天请求次数
RETRIES = 3                  # 单次请求失败时的重试次数
# 输出文件（位于仓库根目录）
DAILY_FILE = "daily-music.m3u"       # 每日歌单（每天覆盖）
HISTORY_FILE = "music-history.m3u"   # 历史记录（持续追加）
# ===========================================

def fetch_song():
    """调用新API获取一首随机歌曲，成功返回歌曲信息字典，失败返回None"""
    for attempt in range(RETRIES):
        try:
            resp = requests.get(API_URL, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                # 检查新API的成功标识 (code=1 表示成功)
                if data.get("code") == 1 and "data" in data:
                    song_data = data["data"]
                    # 确保必要的字段都存在且URL有效
                    if song_data.get("url") and song_data.get("name"):
                        # 提取所有需要的字段
                        return {
                            "name": song_data.get("name", "未知歌曲"),
                            "artistsname": song_data.get("artistsname", "未知歌手"),
                            "alname": song_data.get("alname", "未知专辑"),
                            "picurl": song_data.get("picurl", ""),
                            "url": song_data["url"]
                        }
            print(f"  请求失败或数据无效 (尝试 {attempt+1}/{RETRIES})")
        except Exception as e:
            print(f"  请求异常: {e} (尝试 {attempt+1}/{RETRIES})")
        time.sleep(2)
    return None

def format_extinf(song):
    """根据歌曲信息生成 #EXTINF 行（包含歌手名 - 歌曲名）"""
    # 格式: #EXTINF:-1,歌手名 - 歌曲名
    title = f"{song['artistsname']} - {song['name']}"
    return f"#EXTINF:-1,{title}\n"

def format_comment(song):
    """生成包含详细信息的注释行，用于history文件"""
    # 格式: # 歌手名 - 歌曲名 (专辑: 专辑名) | 封面: 图片URL
    return f"# {song['artistsname']} - {song['name']} (专辑: {song['alname']}) | 封面: {song['picurl']}\n"

def main():
    print(f"开始获取 {REQUESTS_COUNT} 首随机歌曲...")
    successful_songs = []

    for i in range(REQUESTS_COUNT):
        print(f"正在获取第 {i+1} 首歌曲...")
        song_info = fetch_song()
        if song_info:
            successful_songs.append(song_info)
            print(f"  ✓ 成功: {song_info['artistsname']} - {song_info['name']}")
        else:
            print(f"  ✗ 第 {i+1} 次请求最终失败")
        time.sleep(1)  # 礼貌性间隔

    # 如果没有获取到任何歌曲，退出
    if not successful_songs:
        print("错误：没有获取到任何有效歌曲，程序退出。")
        return

    # ========== 1. 更新每日歌单 daily-music.m3u (覆盖) ==========
    daily_path = Path(__file__).parent.parent / DAILY_FILE
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for song in successful_songs:
            f.write(format_extinf(song))
            f.write(f"{song['url']}\n")
    print(f"\n✅ 已更新每日歌单 ({len(successful_songs)} 首): {DAILY_FILE}")

    # ========== 2. 追加到历史记录 music-history.m3u ==========
    history_path = Path(__file__).parent.parent / HISTORY_FILE
    # 使用 'a' 模式追加，如果文件不存在会自动创建
    with open(history_path, "a", encoding="utf-8") as f:
        # 如果文件是新创建的，写入一个文件头
        if history_path.stat().st_size == 0:
            f.write("#EXTM3U - 音乐历史记录\n")

        # 为每次运行添加一个时间戳分组（可选，便于阅读）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n# ===== 更新于 {timestamp} =====\n")

        for song in successful_songs:
            # 先写入详细信息注释行
            f.write(format_comment(song))
            # 再写入标准EXTINF和URL
            f.write(format_extinf(song))
            f.write(f"{song['url']}\n\n")  # 额外空行分隔每首歌
    print(f"✅ 已追加到历史记录: {HISTORY_FILE}")

if __name__ == "__main__":
    main()
