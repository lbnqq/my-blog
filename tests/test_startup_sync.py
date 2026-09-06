from django.test import SimpleTestCase

from apps.blog.services.startup_sync import should_sync_on_start


class StartupSyncTests(SimpleTestCase):
    def test_runserver_noreload_triggers_startup_sync(self):
        self.assertTrue(
            should_sync_on_start(
                argv=["manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
                environ={},
            )
        )

    def test_runserver_autoreload_child_triggers_startup_sync(self):
        self.assertTrue(
            should_sync_on_start(
                argv=["manage.py", "runserver", "127.0.0.1:8000"],
                environ={"RUN_MAIN": "true"},
            )
        )

    def test_management_commands_do_not_trigger_startup_sync(self):
        self.assertFalse(should_sync_on_start(argv=["manage.py", "test"], environ={}))
        self.assertFalse(should_sync_on_start(argv=["manage.py", "check"], environ={}))
        self.assertFalse(should_sync_on_start(argv=["manage.py", "migrate"], environ={}))

    def test_environment_can_disable_startup_sync(self):
        self.assertFalse(
            should_sync_on_start(
                argv=["manage.py", "runserver", "--noreload"],
                environ={"AUTO_SYNC_DOUBAN_ON_START": "False"},
            )
        )
