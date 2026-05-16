# 电影推荐博客

基于 Django + Supabase PostgreSQL 的电影博客推荐系统。用户选择电影偏好类型后，对代表电影评分，系统使用 TaskCF 风格的优化协同过滤算法推荐电影。

## 功能

- 五大电影类型选择
- 匿名用户评分会话
- 电影评分表
- TaskCF 风格推荐算法
- Top20 推荐结果与推荐理由
- 豆瓣 Top1000 CSV 数据模板
- Supabase PostgreSQL 配置，未配置时自动使用 SQLite

## 本地运行

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_movies data/samples/sample_movies.csv
python manage.py runserver 127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:8000/
```

## Supabase 配置

复制 `.env.example` 为 `.env`，填写 Supabase PostgreSQL 连接信息：

```text
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_PASSWORD=
SUPABASE_DB_HOST=db.bbfoajvzijbvlvsjvsvb.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
```

如果 `SUPABASE_DB_HOST` 留空，项目会使用本地 SQLite，方便开发和演示。

如果已经配置了 Supabase，但想临时用 SQLite 跑本地测试，可以设置：

```bash
USE_SQLITE=1
```

当前 Supabase 项目：

```text
Project name: movie-blog-recommender
Project ref: bbfoajvzijbvlvsjvsvb
Region: ap-southeast-1
API URL: https://bbfoajvzijbvlvsjvsvb.supabase.co
```

数据库密码不会提交到仓库。本项目已创建 Django 专用数据库用户 `movie_blog_django`，本地 `.env` 的 `SUPABASE_DB_PASSWORD` 填写该用户密码。

## 测试

```bash
python manage.py test
```

## 数据模板

豆瓣 Top1000 数据模板：

```text
data/templates/douban_top1000_template.csv
```

样例数据：

```text
data/samples/sample_movies.csv
```
