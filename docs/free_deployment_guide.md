# 免费部署指南

目标架构：

```text
GitHub 仓库
  -> Render 免费 Web Service
  -> Supabase Free PostgreSQL

GitHub Actions
  -> 每天执行 python manage.py blog sync --force
```

Render 只运行 Django 网站。豆瓣榜单同步由 GitHub Actions 定时执行，避免使用 Render Cron Job 产生额外费用。

## 1. Supabase 数据库

在 Supabase Free 项目中准备 PostgreSQL 数据库，并记录以下信息：

```text
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_HOST=db.<project-ref>.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
SUPABASE_DB_PASSWORD=<你的数据库密码>
```

如果使用默认 `postgres` 用户，也可以把 `SUPABASE_DB_USER` 设置为 `postgres`。项目代码会在 `USE_SQLITE=False` 且存在 `SUPABASE_DB_HOST` 时连接 Supabase。

## 2. Render Web Service

在 Render 中创建 Web Service，连接 GitHub 仓库。项目根目录已有 `render.yaml`，Render 会使用：

```text
buildCommand: bash build.sh
startCommand: gunicorn config.wsgi:application
```

`build.sh` 会安装依赖、收集静态文件并执行迁移：

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
```

Render 环境变量：

```text
DEBUG=False
USE_SQLITE=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_HOST=db.<project-ref>.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
SUPABASE_DB_PASSWORD=<你的数据库密码>
SECRET_KEY=<Render 自动生成或手动设置>
```

Render 免费 Web Service 会在无访问时休眠，首次打开可能较慢，这是免费服务的正常限制。

## 3. GitHub Actions 定时同步

仓库中已提供：

```text
.github/workflows/sync-douban.yml
```

它支持手动触发，也会每天定时执行：

```text
UTC 20:00
北京时间 04:00
```

执行命令：

```bash
python manage.py blog sync --force
```

## 4. GitHub Secrets 和 Variables

进入 GitHub 仓库：

```text
Settings -> Secrets and variables -> Actions
```

新增 Secrets：

```text
SECRET_KEY
SUPABASE_DB_PASSWORD
```

新增 Variables：

```text
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_HOST=db.<project-ref>.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
```

## 5. 首次上线流程

1. 推送代码到 GitHub。
2. 在 Render 创建 Web Service 并连接仓库。
3. 在 Render 填写环境变量。
4. 等待 Render 部署成功。
5. 在 GitHub Actions 页面手动运行 `Sync Douban Charts`。
6. 打开 Render 线上地址检查首页。

## 6. 验证

本地提交前运行：

```powershell
$env:USE_SQLITE='1'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

线上验证：

```text
Render Deploy: succeeded
GitHub Actions Sync Douban Charts: succeeded
首页每日电影有海报
豆瓣电影排行榜有数据
豆瓣一周口碑榜有数据
查看详情按钮跳转豆瓣 subject 页面
```

如果榜单为空，先手动运行一次 GitHub Actions，或在 Render Shell 中执行：

```bash
python manage.py blog sync --force
```
