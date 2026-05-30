# Agent 使用说明

本项目是一个 Django 电影推荐博客，已经提供统一 CLI 入口：

```powershell
python manage.py blog <command>
```

当用户用自然语言描述博客操作时，Agent 应优先调用下面的 CLI，而不是手动查询数据库或改代码。

## 自然语言到 CLI 的映射

用户说“获取博客主页内容”“查看首页”“首页有什么内容”时，运行：

```powershell
python manage.py blog home
```

用户说“更新博客榜单”“刷新豆瓣榜单”“同步最近榜单”时，运行：

```powershell
python manage.py blog sync --force
```

用户说“只更新豆瓣电影排行榜”时，运行：

```powershell
python manage.py blog sync --chart --force
```

用户说“只更新一周口碑榜”时，运行：

```powershell
python manage.py blog sync --weekly --force
```

用户说“检查博客状态”“为什么没有数据”“网站数据是否正常”时，运行：

```powershell
python manage.py blog doctor
```

用户说“搜索电影 XXX”时，运行：

```powershell
python manage.py blog movies search "XXX"
```

用户说“查看电影 XXX 的详情”时，运行：

```powershell
python manage.py blog movies show XXX
```

`XXX` 可以是本地电影 ID，也可以是豆瓣 ID。

用户说“导入电影数据”时，运行：

```powershell
python manage.py blog movies import data/imports/douban_top1000_import.csv
```

用户说“校验电影数据”时，运行：

```powershell
python manage.py blog movies validate data/imports/douban_top1000_import.csv
```

用户说“给我推荐电影”“运行推荐流程”时，运行：

```powershell
python manage.py blog recommend
```

用户指定推荐类型时，例如“给我推荐爱情剧情电影”，运行：

```powershell
python manage.py blog recommend --category romance_drama
```

可用分类代码：

```text
suspense_crime
romance_drama
comedy_animation
sci_fi_action
history_war_biography
```

## 第一次使用流程

如果数据库表不存在，先运行：

```powershell
python manage.py migrate
```

如果首页榜单为空，运行：

```powershell
python manage.py blog sync --force
```

然后检查：

```powershell
python manage.py blog doctor
python manage.py blog home
```

## 本地 SQLite 测试

如果用户明确要求使用本地 SQLite，或需要避免影响远程数据库，先设置：

```powershell
$env:USE_SQLITE='1'
```

然后再运行相关命令，例如：

```powershell
python manage.py blog home
```

## 安全规则

- `blog home`、`blog doctor`、`blog movies search`、`blog movies show` 是只读命令。
- `blog sync --force` 会抓取豆瓣数据并写入数据库。
- `blog movies import` 会写入电影库并重建评分表。
- `blog recommend` 会创建用户评分会话和推荐结果。
- 在用户只是询问内容时，优先使用只读命令。
- 在执行会修改数据库的命令前，确认用户表达的是“更新、同步、导入、推荐”等写入意图。

## 提交前验证

修改代码后，至少运行：

```powershell
$env:USE_SQLITE='1'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
