# 电影博客内容维护说明

## 每日一片

首页“每日一片”不需要人工维护。系统会从 `Movie` 表中选择 `rank <= 100` 的电影，并以 `2026-05-18` 为锚点按日期自动轮播：

```text
today_index = (今天日期 - 2026-05-18).days % Top100电影数量
```

如果数据库里暂时没有 Top100 排名数据，系统会回退到所有电影中按 `rank`、评分和标题排序后选择。

## 近期片讯

“近期片讯”由 Django 后台维护，模型为 `UpcomingMovieNews`。同一张表同时维护近期预告和正在热播内容。建议每条填写：

- `title`：片名。
- `original_title`：原片名，可选。
- `content_type`：选择“近期预告”或“正在热播”。
- `region`：选择“国内”或“国外”。近期预告会按这个字段分为国内预告和国外预告。
- `event_date`：上映日或预告发布日期。
- `event_label`：例如“中国大陆上映”“海外上映”“正在热映”。
- `genre_text`：展示用类型文本，例如“剧情 / 喜剧 / 爱情”。
- `highlight`：一句到两句看点说明。
- `trailer_url`：预告或影片详情链接，可选。
- `source_name` 和 `source_url`：资讯来源，可选。
- `is_active`：只有启用的内容会出现在首页。
- `sort_order`：同一天多条资讯时的展示顺序。

首页展示规则：

- 近期预告展示 6 条：国内 3 条、国外 3 条，优先展示今天到未来 7 天内的 active 内容，不足时补充更远未来内容。
- 正在热播展示 6 条，只取 `content_type=正在热播` 且 active 的内容，按 `sort_order`、日期和标题排序。
- 个性化推荐保留为首页底部入口，不和片讯模块混排。

## 加载演示数据

本地或演示环境可以加载示例预告数据：

```bash
python manage.py loaddata data/fixtures/upcoming_movie_news.json
```

示例数据仅用于页面演示。正式展示前，建议在 Django 后台更新为最新片单和来源链接。

## 缓存电影海报

豆瓣图片链接可能会禁止浏览器直接热链。为了让首页和详情页稳定显示海报，可以把远程海报缓存到本地静态目录：

```bash
python manage.py cache_movie_posters --limit 100 --rank-lte 100
```

缓存文件会写入 `static/img/posters/`。页面会优先使用本地缓存图；如果某部电影没有缓存图，则显示片名占位。

## 推荐功能入口

个性化推荐功能保留在 `/recommend/category/`，首页只作为次级入口展示。原评分和推荐结果流程没有改变。
