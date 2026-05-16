CATEGORY_LABELS = {
    "suspense_crime": "悬疑犯罪",
    "romance_drama": "爱情剧情",
    "comedy_animation": "喜剧动画",
    "sci_fi_action": "科幻动作冒险",
    "history_war_biography": "历史战争传记",
}

CATEGORY_KEYWORDS = {
    "suspense_crime": {"悬疑", "犯罪", "惊悚", "推理", "黑色电影"},
    "romance_drama": {"爱情", "剧情", "文艺", "青春", "家庭"},
    "comedy_animation": {"喜剧", "动画", "儿童", "家庭", "治愈"},
    "sci_fi_action": {"科幻", "动作", "冒险", "奇幻", "灾难"},
    "history_war_biography": {"历史", "战争", "传记", "纪录片"},
}


def normalize_category(value):
    if value in CATEGORY_LABELS:
        return value

    for code, label in CATEGORY_LABELS.items():
        if value == label:
            return code

    return "romance_drama"


def classify_main_category(genres):
    genre_set = {str(genre).strip() for genre in genres if str(genre).strip()}
    scores = {}
    for code, keywords in CATEGORY_KEYWORDS.items():
        scores[code] = len(genre_set & keywords)

    best_code = max(scores, key=scores.get)
    if scores[best_code] == 0:
        return "romance_drama"
    return best_code
