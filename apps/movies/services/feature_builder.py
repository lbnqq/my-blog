def split_semicolon_text(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [part.strip() for part in str(value).replace("/", ";").split(";") if part.strip()]


def build_feature_tags(*values):
    tags = []
    seen = set()
    for value in values:
        for item in split_semicolon_text(value):
            if item not in seen:
                tags.append(item)
                seen.add(item)
    return tags
