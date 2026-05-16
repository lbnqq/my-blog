from dataclasses import dataclass
from statistics import variance


@dataclass(frozen=True)
class RecommendationParams:
    name: str
    similarity_weight: float
    category_weight: float
    rating_weight: float
    popularity_weight: float
    diversity_weight: float


SIMILARITY_FIRST = RecommendationParams("similarity_first", 0.50, 0.20, 0.15, 0.10, 0.05)
TYPE_FIRST = RecommendationParams("type_first", 0.35, 0.35, 0.15, 0.10, 0.05)
QUALITY_FIRST = RecommendationParams("quality_first", 0.30, 0.20, 0.30, 0.15, 0.05)
DEFAULT_PARAMS = RecommendationParams("default", 0.45, 0.25, 0.15, 0.10, 0.05)


def choose_parameter_group(rating_values):
    values = [int(value) for value in rating_values]
    if len(values) < 12:
        return TYPE_FIRST
    if len(set(values)) <= 1:
        return QUALITY_FIRST
    if variance(values) < 0.35:
        return QUALITY_FIRST
    return SIMILARITY_FIRST
