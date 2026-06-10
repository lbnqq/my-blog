from django.apps import AppConfig

from apps.admin_labels import bilingual_label


class RecommendationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.recommendations"
    verbose_name = bilingual_label("推荐管理", "Recommendation Management")
