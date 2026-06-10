from apps.ratings.models import UserSession


def create_user_session(selected_category, user=None):
    return UserSession.objects.create(selected_category=selected_category, user=user)
