# 博客网站 OpenCLI 命令

这个项目的 CLI 入口统一为 Django 管理命令：

```bash
python manage.py blog <command>
```

## 第一次使用流程

先进入项目根目录：

```powershell
cd "G:\作业\高级算法设计作业\博客cli"
```

更新数据库表结构：

```powershell
python manage.py migrate
```

第一次使用豆瓣榜单时，需要先抓取数据：

```powershell
python manage.py blog sync --force
```

检查系统状态：

```powershell
python manage.py blog doctor
```

查看首页 CLI 内容：

```powershell
python manage.py blog home
```

如果只是本地 SQLite 测试，可以先设置环境变量：

```powershell
$env:USE_SQLITE='1'
```

## `blog home`

查看首页当前展示内容，包括每日一片、豆瓣电影排行榜前 6 条、豆瓣一周口碑榜前 6 条。

```bash
python manage.py blog home
```

## `blog sync`

同步首页外部榜单内容。默认同步豆瓣电影排行榜和豆瓣一周口碑榜，并由已有同步服务控制抓取频率。

```bash
python manage.py blog sync
python manage.py blog sync --chart
python manage.py blog sync --weekly
python manage.py blog sync --force
```

## `blog movies`

管理本地电影库，覆盖导入、校验、搜索和详情查看。

```bash
python manage.py blog movies import data/imports/douban_top1000_import.csv
python manage.py blog movies validate data/imports/douban_top1000_import.csv
python manage.py blog movies search "霸王别姬"
python manage.py blog movies show 1291546
```

`show` 参数支持本地电影主键或豆瓣 ID。

## `blog recommend`

运行网站的电影推荐流程。命令会展示对应评分表电影，输入 1-5 分，至少评分 8 部后输出 Top20 推荐结果。

```bash
python manage.py blog recommend
python manage.py blog recommend --category romance_drama
```

## `blog doctor`

检查网站运行状态，包括数据库连接、迁移状态、电影数据、豆瓣榜单 active 数据和评分表完整性。

```bash
python manage.py blog doctor
```

## 常用演示流程

完整演示首页内容和推荐系统：

```powershell
python manage.py migrate
python manage.py blog sync --force
python manage.py blog doctor
python manage.py blog home
python manage.py blog recommend
```

只检查豆瓣榜单是否正常：

```powershell
python manage.py blog sync --force
python manage.py blog home
```

只演示本地电影库：

```powershell
python manage.py blog movies search "霸王别姬"
python manage.py blog movies show 1291546
```

可用推荐分类代码：

```text
suspense_crime
romance_drama
comedy_animation
sci_fi_action
history_war_biography
```
