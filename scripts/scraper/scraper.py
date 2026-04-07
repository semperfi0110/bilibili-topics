#!/usr/bin/env python3
"""
B站美食类目数据抓取工具
使用urllib（内置模块，无需安装依赖）
"""

import json
import time
import re
from urllib import request, parse
from urllib.error import URLError, HTTPError
from datetime import datetime
from typing import List, Dict, Optional

BILIBILI_API_BASE = "https://api.bilibili.com"

class BilibiliScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.bilibili.com"
        }

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """发送HTTP请求"""
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        req = request.Request(url, headers=self.headers)
        try:
            with request.urlopen(req, timeout=10) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            print(f"请求失败: {e}")
            return None

    def get_hot_videos(self, category_id: int = 36, limit: int = 20) -> List[Dict]:
        """
        获取B站分区热门视频
        category_id 36 = 美食
        """
        url = f"{BILIBILI_API_BASE}/x/web-interface/ranking/v2"
        params = {"rid": category_id, "type": "all"}

        data = self._make_request(url, params)
        if data and data.get("code") == 0:
            videos = data.get("data", {}).get("list", [])
            return self._format_videos(videos[:limit])
        return []

    def search_videos(self, keyword: str, limit: int = 10, max_retries: int = 3) -> List[Dict]:
        """
        搜索B站视频（带重试机制）
        """
        url = f"{BILIBILI_API_BASE}/x/web-interface/search/type"

        for attempt in range(max_retries):
            params = {
                "search_type": "video",
                "keyword": keyword,
                "page": 1,
                "page_size": limit
            }

            data = self._make_request(url, params)
            if data and data.get("code") == 0:
                videos = data.get("data", {}).get("result", [])
                return [self._format_search_result(v) for v in videos if v.get("bvid")]

            # 检查是否是412错误
            if data and data.get("code") == -412:
                print(f"[RETRY] 搜索'{keyword}'遇到412错误，第{attempt+1}次重试...")
                time.sleep(1)  # 延迟1秒后重试
                continue

            break  # 其他错误直接返回空

        return []

    def batch_search(self, keywords: List[str], limit_per_keyword: int = 3) -> List[Dict]:
        """
        批量搜索多个关键词，合并去重
        返回所有搜索到的视频
        """
        all_videos = []
        seen_bvids = set()

        print(f"\n[INFO] 开始批量搜索 {len(keywords)} 个关键词...")

        for i, keyword in enumerate(keywords):
            print(f"[{i+1}/{len(keywords)}] 搜索: {keyword}", end=" ... ")

            videos = self.search_videos(keyword, limit=limit_per_keyword)

            if videos:
                new_count = 0
                for video in videos:
                    if video.get("bvid") not in seen_bvids:
                        all_videos.append(video)
                        seen_bvids.add(video.get("bvid"))
                        new_count += 1
                print(f"✓ 获取{len(videos)}条 (新增{new_count})")
            else:
                print("✗ 无结果")

            # 每个关键词之间稍作延迟
            time.sleep(0.3)

        print(f"[INFO] 批量搜索完成，共获取 {len(all_videos)} 条不重复视频")
        return all_videos

    def get_video_detail(self, bvid: str) -> Optional[Dict]:
        """
        获取视频详细信息
        """
        url = f"{BILIBILI_API_BASE}/x/web-interface/view"
        params = {"bvid": bvid}

        data = self._make_request(url, params)
        if data and data.get("code") == 0:
            return data.get("data", {})
        return None

    def get_category_rank(self, category_id: int = 36, limit: int = 20) -> List[Dict]:
        """
        获取分区排行榜
        """
        return self.get_hot_videos(category_id, limit)

    def get_food_trending(self, limit: int = 20) -> List[Dict]:
        """
        获取美食区实时热门视频（带视频链接）
        """
        videos = self.get_hot_videos(category_id=36, limit=limit)
        # 添加可点击的视频链接
        for v in videos:
            v["url"] = f"https://www.bilibili.com/video/{v['bvid']}"
        return videos

    def search_food_related(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        搜索美食相关视频
        """
        videos = self.search_videos(keyword, limit)
        for v in videos:
            v["url"] = f"https://www.bilibili.com/video/{v['bvid']}"
        return videos

    def _format_videos(self, videos: List[Dict]) -> List[Dict]:
        """格式化视频数据"""
        formatted = []
        for v in videos:
            stat = v.get("stat", {})
            formatted.append({
                "title": v.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                "bvid": v.get("bvid", ""),
                "author": v.get("owner", {}).get("name", ""),
                "author_mid": v.get("owner", {}).get("mid", ""),
                "views": stat.get("view", 0),
                "views_str": self._format_number(stat.get("view", 0)),
                "likes": stat.get("like", 0),
                "likes_str": self._format_number(stat.get("like", 0)),
                "coins": stat.get("coin", 0),
                "favorites": stat.get("favorite", 0),
                "share": stat.get("share", 0),
                "duration": self._format_duration(v.get("duration", 0)),
                "pubdate": datetime.fromtimestamp(v.get("pubdate", 0)).strftime("%Y-%m-%d") if v.get("pubdate") else "",
                "desc": v.get("desc", "")[:200],
                "tags": [tag.get("tag_name", "") for tag in v.get("tags", []) if tag.get("tag_name")][:5],
                "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}"
            })
        return formatted

    def _format_search_result(self, video: Dict) -> Dict:
        """格式化搜索结果"""
        return {
            "title": video.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
            "bvid": video.get("bvid", ""),
            "author": video.get("author", ""),
            "views": self._parse_number(video.get("play", "0")),
            "views_str": video.get("play", "0"),
            "likes": self._parse_number(video.get("like", "0")),
            "duration": video.get("duration", ""),
            "pubdate": video.get("pubdate", ""),
            "tags": [],
            "url": f"https://www.bilibili.com/video/{video.get('bvid', '')}"
        }

    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def _format_number(self, num: int) -> str:
        """格式化数字"""
        if num >= 100000000:
            return f"{num/100000000:.1f}亿"
        elif num >= 10000:
            return f"{num/10000:.1f}万"
        return str(num)

    def _parse_number(self, num_str: str) -> int:
        """解析数字字符串"""
        if isinstance(num_str, int):
            return num_str
        num_str = str(num_str).replace(",", "")
        if "万" in num_str:
            return int(float(num_str.replace("万", "")) * 10000)
        try:
            return int(num_str)
        except:
            return 0


def main():
    scraper = BilibiliScraper()

    print("=" * 60)
    print("B站美食区热门视频（真实数据）")
    print("=" * 60)

    videos = scraper.get_food_trending(limit=10)
    if videos:
        for i, v in enumerate(videos, 1):
            print(f"\n{i}. {v['title']}")
            print(f"   UP主: {v['author']}")
            print(f"   播放: {v['views_str']} | 点赞: {v['likes_str']}")
            print(f"   时长: {v['duration']} | 发布时间: {v['pubdate']}")
            print(f"   链接: {v['url']}")
            if v.get("tags"):
                print(f"   标签: {' '.join(v['tags'])}")
    else:
        print("获取失败，请检查网络或API状态")

    print("\n" + "=" * 60)
    print("搜索'预制菜'相关视频（真实数据）")
    print("=" * 60)

    search_results = scraper.search_food_related("预制菜", limit=5)
    if search_results:
        for i, v in enumerate(search_results, 1):
            print(f"\n{i}. {v['title']}")
            print(f"   UP主: {v['author']}")
            print(f"   播放: {v['views_str']} | 点赞: {v['likes_str']}")
            print(f"   链接: {v['url']}")
    else:
        print("搜索失败")


if __name__ == "__main__":
    main()
