import importlib
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

import config.settings as project_settings


class ProductionSettingsTests(SimpleTestCase):
    def reload_settings(self, env):
        with patch.dict("os.environ", env, clear=False):
            return importlib.reload(project_settings)

    def test_allowed_hosts_can_be_configured_from_environment(self):
        settings = self.reload_settings(
            {
                "ALLOWED_HOSTS": "movie-blog.onrender.com,localhost",
                "DEBUG": "False",
            }
        )

        self.assertEqual(settings.ALLOWED_HOSTS, ["movie-blog.onrender.com", "localhost"])

    def test_render_static_file_settings_are_enabled(self):
        settings = self.reload_settings({"DEBUG": "False"})

        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)
        self.assertEqual(settings.STATIC_ROOT, settings.BASE_DIR / "staticfiles")
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )

    def test_render_yaml_keeps_only_free_web_service(self):
        render_yaml = Path("render.yaml").read_text(encoding="utf-8")

        self.assertIn("type: web", render_yaml)
        self.assertIn("plan: free", render_yaml)
        self.assertNotIn("type: cron", render_yaml)
        self.assertNotIn("sync_douban_chart", render_yaml)
        self.assertNotIn("sync_douban_weekly_reputation", render_yaml)

    def test_github_actions_syncs_douban_charts_daily(self):
        workflow = Path(".github/workflows/sync-douban.yml").read_text(encoding="utf-8")

        self.assertIn("cron: \"0 20 * * *\"", workflow)
        self.assertIn("python manage.py migrate --no-input", workflow)
        self.assertIn("python manage.py blog sync --force", workflow)
        self.assertIn("SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}", workflow)
