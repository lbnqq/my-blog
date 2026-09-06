# Render 部署说明

这个项目适合部署成 Render Web Service，并使用 Supabase PostgreSQL 保存数据。部署完成后，网站运行在 Render 云端，即使本机电脑关机，其他人也能通过公开 HTTPS 地址访问。

## 部署架构

- Web 服务：Render，运行 `gunicorn config.wsgi:application`
- 数据库：Supabase PostgreSQL
- 静态文件：Django `collectstatic` + WhiteNoise
- 榜单同步：GitHub Actions 每天执行 `python manage.py blog sync --force`

## 部署步骤

1. 将代码推送到 GitHub。
2. 登录 Render，选择 New Blueprint。
3. 连接这个项目的 GitHub 仓库。
4. Render 会读取仓库根目录的 `render.yaml` 并创建 `movie-blog-recommender` Web Service。
5. 在 Render 的环境变量里填入 `SUPABASE_DB_PASSWORD` 和需要保密的 API Key。
6. 部署完成后，访问 Render 提供的 `https://*.onrender.com` 地址。

## 必要环境变量

```text
DEBUG=False
USE_SQLITE=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
SECRET_KEY=<Render 自动生成或自行填写>
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_HOST=db.bbfoajvzijbvlvsjvsvb.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
SUPABASE_DB_PASSWORD=<Supabase 数据库密码>
```

## 榜单自动更新

仓库已经包含 `.github/workflows/sync-douban.yml`，每天会向 Supabase 数据库同步豆瓣电影排行榜和一周口碑榜。需要在 GitHub 仓库配置：

- Repository secret: `SECRET_KEY`
- Repository secret: `SUPABASE_DB_PASSWORD`
- Repository variable: `SUPABASE_DB_NAME`
- Repository variable: `SUPABASE_DB_USER`
- Repository variable: `SUPABASE_DB_HOST`
- Repository variable: `SUPABASE_DB_PORT`
- Repository variable: `SUPABASE_DB_SSLMODE`

如果要立即更新，可以在 GitHub Actions 页面手动运行 `Sync Douban Charts` workflow。

## 本地和线上区别

本地开发：

```powershell
$env:USE_SQLITE='1'
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

线上部署：

```text
Render + Supabase，不依赖本机电脑开机。
```
