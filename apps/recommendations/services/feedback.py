from apps.recommendations.models import RecommendationFeedback


def attach_feedback_ratings(results):
    for result in results:
        result.feedback_rating = getattr(getattr(result, "feedback", None), "rating", None)
    return results


def save_recommendation_feedback(post_data, results):
    saved_count = 0
    result_map = {result.id: result for result in results}
    for key, value in post_data.items():
        if not key.startswith("feedback_") or not value:
            continue
        try:
            result_id = int(key.removeprefix("feedback_"))
            rating = int(value)
        except ValueError:
            continue
        if result_id not in result_map or rating < 1 or rating > 5:
            continue
        RecommendationFeedback.objects.update_or_create(
            recommendation_result=result_map[result_id],
            defaults={"rating": rating},
        )
        saved_count += 1
    return saved_count
