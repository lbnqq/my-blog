from django.apps import AppConfig

from apps.admin_labels import bilingual_label


class RatingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ratings"
    verbose_name = bilingual_label("评分管理", "Rating Management")
