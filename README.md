# 电影推荐博客

基于 Django + Supabase PostgreSQL 的电影推荐博客系统。用户先选择偏好的电影类型，再对一组代表电影评分；系统使用 TaskCF 风格的优化协同过滤算法，从豆瓣电影数据中推荐最适合用户的 Top20 电影。

## 功能

- 五大电影类型选择：悬疑犯罪、爱情剧情、喜剧动画、科幻动作冒险、历史战争传记
- 匿名用户评分会话
- 每类 20 部代表电影评分表
- 至少 8 部评分后生成推荐
- Top20 推荐结果与推荐理由
- 豆瓣 Top1000 导入数据
- Supabase PostgreSQL 真数据库接入，未配置时可使用 SQLite

## 当前数据

- 电影总数：1000
- 分类评分表：5 个
- 评分表电影关系：100 条
- 数据来源：公开数据集 `dengfuping/douban-movies-spider`
- 生成脚本：`scripts/build_douban_top1000_import.py`
- 导入文件：`data/imports/douban_top1000_import.csv`

## 本地运行

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:8000/
```

## Supabase 配置

本项目已支持通过 `.env` 连接 Supabase PostgreSQL：

```text
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_PASSWORD=
SUPABASE_DB_HOST=db.bbfoajvzijbvlvsjvsvb.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
```

数据库密码不会提交到仓库。若 `SUPABASE_DB_HOST` 为空，项目会自动回退到本地 SQLite。

临时使用 SQLite 测试：

```bash
USE_SQLITE=1 python manage.py test
```

## 数据导入

校验 Top1000 CSV：

```bash
python manage.py validate_movie_csv data/imports/douban_top1000_import.csv --expect-count 1000
```

导入电影数据并自动重建评分表：

```bash
python manage.py import_movies data/imports/douban_top1000_import.csv
```

## 测试

```bash
python manage.py check
python manage.py test
```

## Render 部署

本项目已准备好使用 Render 免费档运行 Django，并继续连接 Supabase PostgreSQL。部署说明见：

```text
docs/deployment_render.md
```

## 项目流程

1. 用户访问首页。
2. 用户选择一个电影类型。
3. 系统展示对应分类的 20 部代表电影。
4. 用户至少给 8 部电影评分。
5. 系统计算用户偏好，并融合相似度、类型偏好、豆瓣评分、热度和排名。
6. 系统生成 Top20 推荐电影和推荐理由。

## 主要目录

```text
apps/movies/             电影模型、分类、数据导入
apps/ratings/            类型选择、评分表、匿名评分会话
apps/recommendations/    TaskCF 风格推荐算法
data/imports/            真实导入 CSV
data/reference/          分类参考
docs/data/               数据整理说明
templates/               页面模板
static/css/              页面样式
```
