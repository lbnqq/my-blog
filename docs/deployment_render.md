# Render 免费档 + Supabase 部署流程

本项目推荐使用 Render 运行 Django 网站，继续使用 Supabase PostgreSQL 保存电影、评分表和推荐数据。

## 一、部署架构

```text
用户浏览器
  -> Render Web Service: Django 网站
  -> Supabase PostgreSQL: 电影与推荐数据
```

Render 负责运行网站程序，Supabase 只负责数据库。

## 二、部署前确认

本仓库已经包含 Render 需要的文件：

- `requirements.txt`: Python 依赖，包含 Django、Gunicorn、WhiteNoise、PostgreSQL 驱动。
- `build.sh`: Render 构建脚本，安装依赖、收集静态文件、执行迁移。
- `render.yaml`: Render Blueprint 配置。
- `config/settings.py`: 支持生产环境域名、Supabase、静态文件和 HTTPS 代理配置。

不要把 `.env` 提交到 GitHub。数据库密码只在 Render 的环境变量里填写。

## 三、在 Render 创建服务

1. 打开 Render 控制台。
2. 点击 `New +`。
3. 选择 `Blueprint`。
4. 连接 GitHub 仓库：

```text
https://github.com/lbnqq/my-blog
```

5. Render 会读取仓库里的 `render.yaml`。
6. 服务名称可以使用默认值：

```text
movie-blog-recommender
```

## 四、设置环境变量

`render.yaml` 已经写入大部分变量，但数据库密码需要你在 Render 后台手动填写：

```text
SUPABASE_DB_PASSWORD=你的 Supabase 数据库密码
```

如果不用 Blueprint，而是手动创建 Web Service，请填写这些环境变量：

```text
DEBUG=False
USE_SQLITE=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_PASSWORD=你的 Supabase 数据库密码
SUPABASE_DB_HOST=db.bbfoajvzijbvlvsjvsvb.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
SECRET_KEY=一串足够长的随机字符串
```

## 五、手动创建 Web Service 时的配置

如果你不使用 Blueprint，可以手动创建：

```text
Runtime: Python
Build Command: bash build.sh
Start Command: gunicorn config.wsgi:application
Plan: Free
```

## 六、部署后测试

部署完成后，Render 会生成一个公网地址，类似：

```text
https://movie-blog-recommender.onrender.com
```

依次测试：

1. 首页可以打开。
2. 可以进入电影类型选择页。
3. 可以选择一个类型。
4. 可以进入 20 部电影评分表。
5. 至少给 8 部电影评分。
6. 提交后生成 Top20 推荐结果。

## 七、免费档注意事项

Render 免费档适合课程项目、演示和答辩。免费服务可能会在一段时间无人访问后休眠，第一次打开网站可能需要等待几十秒。

如果访问量增加，或者需要更稳定的打开速度，可以后续升级 Render 付费实例。
