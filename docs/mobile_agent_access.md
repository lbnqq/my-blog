# 手机访问站内 Agent 指南

本文档说明如何让手机访问电影资料馆的“电影助手”Agent。推荐使用公网网址部署，局域网和临时隧道适合作为测试或演示备用方案。

## 方案一：公网网址部署

适合长期使用、课程展示和给不懂技术的用户体验。用户只需要在手机浏览器打开部署地址，点击右下角“电影助手”即可聊天。

Render 环境变量建议：

```text
DEBUG=False
USE_SQLITE=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
ZHIPU_MODEL=glm-5.1
ZHIPU_API_KEY=在智谱控制台重新生成的新 key
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=movie_blog_django
SUPABASE_DB_HOST=你的 Supabase PostgreSQL Host
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
SUPABASE_DB_PASSWORD=你的数据库密码
```

如果绑定自定义域名，例如 `https://movie.example.com`，同步更新：

```text
ALLOWED_HOSTS=movie.example.com,.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://movie.example.com,https://*.onrender.com
```

注意：`ZHIPU_API_KEY` 只能配置在服务端环境变量里，不要写入代码、前端页面、Git 仓库或公开文档。此前暴露过的 key 应在正式上线前作废并重新生成。

## 方案二：同一 WiFi 局域网访问

适合你自己用手机快速测试。手机和电脑必须连同一个 WiFi。

PowerShell 示例：

```powershell
$env:USE_SQLITE='1'
$env:ALLOW_LAN_ACCESS='1'
python manage.py runserver 0.0.0.0:8010
```

对应的环境变量含义是 `ALLOW_LAN_ACCESS=1`：仅在 `DEBUG=True` 时临时放开局域网 Host，便于手机通过电脑 IP 访问。

然后在电脑上查看局域网 IP：

```powershell
ipconfig
```

手机浏览器打开：

```text
http://电脑局域网IP:8010/
```

如果打不开，通常是 Windows 防火墙没有放行 Python/Django 的 8010 端口，或者手机和电脑不在同一个网络。

## 方案三：Cloudflare Tunnel / ngrok 临时隧道

适合答辩或临时给别人体验，不适合作为长期稳定地址。

本地先启动项目：

```powershell
$env:USE_SQLITE='1'
python manage.py runserver 127.0.0.1:8010
```

再用 Cloudflare Tunnel 或 ngrok 暴露本地端口。拿到 HTTPS 地址后，把域名加入：

```text
ALLOWED_HOSTS=隧道域名,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://隧道域名
```

重启 Django 后，手机打开隧道 HTTPS 地址即可使用 Agent。

## 手机端验证清单

- 首页能打开，静态样式和海报正常显示。
- 右下角“电影助手”按钮能点击。
- 聊天面板在手机屏幕内显示，消息区可以滚动。
- 能发送“这个博客是干什么的？”并收到回复。
- 能发送“一周口碑榜和排行榜有哪些？”并看到当前数据。
- 能发送“我要电影推荐”，点击按钮进入推荐分类页。
- 登录后发送“更新榜单”，确认后能看到同步结果。
