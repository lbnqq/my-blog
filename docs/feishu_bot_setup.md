# 飞书电影博客机器人接入说明

本项目通过飞书企业自建应用机器人接入站内电影助手。飞书负责接收用户消息，Django 负责查询博客数据、搜索电影并返回推荐入口。

## 开放平台配置

1. 进入飞书开放平台，创建企业自建应用并启用机器人能力。
2. 在权限管理中申请消息接收与回复相关权限：
   - 接收用户发给机器人的单聊消息。
   - 接收群聊中 @ 机器人的消息。
   - 发送或回复消息。
3. 在事件订阅中配置请求地址：

```text
https://你的域名/agent/feishu/events/
```

4. 订阅事件：

```text
im.message.receive_v1
```

5. 将开放平台中的 App ID、App Secret、Verification Token、Encrypt Key 写入部署环境变量。

## 环境变量

```text
SITE_PUBLIC_URL=https://你的域名
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_ENCRYPT_KEY=xxx
```

`SITE_PUBLIC_URL` 用于把站内相对链接转换为飞书里可打开的 HTTPS 链接。

## 本地联调

飞书事件订阅要求公网 HTTPS 地址。本地开发时可以先启动 Django，再用 Cloudflare Tunnel 或 ngrok 暴露端口：

```powershell
$env:USE_SQLITE='1'
python manage.py runserver 127.0.0.1:8010
```

拿到公网 HTTPS 地址后，更新：

```text
ALLOWED_HOSTS=隧道域名,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://隧道域名
SITE_PUBLIC_URL=https://隧道域名
```

然后把飞书事件订阅请求地址设置为：

```text
https://隧道域名/agent/feishu/events/
```

## 当前能力边界

- 支持博客介绍、首页榜单、电影搜索和推荐入口。
- 飞书端不直接执行同步榜单、导入数据等写库操作；需要回到网站登录后确认执行。
- 支持使用 `FEISHU_ENCRYPT_KEY` 解密飞书加密推送，并会校验 `X-Lark-Signature` 请求签名。
