def generate_reason(movie_title, source_titles, shared_tags, category_label, douban_rating):
    parts = []
    if source_titles:
        titles = "、".join(f"《{title}》" for title in source_titles[:2])
        parts.append(f"因为你给 {titles} 较高评分")
    if shared_tags:
        tags = "、".join(shared_tags[:3])
        parts.append(f"系统判断你偏好 {tags} 等元素")
    if category_label:
        parts.append(f"《{movie_title}》符合你选择的 {category_label} 偏好")
    if float(douban_rating or 0) >= 8.5:
        parts.append("同时它在豆瓣评分较高，口碑稳定")
    if not parts:
        return f"《{movie_title}》与你的评分偏好较接近。"
    return "，".join(parts) + "。"
