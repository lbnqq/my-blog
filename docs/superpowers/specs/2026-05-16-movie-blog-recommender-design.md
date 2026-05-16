# 电影博客推荐系统设计文档

生成日期：2026-05-16

## 1. 项目定位

本项目是一个基于 Django 和 Supabase 的电影博客推荐系统。网站面向普通电影用户，用户进入博客后先选择自己偏好的电影类型，再对一组代表电影进行 1-5 分评分。系统根据用户评分和所选类型，使用优化后的协同过滤算法 TaskCF，从豆瓣 Top1000 电影中推荐最适合用户的 20 部电影，并展示推荐理由。

本项目同时服务两个目标：

- 课程答辩：展示推荐系统流程、优化协同过滤算法、数据库设计和系统效果。
- 后续开发：作为 Django 项目搭建、Supabase 表结构、数据导入和推荐算法实现的实施依据。

## 2. 核心目标

系统需要完成以下目标：

- 提供完整的电影推荐闭环：类型选择、电影评分、推荐计算、结果展示。
- 使用 Supabase PostgreSQL 存储电影、评分表、用户评分和推荐结果。
- 使用 Django 负责页面渲染、业务逻辑、推荐算法和数据库访问。
- 支持豆瓣 Top1000 电影数据导入，并为后续整理数据模板预留标准字段。
- 将电影划分为五大主分类，降低新用户冷启动误差。
- 使用 TaskCF 思路优化传统协同过滤，使算法更适合稀疏评分场景。
- 当前版本支持匿名使用，数据库预留后续接入用户登录的能力。

## 3. 系统总体流程

用户访问流程如下：

```text
用户访问博客首页
    ↓
点击开始电影推荐
    ↓
选择五大电影偏好类型
    ↓
系统展示对应评分表
    ↓
用户对 12-20 部代表电影评分
    ↓
Django 保存评分到 Supabase
    ↓
构建用户偏好模型
    ↓
TaskCF 优化协同过滤计算推荐分数
    ↓
排除已评分电影并做多样性过滤
    ↓
返回 Top20 推荐电影
    ↓
结果页展示电影与推荐理由
```

系统由五个核心部分组成：

- 博客展示模块：首页、项目介绍、推荐入口、电影推荐结果展示。
- 评分引导模块：用户先选择五大电影类型，再填写对应电影评分表。
- 数据存储模块：Supabase PostgreSQL 存储电影、评分表、用户评分、推荐结果。
- 推荐算法模块：使用优化后的 TaskCF 思路，融合类型偏好、电影相似度、豆瓣评分和热度。
- 数据导入模块：整理豆瓣 Top1000 数据模板，并提供 CSV 导入 Supabase 的方案。

## 4. 页面与用户流程

### 4.1 首页

首页展示博客名称、电影推荐功能简介和“开始推荐”按钮。用户点击按钮后进入电影类型选择页。

### 4.2 类型选择页

用户从五类电影中选择自己更感兴趣的一类：

- 悬疑犯罪
- 爱情剧情
- 喜剧动画
- 科幻动作冒险
- 历史战争传记

用户提交选择后，系统创建匿名推荐会话，记录 `session_key` 和 `selected_category`。

### 4.3 评分表页

系统根据用户选择的类型展示对应评分表。每个表单包含 12-20 部代表电影。

每部电影展示：

- 海报
- 电影名
- 年份
- 类型
- 豆瓣评分
- 一句简介
- 1-5 分评分控件

交互规则：

- 用户至少评分 8 部电影才能提交。
- 用户可以跳过没看过的电影。
- 评分范围为 1-5 分。
- 提交前进行评分数量校验。

### 4.4 推荐计算页

推荐计算如果较快，可以不单独显示中间页，提交评分后直接跳转结果页。若需要增强体验，可显示“正在分析偏好、计算相似电影、生成推荐理由”等状态文案。

### 4.5 推荐结果页

推荐结果页展示最终推荐的 20 部电影。

每部电影展示：

- 推荐排名
- 海报
- 电影名
- 年份
- 类型
- 豆瓣评分
- 推荐理由

结果页提供“重新测试”“返回首页”“查看电影详情”等入口。

## 5. 功能模块设计

Django 项目建议分为以下模块：

```text
blog
    负责首页、博客介绍、普通展示页面。

movies
    负责电影数据模型、电影查询、豆瓣数据导入、五大类分类。

ratings
    负责用户匿名会话、类型选择、评分表展示、评分提交。

recommendations
    负责推荐算法、推荐理由生成、推荐结果保存和展示。

data_import
    负责豆瓣 Top1000 数据模板与导入脚本。
```

## 6. Supabase 数据库设计

Supabase 作为后端数据库使用，Django 通过 PostgreSQL 连接它。当前版本由 Django 服务端访问数据库，浏览器不直接访问 Supabase。

### 6.1 movies

存储豆瓣 Top1000 电影基础信息。

```text
id                    主键
douban_id             豆瓣电影 ID，可为空
title                 中文片名
original_title        原片名
year                  上映年份
directors             导演，JSON 或文本
actors                主演，JSON 或文本
genres                原始类型标签，JSON
countries             国家/地区，JSON
rating                豆瓣评分
rating_count          评分人数
rank                  豆瓣 Top1000 排名
poster_url            海报地址
summary               简介
main_category         五大主分类
feature_tags          算法使用的特征标签，JSON
created_at            创建时间
updated_at            更新时间
```

### 6.2 rating_forms

存储五种评分表。

```text
id                    主键
category              对应五大分类
title                 表单标题
description           表单说明
is_active             是否启用
created_at            创建时间
```

### 6.3 rating_form_movies

存储评分表和电影的对应关系。

```text
id                    主键
form_id               评分表 ID
movie_id              电影 ID
sort_order            展示顺序
is_required           是否重点样本
created_at            创建时间
```

### 6.4 user_sessions

存储匿名用户的一次推荐会话。

```text
id                    主键
session_key           匿名用户会话标识
selected_category     用户选择的电影大类
user_id               预留字段，未来接入登录系统
created_at            创建时间
completed_at          完成推荐时间
```

### 6.5 user_ratings

存储用户对电影的评分。

```text
id                    主键
session_id            用户会话 ID
movie_id              被评分电影 ID
rating                用户评分，1-5
created_at            创建时间
```

约束：

- 同一个 session 对同一部 movie 只能评分一次。
- rating 必须在 1 到 5 之间。

### 6.6 recommendation_results

存储系统最终推荐结果。

```text
id                    主键
session_id            用户会话 ID
movie_id              推荐电影 ID
score                 推荐得分
rank_order            推荐排名，1-20
reason                推荐理由
algorithm_version     算法版本，例如 taskcf_v1
created_at            创建时间
```

## 7. 电影分类与数据模板

### 7.1 五大分类

数据库中使用稳定英文编码，页面展示时转换为中文。

```text
suspense_crime         悬疑犯罪
romance_drama          爱情剧情
comedy_animation       喜剧动画
sci_fi_action          科幻动作冒险
history_war_biography  历史战争传记
```

每部电影保留两类分类信息：

- `main_category`：五大主分类之一。
- `genres`：电影原始类型标签，例如剧情、爱情、犯罪、动画。

### 7.2 豆瓣 Top1000 数据模板

后续整理 CSV 数据模板，字段如下：

```text
douban_id
title
original_title
year
directors
actors
genres
countries
rating
rating_count
rank
poster_url
summary
main_category
feature_tags
```

示例数据：

```text
douban_id: 1292052
title: 肖申克的救赎
original_title: The Shawshank Redemption
year: 1994
directors: 弗兰克·德拉邦特
actors: 蒂姆·罗宾斯; 摩根·弗里曼
genres: 剧情; 犯罪
countries: 美国
rating: 9.7
rating_count: 3000000
rank: 1
poster_url: https://example.com/poster.jpg
summary: 一场关于希望与自由的故事
main_category: suspense_crime
feature_tags: 剧情; 犯罪; 监狱; 人性; 高评分
```

### 7.3 评分表选片原则

每个分类评分表选择 12-20 部代表电影，要求：

- 知名度较高，用户更可能看过。
- 豆瓣评分较高，数据质量稳定。
- 风格覆盖全面，避免同质化。
- 年份分布合理，兼顾经典电影和较新的电影。

## 8. TaskCF 优化推荐算法设计

本项目将课程文档中的 TaskCF 思路适配到电影网站场景。

原 TaskCF 核心优化点：

- 任务分解：根据兴趣分组，提高匹配质量。
- 变权重相似度：共同评分少时降低相似度可信度，缓解稀疏问题。
- 竞争进化：通过多组参数选择更合适的推荐参数。

电影网站适配方式：

- 任务分解：用户先选择五大电影类型，系统对该偏好领域增强推荐。
- 变权重相似度：根据评分数量和共同标签数量调整相似度可信度。
- 竞争进化：预设多组推荐参数，根据用户评分特征选择参数组。

### 8.1 用户偏好向量

用户评分转换为偏好权重：

```text
5 分：强喜欢，权重 +2.0
4 分：喜欢，权重 +1.0
3 分：中性，权重 +0.2
2 分：不喜欢，权重 -1.0
1 分：强不喜欢，权重 -2.0
```

系统从评分电影中提取：

- 类型偏好
- 导演偏好
- 国家/地区偏好
- 年代偏好
- 关键词偏好
- 高分电影列表
- 低分电影列表

### 8.2 电影相似度

候选电影与用户已评分电影进行相似度计算。

```text
movie_similarity =
0.40 × 类型相似度
+ 0.15 × 导演相似度
+ 0.15 × 主演相似度
+ 0.10 × 国家地区相似度
+ 0.10 × 年份相似度
+ 0.10 × 关键词相似度
```

再根据用户评分权重加权：

```text
similarity_score =
Σ(用户评分权重 × 候选电影与已评分电影相似度)
```

### 8.3 变权重相似度

评分数量较少时降低相似度可信度：

```text
confidence = min(1, 用户评分数量 / 12)
weighted_similarity = similarity_score × confidence
```

共同标签太少时进行惩罚：

```text
tag_penalty = min(1, 共同标签数量 / 3)
adjusted_similarity = weighted_similarity × tag_penalty
```

### 8.4 类型增强

如果候选电影属于用户选择的主分类，则获得额外加成：

```text
same_category_boost = 1.15
```

系统不会只推荐同主分类电影，避免结果过窄。

### 8.5 参数选择

系统预设三组参数：

```text
参数组 A：相似度优先
适合评分数量多、偏好明显的用户。

参数组 B：类型优先
适合评分数量少、冷启动明显的用户。

参数组 C：质量优先
适合评分分布不明显、大量评分接近 3 分的用户。
```

默认参数：

```text
similarity_weight = 0.45
category_weight = 0.25
rating_weight = 0.15
popularity_weight = 0.10
diversity_weight = 0.05
```

选择规则：

```text
评分数量 >= 12 且评分方差较大 → 参数组 A
评分数量 < 12 → 参数组 B
评分方差较小 → 参数组 C
```

### 8.6 最终推荐分数

```text
final_score =
similarity_weight × similarity_score
+ category_weight × category_score
+ rating_weight × douban_rating_score
+ popularity_weight × popularity_score
+ diversity_weight × diversity_score
```

如果电影属于用户选择的主分类：

```text
final_score = final_score × 1.15
```

### 8.7 多样性过滤

最终 Top20 推荐结果需要进行多样性过滤：

- 同一导演最多 3 部。
- 同一电影系列最多 2 部。
- 同一细分类型不要过度集中。
- 尽量覆盖 2-4 个相关类型标签。

### 8.8 推荐理由生成

推荐理由使用规则生成，不依赖外部大模型。

示例：

```text
因为你给《盗梦空间》和《看不见的客人》较高评分，
系统判断你偏好悬疑、反转和高概念剧情。
《致命魔术》同样具有悬疑和反转特征，并且豆瓣评分较高。
```

### 8.9 推荐伪代码

```python
def recommend_movies(session_id):
    session = get_user_session(session_id)
    ratings = get_user_ratings(session_id)

    preference = build_user_preference_vector(ratings)
    params = choose_parameter_group(ratings)

    candidates = get_movies_excluding_rated(ratings)
    scored_movies = []

    for movie in candidates:
        similarity_score = calculate_similarity(preference, movie)
        category_score = calculate_category_score(movie, session.selected_category)
        douban_score = normalize_douban_rating(movie.rating)
        popularity_score = normalize_rank(movie.rank)
        diversity_score = calculate_diversity_score(movie)

        final_score = (
            params.similarity_weight * similarity_score
            + params.category_weight * category_score
            + params.rating_weight * douban_score
            + params.popularity_weight * popularity_score
            + params.diversity_weight * diversity_score
        )

        if movie.main_category == session.selected_category:
            final_score *= 1.15

        scored_movies.append((movie, final_score))

    ranked_movies = sort_by_score(scored_movies)
    result = apply_diversity_filter(ranked_movies, limit=20)
    save_recommendation_results(session_id, result)

    return result
```

## 9. Django 项目结构

建议项目命名为 `movie_blog_recommender`。

```text
movie_blog_recommender/
    manage.py
    config/
        settings.py
        urls.py
        wsgi.py
        asgi.py

    apps/
        blog/
            models.py
            views.py
            urls.py
            templates/blog/

        movies/
            models.py
            views.py
            urls.py
            services/
                importer.py
                classifier.py
                feature_builder.py

        ratings/
            models.py
            forms.py
            views.py
            urls.py
            services/
                session_service.py
                rating_form_service.py

        recommendations/
            models.py
            views.py
            urls.py
            services/
                recommender.py
                similarity.py
                parameter_selector.py
                reason_generator.py

    templates/
        base.html
        home.html
        select_category.html
        rating_form.html
        recommendation_result.html

    static/
        css/
        js/
        images/

    data/
        templates/
            douban_top1000_template.csv
        samples/
            sample_movies.csv

    docs/
        database-design.md
        algorithm-design.md
        user-flow.md
```

## 10. URL 与接口流程

核心页面 URL：

```text
/                         首页
/recommend/start/         开始推荐
/recommend/category/      选择电影类型
/recommend/rate/<sid>/    填写评分表
/recommend/result/<sid>/  查看推荐结果
/movies/<id>/             电影详情，可选
/admin/                   Django 后台
```

视图流程：

```text
GET /
    返回首页模板。

GET /recommend/category/
    展示五大电影类型。

POST /recommend/category/
    创建 user_sessions，保存 selected_category，跳转评分表页。

GET /recommend/rate/<session_key>/
    根据 selected_category 查询对应 rating_form 和 rating_form_movies，展示评分表。

POST /recommend/rate/<session_key>/
    校验至少评分 8 部电影，保存 user_ratings，调用推荐算法，跳转推荐结果页。

GET /recommend/result/<session_key>/
    查询 recommendation_results，按 rank_order 排序后展示 Top20。
```

## 11. Supabase 连接与安全

Django 通过环境变量连接 Supabase PostgreSQL：

```text
SUPABASE_DB_NAME
SUPABASE_DB_USER
SUPABASE_DB_PASSWORD
SUPABASE_DB_HOST
SUPABASE_DB_PORT
SECRET_KEY
DEBUG
```

Django 配置示例：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("SUPABASE_DB_NAME"),
        "USER": env("SUPABASE_DB_USER"),
        "PASSWORD": env("SUPABASE_DB_PASSWORD"),
        "HOST": env("SUPABASE_DB_HOST"),
        "PORT": env("SUPABASE_DB_PORT", default="5432"),
    }
}
```

安全要求：

- 数据库连接信息只放在 Django 环境变量中。
- 不在前端暴露 Supabase service_role key。
- 当前阶段由 Django 服务端访问数据库。
- 如果后续开放 Supabase Data API，需要启用 RLS 并设计访问策略。

## 12. 数据导入流程

导入命令建议：

```text
python manage.py import_movies data/templates/douban_top1000_template.csv
```

导入步骤：

```text
读取 CSV
校验必要字段
转换 genres/directors/actors 为列表或 JSON
校验 main_category 是否属于五大分类
写入 movies 表
生成 feature_tags
生成或更新五类评分表
```

## 13. 测试方案

### 13.1 数据测试

- 电影数据是否能成功导入。
- 五大分类是否合法。
- 评分表是否都绑定了电影。
- 每个评分表是否至少有 12 部电影。

### 13.2 页面流程测试

- 首页能打开。
- 类型选择能提交。
- 评分表能根据类型正确展示。
- 评分不足 8 部时不能提交。
- 评分成功后能跳转结果页。

### 13.3 推荐算法测试

- 推荐结果不包含用户已评分电影。
- 推荐结果数量为 20 部。
- 同类型电影有合理加权。
- 高评分电影有合理优势。
- 低分偏好会降低相似电影推荐。

### 13.4 数据库测试

- `user_sessions` 能正确创建。
- `user_ratings` 能正确保存。
- `recommendation_results` 能正确保存。
- 同一 session 不重复评分同一电影。

## 14. 答辩展示流程

答辩演示建议按以下顺序：

```text
1. 展示首页。
2. 选择一个电影类型，例如悬疑犯罪。
3. 对评分表中的电影打分。
4. 提交评分。
5. 展示推荐结果 Top20。
6. 解释推荐理由。
7. 展示 Supabase 中保存的评分和推荐结果。
8. 说明 TaskCF 优化点。
```

重点说明：

- 系统通过类型选择降低冷启动误差。
- 评分表只要求用户评价少量代表电影，降低使用门槛。
- 推荐算法融合电影相似度、类型偏好、豆瓣评分和热度。
- TaskCF 的任务分解、变权重相似度和参数选择思想都已适配到网站推荐流程中。

## 15. 后续实施顺序

后续开发建议按以下阶段推进：

```text
1. 创建 Django 项目和基础配置。
2. 配置 Supabase PostgreSQL 连接。
3. 创建 movies、ratings、recommendations、blog 模块。
4. 设计 Django models 并执行迁移。
5. 创建豆瓣 Top1000 数据模板和示例数据。
6. 实现电影数据导入命令。
7. 实现首页、类型选择页、评分表页。
8. 实现用户评分保存。
9. 实现 TaskCF 推荐算法服务。
10. 实现推荐结果页和推荐理由。
11. 编写测试并验证完整流程。
12. 准备答辩截图、流程图和算法说明。
```

## 16. 设计结论

本项目最终设计为“Django 博客系统 + Supabase 数据库 + 豆瓣 Top1000 数据模板 + 五类电影评分表 + TaskCF 优化推荐算法”的课程项目增强版。它既能作为可运行的网站项目，也能在课程答辩中清晰展示算法设计、系统流程、数据库结构和推荐效果。
