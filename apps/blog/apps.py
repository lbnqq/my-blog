from django.apps import AppConfig

from apps.admin_labels import bilingual_label


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blog"
    verbose_name = bilingual_label("博客管理", "Blog Management")

    def ready(self):
        from apps.blog.services.startup_sync import start_douban_sync_thread

        start_douban_sync_thread()
