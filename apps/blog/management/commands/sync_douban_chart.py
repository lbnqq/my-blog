from django.core.management.base import BaseCommand

from apps.blog.services.douban_chart import sync_douban_chart


class Command(BaseCommand):
    help = "Sync Douban movie chart data for the homepage ranking module."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Fetch even when local chart data is newer than 3 days.")

    def handle(self, *args, **options):
        result = sync_douban_chart(force=options["force"])
        if result.status == "failed":
            self.stderr.write(self.style.WARNING(result.message))
            return
        self.stdout.write(self.style.SUCCESS(result.message))
