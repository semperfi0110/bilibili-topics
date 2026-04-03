# B站美食创作灵感

每日为B站美食UP主推送差异化创作选题灵感。

## 功能

- **3层级差异化灵感**：针对头部、中腰部、长尾/新人UP主生成不同方向的选题
- **真实B站数据**：基于B站搜索结果，参考真实热门视频
- **每日自动更新**：每天10:00 UTC自动生成新选题
- **历史记录**：支持查看过往日期的灵感内容

## 技术架构

- **数据生成**：Python + B站搜索API
- **托管平台**：GitHub Pages (免费)
- **自动执行**：GitHub Actions (免费额度)

## 本地运行

```bash
# 生成今日灵感
python3 .claude/skills/topic-generator/generator.py

# 查看生成的JSON文件
cat ~/.claude/data/bilibili-topics/history/$(date +%Y-%m-%d).json
```

## 部署说明

1. Fork 或克隆此仓库
2. 在 GitHub 仓库设置中启用 GitHub Pages (Settings → Pages → Deploy from branch: main)
3. GitHub Actions 将自动在每天 10:00 UTC 执行

## 查看灵感

访问: `https://yourusername.github.io/bilibili-topics`

## 数据来源

- 关键词扩展自美食品类特征
- 参考视频来自B站真实搜索结果
- 过滤非美食内容（游戏、美妆、娱乐综艺等）
