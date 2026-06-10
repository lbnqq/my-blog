from django.apps import AppConfig

from apps.admin_labels import bilingual_label


class MoviesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.movies"
    verbose_name = bilingual_label("电影管理", "Movie Management")
