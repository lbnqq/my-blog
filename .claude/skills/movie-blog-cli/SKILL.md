---
name: movie-blog-cli
description: Use when a user asks for Django movie recommendation blog information or operations through natural language, including viewing homepage content, checking blog health, syncing Douban charts, searching or showing movies, importing or validating movie CSV data, and running movie recommendations. This skill maps requests to the project's existing python manage.py blog command CLI instead of querying the database or changing code directly.
---

# Movie Blog CLI

Use this skill to answer natural-language requests about this Django movie recommendation blog by invoking the existing project CLI.

Prefer the bundled script so other CLIs can run the same workflow reliably:

```powershell
python <skill-folder>/scripts/run_blog.py <blog-command> [args...] [--sqlite]
```

If the script cannot be used, run the equivalent Django command from the project root:

```powershell
python manage.py blog <command>
```

## Command Mapping

- 用户说“获取博客主页内容”“查看首页”“首页有什么内容”：运行 `home`。
- 用户说“检查博客状态”“为什么没有数据”“网站数据是否正常”：运行 `doctor`。
- 用户说“更新博客榜单”“刷新豆瓣榜单”“同步最近榜单”：运行 `sync --force`。
- 用户说“只更新豆瓣电影排行榜”：运行 `sync --chart --force`。
- 用户说“只更新一周口碑榜”：运行 `sync --weekly --force`。
- 用户说“搜索电影 XXX”：运行 `movies search "XXX"`。
- 用户说“查看电影 XXX 的详情”：运行 `movies show XXX`。`XXX` 可以是本地电影 ID 或豆瓣 ID。
- 用户说“导入电影数据”：运行 `movies import data/imports/douban_top1000_import.csv`。
- 用户说“校验电影数据”：运行 `movies validate data/imports/douban_top1000_import.csv`。
- 用户说“给我推荐电影”“运行推荐流程”：运行 `recommend`。
- 用户指定推荐类型时，运行 `recommend --category <category-code>`。

Available recommendation category codes:

```text
suspense_crime
romance_drama
comedy_animation
sci_fi_action
history_war_biography
```

## Safety Rules

- For content-only questions, prefer read-only commands: `home`, `doctor`, `movies search`, `movies show`.
- Run mutating commands only when the user clearly asks to update, sync, import, or recommend.
- `sync --force` fetches Douban data and writes to the database.
- `movies import` writes to the movie library and rebuilds rating data.
- `recommend` creates a rating session and recommendation results.
- If the user asks to use local SQLite, pass `--sqlite` to the bundled script or set `USE_SQLITE=1` before running Django directly.

## First Use

If database tables do not exist, run:

```powershell
python manage.py migrate
```

If homepage charts are empty, run:

```powershell
python <skill-folder>/scripts/run_blog.py sync --force
python <skill-folder>/scripts/run_blog.py doctor
python <skill-folder>/scripts/run_blog.py home
```

## Examples

```powershell
python <skill-folder>/scripts/run_blog.py home --sqlite
python <skill-folder>/scripts/run_blog.py doctor --sqlite
python <skill-folder>/scripts/run_blog.py movies search "霸王别姬" --sqlite
python <skill-folder>/scripts/run_blog.py movies show 1291546 --sqlite
python <skill-folder>/scripts/run_blog.py recommend --category romance_drama --sqlite
```
