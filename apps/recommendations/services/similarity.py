def jaccard_similarity(left, right):
    left_set = {str(item).strip() for item in left if str(item).strip()}
    right_set = {str(item).strip() for item in right if str(item).strip()}
    if not left_set and not right_set:
        return 0.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def normalize_douban_rating(value):
    score = float(value or 0)
    normalized = (score - 7.0) / (9.8 - 7.0)
    return max(0.0, min(1.0, normalized))


def normalize_rank(rank, max_rank=1000):
    if not rank:
        return 0.5
    normalized = 1 - ((int(rank) - 1) / max_rank)
    return max(0.0, min(1.0, normalized))


def year_similarity(left, right):
    if not left or not right:
        return 0.0
    diff = abs(int(left) - int(right))
    return max(0.0, 1 - diff / 40)
