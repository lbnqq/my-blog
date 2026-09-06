import os
import sys
import threading

from django.conf import settings


_started = False


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def should_sync_on_start(argv=None, environ=None):
    argv = list(argv if argv is not None else sys.argv)
    environ = environ if environ is not None else os.environ
    if not any(arg.endswith("runserver") or arg == "runserver" for arg in argv):
        return False
    if environ.get("AUTO_SYNC_DOUBAN_ON_START", "true").lower() in {"0", "false", "no", "off"}:
        return False
    if "--noreload" in argv:
        return True
    return environ.get("RUN_MAIN") == "true"


def start_douban_sync_thread():
    global _started
    if _started or not should_sync_on_start():
        return
    _started = True

    thread = threading.Thread(target=sync_douban_on_start, name="douban-startup-sync", daemon=True)
    thread.start()


def sync_douban_on_start():
    from apps.blog.services.douban_chart import sync_douban_chart
    from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation

    force = env_flag("AUTO_SYNC_DOUBAN_FORCE", getattr(settings, "DEBUG", False))
    for label, sync_func in (
        ("豆瓣电影排行榜", sync_douban_chart),
        ("豆瓣一周口碑榜", sync_douban_weekly_reputation),
    ):
        try:
            result = sync_func(force=force)
        except Exception as exc:
            print(f"[startup-sync] {label} 自动同步失败，继续使用缓存：{exc}", flush=True)
        else:
            print(f"[startup-sync] {label}: {result.message}", flush=True)
