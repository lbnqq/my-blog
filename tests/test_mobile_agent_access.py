import importlib
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

import config.settings as project_settings


class MobileAgentAccessTests(SimpleTestCase):
    def reload_settings(self, env):
        with patch.dict("os.environ", env, clear=False):
            return importlib.reload(project_settings)

    def test_debug_lan_access_can_be_enabled_for_phone_testing(self):
        settings = self.reload_settings(
            {
                "DEBUG": "True",
                "ALLOW_LAN_ACCESS": "1",
                "ALLOWED_HOSTS": "127.0.0.1,localhost",
            }
        )

        self.assertIn("*", settings.ALLOWED_HOSTS)

    def test_lan_access_flag_is_ignored_when_debug_is_disabled(self):
        settings = self.reload_settings(
            {
                "DEBUG": "False",
                "ALLOW_LAN_ACCESS": "1",
                "ALLOWED_HOSTS": "movie-blog.onrender.com",
            }
        )

        self.assertEqual(settings.ALLOWED_HOSTS, ["movie-blog.onrender.com"])

    def test_render_deployment_exposes_agent_environment_variables(self):
        render_yaml = Path("render.yaml").read_text(encoding="utf-8")

        self.assertIn("ZHIPU_API_KEY", render_yaml)
        self.assertIn("sync: false", render_yaml)
        self.assertIn("ZHIPU_MODEL", render_yaml)
        self.assertIn("glm-5.1", render_yaml)
        self.assertIn("https://*.onrender.com", render_yaml)

    def test_mobile_agent_css_uses_phone_friendly_panel_layout(self):
        css = Path("static/css/site.css").read_text(encoding="utf-8")
        base_template = Path("templates/base.html").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn("width: calc(100vw - 24px)", css)
        self.assertIn("max-height: calc(100dvh - 96px)", css)
        self.assertIn("-webkit-overflow-scrolling: touch", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".movie-agent__panel[hidden]", css)
        self.assertIn("display: none", css)
        self.assertIn("css/site.css' %}?v=20260616-mobile-agent", base_template)

    def test_mobile_access_guide_documents_all_supported_paths(self):
        guide = Path("docs/mobile_agent_access.md").read_text(encoding="utf-8")

        self.assertIn("公网网址部署", guide)
        self.assertIn("同一 WiFi", guide)
        self.assertIn("Cloudflare Tunnel", guide)
        self.assertIn("ALLOW_LAN_ACCESS=1", guide)
        self.assertIn("ZHIPU_API_KEY", guide)
