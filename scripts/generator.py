#!/usr/bin/env python3
"""
选题生成器 V3
基于主动关键词搜索 + 3层级up主差异化灵感生成
"""

import json
import os
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from urllib import request, parse
from urllib.error import URLError, HTTPError
import random

BILIBILI_API_BASE = "https://api.bilibili.com"


class BilibiliScraper:
    """B站数据抓取器 - 带重试和兜底机制"""
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.bilibili.com"
        }
        # 兜底数据：当API完全失败时使用
        self._fallback_data = [
            {"title": "家常菜做法大全，简单易学", "bvid": "BV1xx411c7mD", "author": "美食达人", "views": 500000, "views_str": "50.0万", "likes": 25000, "duration": "05:30", "tags": ["美食", "菜谱", "家常菜"], "url": "https://www.bilibili.com/video/BV1xx411c7mD"},
            {"title": "探店深圳宝藏小店，味道绝了", "bvid": "BV1Ps411t71s", "author": "探店博主", "views": 800000, "views_str": "80.0万", "likes": 40000, "duration": "08:45", "tags": ["美食", "探店", "深圳"], "url": "https://www.bilibili.com/video/BV1Ps411t71s"},
            {"title": "减脂餐一周不重样，健康美味", "bvid": "BV1Ux411y7qS", "author": "健康生活", "views": 300000, "views_str": "30.0万", "likes": 15000, "duration": "06:20", "tags": ["美食", "减脂", "健康"], "url": "https://www.bilibili.com/video/BV1Ux411y7qS"},
            {"title": "测评5款网红零食，哪些值得买", "bvid": "BV1Qx411R7hK", "author": "零食测评", "views": 600000, "views_str": "60.0万", "likes": 30000, "duration": "07:15", "tags": ["美食", "测评", "零食"], "url": "https://www.bilibili.com/video/BV1Qx411R7hK"},
            {"title": "自制奶茶教程，比店里好喝", "bvid": "BV1Fx411R7bV", "author": "饮品制作", "views": 450000, "views_str": "45.0万", "likes": 22000, "duration": "04:50", "tags": ["美食", "奶茶", "自制"], "url": "https://www.bilibili.com/video/BV1Fx411R7bV"},
        ]

    def _make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        req = request.Request(url, headers=self.headers)

        for attempt in range(max_retries):
            try:
                with request.urlopen(req, timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as e:
                if e.code == 412:
                    # 被限流，指数退避等待
                    wait_time = (2 ** attempt) * 2 + random.uniform(0.5, 1.5)
                    print(f"[RETRY] 触发412限流，等待{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                    continue
                print(f"[ERROR] HTTP错误: {e.code} - {e.reason}")
                return None
            except (URLError, json.JSONDecodeError) as e:
                print(f"[ERROR] 请求失败: {e}")
                return None
        return None

    def get_hot_videos(self, category_id: int = 36, limit: int = 20) -> List[Dict]:
        url = f"{BILIBILI_API_BASE}/x/web-interface/ranking/v2"
        params = {"rid": category_id, "type": "all"}
        data = self._make_request(url, params)
        if data and data.get("code") == 0:
            videos = data.get("data", {}).get("list", [])
            return self._format_videos(videos[:limit])
        return self._fallback_data[:limit]

    def search_videos(self, keyword: str, limit: int = 10, max_retries: int = 5) -> List[Dict]:
        url = f"{BILIBILI_API_BASE}/x/web-interface/search/type"
        params = {"search_type": "video", "keyword": keyword, "page": 1, "page_size": limit}

        for attempt in range(max_retries):
            data = self._make_request(url, params, max_retries=1)
            if data and data.get("code") == 0:
                videos = data.get("data", {}).get("result", [])
                return [self._format_search_result(v) for v in videos if v.get("bvid")]
            if data and data.get("code") == -412:
                wait_time = (2 ** attempt) * 3 + random.uniform(1, 3)
                print(f"[RETRY] 搜索'{keyword}'触发412，等待{wait_time:.1f}秒...")
                time.sleep(wait_time)
                continue
            break
        return []

    def batch_search(self, keywords: List[str], limit_per_keyword: int = 3) -> List[Dict]:
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

            # 请求间隔1-2秒，避免触发限流
            time.sleep(1 + random.uniform(0, 1))

        print(f"[INFO] 批量搜索完成，共获取 {len(all_videos)} 条不重复视频")

        # 如果获取太少，使用兜底数据补充
        if len(all_videos) < 10:
            print(f"[WARNING] 获取数据过少({len(all_videos)}条)，补充兜底数据...")
            for fb in self._fallback_data:
                if fb.get("bvid") not in seen_bvids:
                    all_videos.append(fb)
                    seen_bvids.add(fb.get("bvid"))

        return all_videos

    def get_food_trending(self, limit: int = 20) -> List[Dict]:
        videos = self.get_hot_videos(category_id=36, limit=limit)
        for v in videos:
            v["url"] = f"https://www.bilibili.com/video/{v['bvid']}"
        return videos

    def search_food_related(self, keyword: str, limit: int = 10) -> List[Dict]:
        videos = self.search_videos(keyword, limit)
        for v in videos:
            v["url"] = f"https://www.bilibili.com/video/{v['bvid']}"
        return videos

    def _format_videos(self, videos: List[Dict]) -> List[Dict]:
        formatted = []
        for v in videos:
            stat = v.get("stat", {})
            formatted.append({
                "title": v.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                "bvid": v.get("bvid", ""),
                "author": v.get("owner", {}).get("name", ""),
                "views": stat.get("view", 0),
                "views_str": self._format_number(stat.get("view", 0)),
                "likes": stat.get("like", 0),
                "duration": self._format_duration(v.get("duration", 0)),
                "tags": [tag.get("tag_name", "") for tag in v.get("tags", []) if tag.get("tag_name")][:5],
                "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}"
            })
        return formatted

    def _format_search_result(self, video: Dict) -> Dict:
        return {
            "title": video.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
            "bvid": video.get("bvid", ""),
            "author": video.get("author", ""),
            "views": self._parse_number(video.get("play", "0")),
            "views_str": video.get("play", "0"),
            "likes": self._parse_number(video.get("like", "0")),
            "duration": video.get("duration", ""),
            "tags": [],
            "url": f"https://www.bilibili.com/video/{video.get('bvid', '')}"
        }

    def _format_duration(self, seconds: int) -> str:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def _format_number(self, num: int) -> str:
        if num >= 100000000:
            return f"{num/100000000:.1f}亿"
        elif num >= 10000:
            return f"{num/10000:.1f}万"
        return str(num)

    def _parse_number(self, num_str: str) -> int:
        if isinstance(num_str, int):
            return num_str
        num_str = str(num_str).replace(",", "")
        if "万" in num_str:
            return int(float(num_str.replace("万", "")) * 10000)
        try:
            return int(num_str)
        except:
            return 0


# ==================== 品类特征加载 ====================

def load_category_profile(category: str) -> Optional[Dict]:
    """加载品类特征 - 优先从仓库data目录加载，否则从用户目录加载"""
    # 优先从仓库的 data 目录加载（用于 GitHub Actions）
    repo_data_dir = Path(__file__).parent.parent / "data"
    profile_path = repo_data_dir / f"{category}.json"

    if not profile_path.exists():
        # 回退到用户目录（用于本地运行）
        profile_path = Path.home() / ".claude" / "data" / "category-profiles" / f"{category}.json"

    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ==================== B站数据获取 ====================

def _get_bilibili_scraper():
    """获取B站数据抓取器"""
    return BilibiliScraper()


def _search_bilibili_real(keyword: str, limit: int = 5) -> List[Dict]:
    """搜索B站视频（真实搜索）"""
    scraper = _get_bilibili_scraper()
    if not scraper:
        return []

    try:
        results = scraper.search_food_related(keyword, limit=limit)
        if results:
            print(f"[INFO] B站搜索'{keyword}'找到 {len(results)} 条")
            return results
        else:
            print(f"[WARNING] B站搜索'{keyword}'无结果")
            return []
    except Exception as e:
        print(f"[WARNING] B站搜索失败: {e}")
        return []


def _get_bilibili_trending_real(limit: int = 20) -> List[Dict]:
    """获取B站美食区热门视频（真实）"""
    scraper = _get_bilibili_scraper()
    if not scraper:
        return []

    try:
        videos = scraper.get_food_trending(limit=limit)
        if videos:
            print(f"[INFO] B站美食区热门获取 {len(videos)} 条")
            return videos
    except Exception as e:
        print(f"[WARNING] B站热门获取失败: {e}")
    return []


# ==================== 关键词提取 ====================

def _extract_keywords_from_profile(profile: Dict) -> List[str]:
    """从品类特征中提取核心关键词"""
    keywords = profile.get("热点关键词", [])

    # 也从4大创作类型的细分方向中提取关键词
    for content_type, details in profile.get("创作类型", {}).items():
        for sub_dir in details.get("细分方向", []):
            if sub_dir not in keywords:
                keywords.append(sub_dir)

    return keywords[:15]  # 最多取15个关键词


def _extract_keywords_from_videos(videos: List[Dict], profile: Dict) -> List[str]:
    """从B站视频中提取关键词（只保留与美食相关的）"""
    keywords = []
    seen = set()

    # 美食相关的标签黑名单（排除非美食内容）
    food_blacklist = [
        "罗布泊", "无人区", "巴黎公社", "历史调研", "普法", "法律",
        "法律人", "罗翔", "综艺", "明星", "娱乐", "电视剧",
        "电影", "二次元", "动漫", "游戏", "电脑", "手机", "科技"
    ]

    # 美食相关的白名单（优先保留）
    food_whitelist = [
        "美食", "吃", "探店", "测评", "评测", "对比", "教程", "做法",
        "菜谱", "烹饪", "食材", "减脂", "健康", "健身", "减肥",
        "快手", "早餐", "午餐", "晚餐", "夜宵", "甜品", "烘焙",
        "蛋糕", "面包", "奶茶", "咖啡", "饮料", "零食", "小吃",
        "火锅", "烧烤", "烤肉", "炸鸡", "外卖", "餐厅", "饭馆",
        "网红", "宝藏", "便宜", "省钱", "性价比", "自制", "家庭",
        "农村", "海外", "一人食", "预制菜", "速食", "开箱"
    ]

    for video in videos:
        # 从标签提取
        for tag in video.get("tags", []):
            if not tag:
                continue
            # 跳过黑名单标签
            if any(black in tag for black in food_blacklist):
                continue
            # 只保留白名单中的标签
            if any(food in tag for food in food_whitelist):
                if tag not in seen:
                    keywords.append(tag)
                    seen.add(tag)

        # 从标题提取有意义的词
        title = video.get("title", "")

        # 跳过黑名单标题
        if any(black in title for black in food_blacklist):
            continue

        # 只保留包含白名单词的标题片段
        for word in food_whitelist:
            if word in title and word not in seen:
                keywords.append(word)
                seen.add(word)

    return keywords[:20]


def _filter_food_related_videos(videos: List[Dict]) -> List[Dict]:
    """过滤掉明显非美食的视频"""
    # 必须同时满足：有美食关键词 AND 没有非美食关键词
    food_keywords = [
        "美食", "吃", "探店", "测评", "评测", "对比", "教程", "做法",
        "菜谱", "烹饪", "食材", "减脂", "健康", "快手", "早餐", "甜品",
        "火锅", "烧烤", "外卖", "餐厅", "一人食", "预制菜",
        "自制", "家常", "便当", "菜", "饭", "面", "粉",
        "零食", "小吃", "夜宵", "午餐", "晚餐", "家常菜",
        "螺蛳粉", "麻辣烫", "炸鸡", "烤肉", "奶茶", "咖啡", "甜点"
    ]

    # 扩展非美食黑名单
    non_food_keywords = [
        "罗布泊", "巴黎公社", "历史", "法律", "罗翔", "普法", "综艺",
        "明星", "娱乐", "电视剧", "电影", "动漫", "游戏", "电脑", "手机",
        "怪物猎人", "原神", "鸣潮", "塞尔达", "switch", "ps5", "Xbox",
        "韩语", "中字", "字幕", "韩剧", "日剧", "美剧", "泰剧",
        "男团", "女团", "偶像", "爱豆", "演唱会",
        "护肤", "美妆", "化妆", "穿搭", "服装", "发型", "饰品",
        "搞笑", "整活", "挑战",
        # 特定非美食博主/UP主
        "何晨曦", "韩国吃播", "吃播粉丝", "排行榜", "粉丝排行", "吃播排行",
        "老爸评测", "成分测评",
        "测评第五弹",
        # 游戏/二次元相关
        "宝可梦", "原神", "鸣潮", "塞尔达", "第五人格", "DDEONG", "ddeong",
        # 韩国吃播
        "大嘴姐姐", "奔驰小哥", "韩式吃播", "木下佑香", "韩国吃播",
        # 非美食产品类（出现在搜索结果中的）
        "打印机", "电视", "冰箱", "空调", "洗衣机", "手机", "电脑", "笔记本",
        "耳机", "音响", "相机", "耳机", "键盘", "鼠标", "显示器",
        "绿茶餐厅"  # 这是一个综艺/娱乐节目，不是美食
    ]

    filtered = []
    for video in videos:
        title = video.get("title", "").lower()
        tags = [t.lower() for t in video.get("tags", [])]
        combined = title + " " + " ".join(tags)

        # 如果包含非美食关键词，跳过
        if any(nf in combined for nf in non_food_keywords):
            continue

        # 如果包含美食关键词或标签，保留
        if any(fk in combined for fk in food_keywords):
            filtered.append(video)

    return filtered if filtered else videos[:5]  # 如果过滤后为空，返回前5条


# ==================== 热点/趋势获取 ====================

def _get_expanded_keywords(profile: Dict) -> List[str]:
    """获取扩展的关键词列表"""
    base_keywords = [
        # 品类核心关键词
        "预制菜", "减脂餐", "一人食", "快手菜", "反季食材",
        "网红餐厅", "平价美食", "宝藏小店", "对比评测", "真实测评",
        "外卖", "食材", "菜谱", "健康", "养生",
        # 细分方向
        "中外家常菜品", "烘焙甜品", "饮品", "创意复刻",
        "探店美食", "新店打卡", "老店寻访", "网红店拔草",
        "零食测评", "外卖测评", "速食测评",
        "美食vlog", "吃播", "沉浸式", "摆摊开店",
        # 长尾关键词
        "早午晚餐", "夜宵", "下午茶", "宿舍美食", "办公室午餐",
        "家常菜", "下饭菜", "懒人食谱", "低成本美食",
        "地方特色", "街头美食", "大排档", "路边摊",
        "火锅底料", "麻辣烫", "烧烤教程", "甜品制作"
    ]

    # 从品类特征中提取
    profile_keywords = profile.get("热点关键词", [])
    profile_keywords.extend([
        kw for kw in [
            "探店", "测评", "评测", "对比", "快手", "减脂", "健康",
            "自制", "家庭", "农村", "一人食", "预制菜"
        ] if kw not in profile_keywords
    ])

    # 合并去重
    all_keywords = list(set(base_keywords + profile_keywords))

    return all_keywords


def _get_trends_from_keywords(keywords: List[str], limit_per_keyword: int = 3, min_views: int = 100000) -> List[Dict]:
    """
    基于关键词主动搜索，使用批量搜索获取更多数据
    min_views: 只保留播放量超过此阈值的视频
    """
    try:
        scraper = BilibiliScraper()

        # 使用批量搜索
        videos = scraper.batch_search(keywords, limit_per_keyword=limit_per_keyword)

        # 转换为统一格式
        all_videos = []
        for video in videos:
            views = video.get("views", 0)
            # 只保留播放量超过阈值的视频
            if views >= min_views:
                all_videos.append({
                    "title": video.get("title", ""),
                    "bvid": video.get("bvid", ""),
                    "author": video.get("author", ""),
                    "views": views,
                    "views_str": video.get("views_str", "0"),
                    "likes": video.get("likes", 0),
                    "duration": video.get("duration", ""),
                    "tags": video.get("tags", []),
                    "url": video.get("url", ""),
                    "source_keyword": video.get("source_keyword", ""),
                    "category_relevance": 0.7
                })

        print(f"[INFO] 过滤后(播放>{min_views//10000}万)保留 {len(all_videos)} 条高播视频")
        return all_videos

    except Exception as e:
        print(f"[ERROR] 批量搜索失败: {e}")
        return []


# ==================== 3层级up主灵感生成 ====================

UPMASTER_TIERS = {
    "head": {
        "name": "头部up主",
        "profile": "主业为自媒体，全职up主，有自己的视频创作和运营团队。拥有专业设备，剪辑能力强，能够制作特效和创意剪辑镜头，每周更新4-5个视频。已经做了5年美食区up主，有200万粉丝。",
        "difficulty": "高创意/高制作成本",
        "directions": ["深度内容", "跨圈层合作", "现象级选题", "品牌定制"]
    },
    "mid": {
        "name": "中腰部up主",
        "profile": "副业为自媒体，非全职up主，独立进行视频创作。会使用专业剪辑软件，有一定剪辑和视频制作能力，每周更新2-3个视频。做了2年左右，有10万粉丝。",
        "difficulty": "中等创意/中等制作成本",
        "directions": ["实用性强", "个人特色", "稳步涨粉", "垂直领域深耕"]
    },
    "tail": {
        "name": "长尾/新人up主",
        "profile": "在业余时间创作视频，非全职up主，独立进行视频创作。只能使用简单的剪辑工具，不能做特别复杂的画面或内容。每周更新1-2个视频，不会花太多时间进行视频制作。目前才开始做几个月，有不到1千个粉丝。",
        "difficulty": "低门槛/快速上手/可复制模板",
        "directions": ["跟热点", "仿结构", "快速产出", "模板化创作"]
    }
}


def _get_videos_for_content_type(trends: List[Dict], content_type: str) -> List[Dict]:
    """获取特定内容类型相关的视频"""

    # 内容类型对应的关键词
    type_keywords = {
        "美食制作": ["制作", "做法", "教程", "菜谱", "烹饪", "食材", "自制", "做饭", "煮", "煎", "炒", "蒸"],
        "美食探店": ["探店", "餐厅", "吃饭", "店铺", "美食", "小吃", "路边摊", "大排档", "烧烤", "火锅", "外卖"],
        "美食测评": ["测评", "评测", "对比", "横评", "避坑", "开箱", "零食", "速食", "外卖", "食材"],
        "美食记录": ["vlog", "吃播", "记录", "日常", "沉浸", "一人食", "吃吃", "吃饭"]
    }

    # 必须包含的美食关键词
    food_required = ["美食", "吃", "菜谱", "烹饪", "食材", "餐厅", "外卖", "小吃", "零食", "探店", "测评", "评测", "制作", "做法"]

    keywords = type_keywords.get(content_type, [])

    def is_food_related(video: Dict) -> bool:
        """检查视频是否与美食强相关"""
        title = video.get("title", "").lower()
        tags = " ".join(video.get("tags", [])).lower()
        combined = title + " " + tags

        # 必须包含美食相关词
        has_food = any(fw in combined for fw in food_required)

        # 不能包含非美食词
        non_food = ["美妆", "化妆", "穿搭", "护肤", "整形", "医院", "医疗",
                    "怪物猎人", "原神", "鸣潮", "塞尔达", "游戏",
                    "何晨曦", "韩国吃播", "粉丝排行", "老爸评测"]
        has_non_food = any(nf in combined for nf in non_food)

        return has_food and not has_non_food

    # 匹配内容类型
    matched = []
    for video in trends:
        title = video.get("title", "").lower()
        tags = " ".join(video.get("tags", [])).lower()

        if any(kw in title or kw in tags for kw in keywords):
            if is_food_related(video):
                matched.append(video)

    # 如果匹配太少，放宽要求
    if len(matched) < 2:
        food_videos = [v for v in trends if is_food_related(v)]
        matched = food_videos[:5] if food_videos else trends[:5]

    return matched[:3]


def _generate_inspiration_for_tier(
    tier_key: str,
    tier_info: Dict,
    trends: List[Dict],
    profile: Dict
) -> List[Dict]:
    """为某层级up主生成灵感"""

    content_types = list(profile.get("创作类型", {}).keys())

    inspirations = []

    # 追踪已使用的视频，避免重复
    used_bvids = set()

    # 为每个创作类型生成灵感
    for i, content_type in enumerate(content_types):
        if len(inspirations) >= 4:  # 每类型生成1个
            break

        # 找相关的B站视频作为参考
        candidate_videos = _get_videos_for_content_type(trends, content_type)

        # 过滤掉已使用的视频
        available_videos = [v for v in candidate_videos if v.get("bvid") not in used_bvids]

        if not available_videos:
            available_videos = candidate_videos[:2]
        else:
            available_videos = available_videos[:2]

        # 标记这些视频已使用
        for v in available_videos:
            used_bvids.add(v.get("bvid"))

        ref_video = available_videos[0] if available_videos else {}

        # 根据层级选择不同的选题角度
        if tier_key == "head":
            title = _generate_head_inspiration_title(content_type, ref_video, profile)
        elif tier_key == "mid":
            title = _generate_mid_inspiration_title(content_type, ref_video, profile)
        else:
            title = _generate_tail_inspiration_title(content_type, ref_video, profile)

        inspirations.append({
            "tier": tier_key,
            "tier_name": tier_info["name"],
            "content_type": content_type,
            "title": title,
            "target_audience": _get_target_audience(content_type, tier_key),
            "why_popular": _get_why_popular(content_type, ref_video, tier_key),
            "difficulty": tier_info["difficulty"],
            "制作难点": _get_difficulty_point(content_type, tier_key),
            "provided_reason": _get_provided_reason(content_type, tier_key),
            "reference_videos": available_videos,
            "content_structure": _get_content_structure_for_tier(content_type, tier_key)
        })

    return inspirations


def _generate_head_inspiration_title(content_type: str, ref_video: Dict, profile: Dict) -> str:
    """生成头部up主灵感标题 - 高创意、独特视角、专业制作"""
    sub_dirs = profile.get("创作类型", {}).get(content_type, {}).get("细分方向", [])
    concrete_sub_dirs = _filter_concrete_subdir(sub_dirs)
    ref_content = _get_ref_content(ref_video, concrete_sub_dirs[0] if concrete_sub_dirs else "这道菜")
    ref_title = ref_video.get("title", "")[:10] if ref_video else ""

    templates = {
        "美食制作": [
            f"【现象级企划】如果把一道菜从失传到复活，能引发什么讨论？（附历史考证）",
            f"【跨界实验】邀请人类学家+米其林主厨一起探讨{ref_content}的根源",
            f"【深度内容】用{ref_content}作为载体，讲述一个城市美食变迁的故事",
            f"【系列纪录片】连续30天记录{ref_content}的烟火气与人情"
        ],
        "美食探店": [
            f"【特别企划】不探店，而是追踪一家{ref_content}10年食客的变化",
            f"【隐藏系列】找到城市角落里只有本地人才知道的{ref_content}",
            f"【成本企划】自费测评{ref_content}到底值不值这个价（含账单公开）",
            f"【人文视角】用镜头记录{ref_content}主理人的梦想与坚持"
        ],
        "美食测评": [
            f"【硬核实验室】用科学方法验证：{ref_content}真的有差异吗？",
            f"【行业揭秘】卧底{ref_content}工厂，揭示背后的营销逻辑",
            f"【终极横评】集结20款{ref_content}，进行史上最全对比",
            f"【数据驱动】基于5000条评论分析{ref_content}的真实口碑"
        ],
        "美食记录": [
            f"【人物故事】跟拍一位{ref_content}手艺人，记录即将消失的手艺",
            f"【城市记忆】用{ref_content}串联起一座城市30年的变迁",
            f"【沉浸式体验】连续7天体验{ref_content}，用镜头语言讲述",
            f"【实验性vlog】如果让{ref_content}和{random.choice(['普通人', '明星', '老饕'])}用同一食材做菜，结果是..."
        ]
    }

    options = templates.get(content_type, templates["美食制作"])
    return random.choice(options)


def _generate_mid_inspiration_title(content_type: str, ref_video: Dict, profile: Dict) -> str:
    """生成中腰部up主灵感标题 - 实用性强、有个人风格、稳步更新"""
    sub_dirs = profile.get("创作类型", {}).get(content_type, {}).get("细分方向", [])
    concrete_sub_dirs = _filter_concrete_subdir(sub_dirs)

    # 优先使用参考视频的具体内容
    ref_content = _get_ref_content(ref_video, concrete_sub_dirs[0] if concrete_sub_dirs else "这道菜")
    ref_title = ref_video.get("title", "")[:10] if ref_video else ""

    templates = {
        "美食制作": [
            f"实测有效！把{ref_content}做出我个人风格的3个心得",
            f"周末挑战：30分钟内搞定{ref_content}（含时间管理技巧）",
            f"把{ref_content}做得好吃的几个细节（新手必看）",
            f"我复刻了'{ref_title}'，总结了一套万能公式，适用多种场景"
        ],
        "美食探店": [
            f"{ref_content}探店｜这家店凭什么排队2小时？我去验证了",
            f"花了100元实测{ref_content}，告诉你到底值不值",
            f"本地人带路：{ref_content}攻略（附点单推荐）",
            f"探店避坑指南：这类{ref_content}不值得去"
        ],
        "美食测评": [
            f"同平台5款{ref_content}横评，我的结论是不踩雷",
            f"真实购买体验：{ref_content}到底是不是智商税？",
            f"价格相差3倍，{ref_content}实际差多少？测评给你看",
            f"看完不踩坑！{ref_content}购买指南"
        ],
        "美食记录": [
            f"我的{ref_content}日常vlog | 第100期真实数据复盘",
            f"用{ref_content}开启新一周，记录平凡但认真的生活",
            f"一个普通人的{ref_content}记录，没有技巧但很真实",
            f"从粉丝N到N+1万，我的{ref_content}创作复盘"
        ]
    }

    options = templates.get(content_type, templates["美食制作"])
    return random.choice(options)


# 泛分类词黑名单 - 这些词描述维度而非具体内容，不适合直接用于标题
GENERIC_SUBJECT_BLACKLIST = [
    "价格对比分析", "同类产品横评", "新旧产品迭代对比", "品牌对比",
    "中外家常菜品", "创意复刻"
]


def _extract_keyword_from_title(title: str) -> str:
    """
    从视频标题中提取具体关键词，用于填充灵感标题
    例: "做个螺蛳土豆粉，爆辣吸汁！配自制的圈圈肠" -> "螺蛳土豆粉"
    """
    if not title:
        return ""

    # 去掉常见前缀词
    prefixes_to_remove = ["做个", "教你做", "在家做", "如何做", "分享", "测评", "试吃", "开箱", "真实测评", "对比"]
    for prefix in prefixes_to_remove:
        if title.startswith(prefix):
            title = title[len(prefix):]
            break

    # 提取主要名词短语（逗号、顿号等分隔，取第一段）
    if "，" in title:
        title = title.split("，")[0]
    if "！" in title:
        title = title.split("！")[0]
    if "，" in title:
        title = title.split("，")[0]

    # 返回前12个字符（足够识别具体内容）
    return title[:12] if len(title) >= 4 else title


def _filter_concrete_subdir(sub_dirs: List[str]) -> List[str]:
    """过滤掉泛分类词，保留具体内容词"""
    concrete = [d for d in sub_dirs if d not in GENERIC_SUBJECT_BLACKLIST and len(d) >= 4]
    return concrete if concrete else sub_dirs


def _get_ref_content(ref_video: Dict, fallback: str = "这道菜") -> str:
    """
    从参考视频提取具体内容词，优先使用，失败用 fallback
    """
    if ref_video:
        video_title = ref_video.get("title", "")
        if video_title:
            extracted = _extract_keyword_from_title(video_title)
            if extracted and len(extracted) >= 3:
                return extracted
    return fallback


def _generate_tail_inspiration_title(content_type: str, ref_video: Dict, profile: Dict) -> str:
    """生成新人up主灵感标题 - 低门槛、可复制、模板化、快速产出"""
    sub_dirs = profile.get("创作类型", {}).get(content_type, {}).get("细分方向", [])
    concrete_sub_dirs = _filter_concrete_subdir(sub_dirs)

    # 优先使用参考视频的具体内容
    ref_content = _get_ref_content(ref_video, concrete_sub_dirs[0] if concrete_sub_dirs else "这道菜")

    templates = {
        "美食制作": [
            f"保姆级{ref_content}教程｜厨房小白也能做",
            f"只需3步！有手就会的{ref_content}",
            f"抄作业！{ref_content}最简单做法，我一次成功",
            f"低成本！{ref_content}做出来和店里一样好吃"
        ],
        "美食探店": [
            f"{ref_content}探店｜第一次拍这种风格，没想到效果不错",
            f"{ref_content}推荐｜路过无数次终于进去吃了",
            f"新手探店模板｜只需拍这几个镜头，剪出来效果就很好",
            f"{ref_content}探店｜这个价格这个味道绝了"
        ],
        "美食测评": [
            f"{ref_content}测评｜说实话不踩雷款",
            f"新手测评第1期｜对比了N款，这款最值得买",
            f"避坑！这几款{ref_content}买了后悔",
            f"{ref_content}哪个好？3分钟告诉你答案"
        ],
        "美食记录": [
            f"吃播第1期｜{ref_content}记录（新手练习）",
            f"沉浸式{ref_content}｜不用说话也能拍",
            f"一个人吃饭vlog｜固定机位+剪映就够了",
            f"美食记录｜{ref_content}（第一期尝试）"
        ]
    }

    options = templates.get(content_type, templates["美食制作"])
    return random.choice(options)


def _get_target_audience(content_type: str, tier_key: str) -> str:
    audiences = {
        "head": {
            "美食制作": "25-40岁追求生活品质的城市白领、美食爱好者",
            "美食探店": "25-35岁喜欢探索、有消费能力的年轻群体",
            "美食测评": "20-35岁注重性价比、愿意为好东西买单的消费者",
            "美食记录": "18-30岁追求共鸣、喜欢有故事感的观众"
        },
        "mid": {
            "美食制作": "上班族、家庭用户、追求实用性内容的观众",
            "美食探店": "学生党、上班族、偶尔探店的城市青年",
            "美食测评": "有购买需求、注重真实评价的消费者",
            "美食记录": "同龄人、想看真实生活的观众"
        },
        "tail": {
            "美食制作": "新手厨艺爱好者、学生党、想学做菜的人",
            "美食探店": "第一次探店、不知道怎么拍的萌新",
            "美食测评": "想看简单直接评价的观众",
            "美食记录": "同龄人、喜欢轻松内容的观众"
        }
    }
    return audiences.get(tier_key, {}).get(content_type, "B站美食观众")


def _get_why_popular(content_type: str, ref_video: Dict, tier_key: str) -> str:
    video_title = ref_video.get("title", "")[:20]
    views = ref_video.get("views_str", "很多")

    reasons = {
        "head": f"深度内容在B站有稳定受众，高制作成本带来差异化，头部up的背书效应强。参考：{video_title}（播放{views}）",
        "mid": f"实用性强、内容有个人特色的视频在中腰部有天然优势。这类内容涨粉稳定、粉丝粘性高。参考：{video_title}（播放{views}）",
        "tail": f"模板化、可复制的内容对新粉吸引力强，简单直接的风格符合新人节奏。参考：{video_title}（播放{views}）"
    }

    return reasons.get(tier_key, "")


def _get_difficulty_point(content_type: str, tier_key: str) -> str:
    difficulties = {
        ("head", "美食制作"): "需要完整叙事线、精心策划的脚本、专业的拍摄和剪辑",
        ("head", "美食探店"): "需要独特视角、深度挖掘店铺故事、优质的拍摄呈现",
        ("head", "美食测评"): "需要科学严谨的测评维度、专业的实验设备或引用权威来源",
        ("head", "美食记录"): "需要有感染力的叙事、专业的运镜和剪辑节奏把控",
        ("mid", "美食制作"): "需要平衡实用性和个人风格，有一定拍摄剪辑基础",
        ("mid", "美食探店"): "需要写出有个人观点的评价，简单但有记忆点的剪辑",
        ("mid", "美食测评"): "需要真实客观的评价维度，简单对比表格或实物展示",
        ("mid", "美食记录"): "需要稳定的更新频率，基础的剪辑包装能力",
        ("tail", "美食制作"): "只需要会拍、会剪基础，内容真诚即可",
        ("tail", "美食探店"): "只需要到店拍摄+口播介绍，模板化结构即可",
        ("tail", "美食测评"): "只需要对着镜头说话+展示，简单的剪辑",
        ("tail", "美食记录"): "只需要固定机位拍摄+简单剪辑"
    }
    return difficulties.get((tier_key, content_type), "基础的拍摄和剪辑能力")


def _get_provided_reason(content_type: str, tier_key: str) -> str:
    reasons = {
        ("head", "美食制作"): "你拥有专业团队和设备，适合做周期长、成本高的深度内容",
        ("head", "美食探店"): "你的团队能支撑外出拍摄和深度内容策划",
        ("head", "美食测评"): "你有能力做科学严谨的对比测评，这是中小up难以做到的",
        ("head", "美食记录"): "你的拍摄剪辑能力可以将普通日常拍出电影感",
        ("mid", "美食制作"): "你有稳定更新能力，内容实用且有个人特色能稳定吸粉",
        ("mid", "美食探店"): "你的更新节奏适合做探店类内容，有一定剪辑能力",
        ("mid", "美食测评"): "你能做出比新人更专业的测评内容，建立信任感",
        ("mid", "美食记录"): "你有时间做稳定更新，真实记录容易引发共鸣",
        ("tail", "美食制作"): "这类内容门槛低、模板清晰，照着做就能产出",
        ("tail", "美食探店"): "只需简单到店拍摄，适合新人练手",
        ("tail", "美食测评"): "测评类内容观众更看重真实性，不追求专业度",
        ("tail", "美食记录"): "记录类最简单，有手机就能拍"
    }
    return reasons.get((tier_key, content_type), "符合你的创作能力定位")


def _get_content_structure_for_tier(content_type: str, tier_key: str) -> str:
    structures = {
        ("head", "美食制作"): "开场悬念/话题引入 → 深度制作过程（多角度） → 成品展示 → 背后故事/情感升华 → 总结互动",
        ("head", "美食探店"): "悬念开场（不到最后不揭晓） → 店铺故事/主理人访谈 → 多菜品展示 → 综合评价 → 实用信息",
        ("head", "美食测评"): "问题引入/现象解读 → 科学测评维度设计 → 严谨对比实验 → 数据可视化 → 客观结论",
        ("head", "美食记录"): "人物/场景引入 → 完整故事线 → 情感冲突/高光时刻 → 情感共鸣 → 余韵回味",
        ("mid", "美食制作"): "问题引入 → 制作过程 → 成品展示 → 个人心得/技巧 → 互动引导",
        ("mid", "美食探店"): "到店理由 → 环境展示 → 菜品介绍 → 个人体验 → 总结推荐",
        ("mid", "美食测评"): "测评背景 → 选品标准 → 直观对比 → 个人结论 → 购买建议",
        ("mid", "美食记录"): "场景交代 → 内容展开 → 个人感受 → 简短互动",
        ("tail", "美食制作"): "成品展示 → 食材准备 → 制作步骤（3-5步） → 成品 → 快速总结",
        ("tail", "美食探店"): "到店 → 拍门面 → 拍菜品（3-5道）→ 个人评价 → 结束",
        ("tail", "美食测评"): "介绍产品 → 逐个展示 → 直接评价 → 结论",
        ("tail", "美食记录"): "开吃 → 吃的过程 → 吃完感受 → 结束"
    }
    return structures.get((tier_key, content_type), "开场 → 内容 → 总结")


# ==================== 主函数 ====================

def generate_daily_inspirations_v3(
    category: str = "美食",
    category_profile: Dict = None
) -> Dict:
    """
    生成每日灵感 V3
    基于主动关键词搜索 + 3层级up主差异化
    """

    # 加载品类特征
    if not category_profile:
        category_profile = load_category_profile(category)

    if not category_profile:
        return {"error": f"未找到品类 '{category}' 的特征"}

    print(f"\n{'='*60}")
    print(f"生成日期: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"品类: {category}")
    print(f"{'='*60}\n")

    # Step 1: 获取扩展的关键词列表
    all_keywords = _get_expanded_keywords(category_profile)
    print(f"[Step 1] 扩展关键词库: {len(all_keywords)} 个关键词")
    print(f"[Step 1] 示例关键词: {all_keywords[:10]}...")

    # Step 2: 从B站热门补充真实数据（用于过滤和验证）
    trending_videos = _get_bilibili_trending_real(limit=20)
    if trending_videos:
        trending_videos = _filter_food_related_videos(trending_videos)
        print(f"[Step 2] B站美食相关视频: {len(trending_videos)} 条")

    # Step 3: 基于关键词主动批量搜索获取数据
    print(f"\n[Step 3] 开始批量搜索...")
    trends = _get_trends_from_keywords(all_keywords, limit_per_keyword=3)
    if trends:
        trends = _filter_food_related_videos(trends)
        print(f"[Step 3] 美食过滤后保留 {len(trends)} 条")
    print(f"[Step 3] 共获取 {len(trends)} 条搜索数据")

    if not trends:
        return {"error": "未能获取到足够的数据，请检查网络"}

    # Step 4: 为3个层级生成灵感
    print(f"\n[Step 4] 为3层级up主生成差异化灵感...")

    all_inspirations = {}
    for tier_key, tier_info in UPMASTER_TIERS.items():
        inspirations = _generate_inspiration_for_tier(
            tier_key, tier_info, trends, category_profile
        )
        all_inspirations[tier_key] = {
            "tier_name": tier_info["name"],
            "tier_description": tier_info["profile"],
            "count": len(inspirations),
            "inspirations": inspirations
        }
        print(f"  - {tier_info['name']}: {len(inspirations)}条灵感")

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "category": category,
        "keywords_used": all_keywords[:10],
        "data_sources": {
            "bilibili_trending": len(trending_videos),
            "search_results": len(trends)
        },
        "inspirations": all_inspirations
    }


# ==================== 输出格式化 ====================

def print_inspirations(result: Dict):
    """打印灵感结果"""

    if "error" in result:
        print(result["error"])
        return

    print(f"\n{'#'*60}")
    print(f"# 美食品类每日创作灵感 - {result['date']}")
    print(f"# 使用关键词: {', '.join(result['keywords_used'][:5])}...")
    print(f"# 数据来源: B站{result['data_sources']['bilibili_trending']}条热门 + {result['data_sources']['search_results']}条搜索结果")
    print(f"{'#'*60}\n")

    for tier_key, tier_data in result["inspirations"].items():
        print(f"\n{'='*60}")
        print(f"【{tier_data['tier_name']}】")
        print(f"{tier_data['tier_description'][:50]}...")
        print(f"{'='*60}")

        for i, insp in enumerate(tier_data["inspirations"], 1):
            print(f"\n--- 灵感 {i} ---")
            print(f"内容类型: {insp['content_type']}")
            print(f"标题: {insp['title']}")
            print(f"\n目标受众: {insp['target_audience']}")
            print(f"\n受欢迎原因: {insp['why_popular']}")
            print(f"\n制作难点: {insp['制作难点']}")
            print(f"提供原因: {insp['provided_reason']}")
            print(f"\n内容结构: {insp['content_structure']}")

            if insp.get("reference_videos"):
                print(f"\n参考视频:")
                for ref in insp["reference_videos"]:
                    print(f"  - {ref['title']}")
                    print(f"    链接: {ref['url']}")
                    print(f"    播放: {ref.get('views_str', 'N/A')} | 时长: {ref.get('duration', 'N/A')}")

        print(f"\n")


# ==================== 旧版本兼容 ====================

def generate_daily_topics_v2(category: str = "美食", limit: int = 10) -> Dict:
    """兼容旧接口，返回简化版选题"""
    result = generate_daily_inspirations_v3(category)
    return result


def save_inspirations_to_file(result: Dict, output_dir: str = None) -> str:
    """保存灵感到 JSON 文件"""
    if output_dir is None:
        # 保存到脚本同级的 history 目录
        script_dir = Path(__file__).parent.resolve()
        output_dir = script_dir.parent / "history"
        print(f"[DEBUG] script_dir: {script_dir}")
        print(f"[DEBUG] output_dir: {output_dir}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] output_dir exists: {output_dir.exists()}")
    print(f"[DEBUG] output_dir is dir: {output_dir.is_dir()}")

    date = result.get("date", datetime.now().strftime("%Y-%m-%d"))
    filepath = output_dir / f"{date}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[DEBUG] file exists after write: {filepath.exists()}")
    print(f"[DEBUG] file size: {filepath.stat().st_size if filepath.exists() else 0}")
    print(f"[INFO] 已保存到 {filepath}")
    return str(filepath)


def main():
    """主入口"""
    print("=== 美食品类每日创作灵感生成器 V3 ===")
    print("基于主动关键词搜索 + 3层级up主差异化\n")

    result = generate_daily_inspirations_v3("美食")

    if "error" not in result:
        save_inspirations_to_file(result)
        print_inspirations(result)
    else:
        print(result["error"])


if __name__ == "__main__":
    main()
