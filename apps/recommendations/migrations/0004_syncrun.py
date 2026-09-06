import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("recommendations", "0003_alter_recommendationfeedback_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(choices=[("douban_chart", "豆瓣电影排行榜"), ("weekly_reputation", "豆瓣一周口碑榜")], db_index=True, max_length=32)),
                ("status", models.CharField(choices=[("running", "执行中"), ("success", "成功"), ("skipped", "已跳过"), ("failed", "失败")], db_index=True, default="running", max_length=16)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("triggered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="analytics_sync_runs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "数据同步记录",
                "verbose_name_plural": "数据同步记录",
                "ordering": ["-started_at"],
            },
        ),
    ]
