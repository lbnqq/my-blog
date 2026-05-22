from django.core.management.base import BaseCommand

from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation


class Command(BaseCommand):
    help = "Sync Douban weekly reputation chart data for the homepage."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Fetch even when local weekly data is newer than 7 days.")

    def handle(self, *args, **options):
        result = sync_douban_weekly_reputation(force=options["force"])
        if result.status == "failed":
            self.stderr.write(self.style.WARNING(result.message))
            return
        self.stdout.write(self.style.SUCCESS(result.message))
