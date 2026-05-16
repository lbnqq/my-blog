from apps.ratings.models import RatingForm


def get_active_form_for_category(category):
    return (
        RatingForm.objects.filter(category=category, is_active=True)
        .prefetch_related("form_movies__movie")
        .first()
    )
