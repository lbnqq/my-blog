import importlib
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
