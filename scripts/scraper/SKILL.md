# Bilibili Trend Scraper Skill

## 职责
抓取B站美食类目下的高热视频数据，为选题生成提供数据支撑。

## 能力范围
- 获取B站美食分类热门视频
- 发现低粉高播的潜力视频
- 获取视频详情（播放量、点赞、投币、收藏）
- 搜索特定关键词相关的热门视频

## 数据源
- B站公开API
- B站网页版爬取

## 输出格式

```json
{
  "timestamp": "2026-04-02T10:00:00Z",
  "category": "美食",
  "hot_videos": [
    {
      "title": "视频标题",
      "bvid": "BV1GJ411x7h7",
      "author": "UP主名",
      "views": 152000,
      "likes": 12000,
      "coins": 3500,
      "favorites": 8900,
      "share": 1200,
      "duration": "12:34",
      "pubdate": "2026-04-01",
      "desc": "视频简介",
      "tags": ["美食", "探店", "成都"]
    }
  ],
  "rising_videos": [
    {
      "title": "低粉高播视频标题",
      "bvid": "BVxxxx",
      "author": "UP主名",
      "followers": 5000,
      "views": 150000,
      "views_to_followers_ratio": 30,
      "tags": ["美食", "快手菜"]
    }
  ],
  "category_rank": {
    "rank_type": "美食周榜",
    "videos": [...]
  }
}
```

## 使用方式

### 获取美食类热门视频
```
名称: 获取B站美食类热门视频
参数:
  - limit: 获取数量 (默认20, 最大50)
  - time_range: 时间范围 (day/week/month/all)
```

### 搜索关键词相关视频
```
名称: 搜索B站美食相关视频
参数:
  - keyword: 搜索关键词
  - limit: 获取数量 (默认10)
```

### 获取视频详情
```
名称: 获取B站视频详情
参数:
  - bvid: 视频BV号
```

## 技术实现
- 使用B站公开API: `api.bilibili.com`
- requests库进行HTTP请求
- 数据清洗和格式化

## 注意事项
- 遵守B站robots.txt
- 控制请求频率，避免封禁
- 视频数据会有一定延迟
