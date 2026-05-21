from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="upcomingmovienews",
            name="content_type",
            field=models.CharField(
                choices=[("upcoming", "近期预告"), ("now_showing", "正在热播")],
                default="upcoming",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="upcomingmovienews",
            name="region",
            field=models.CharField(
                choices=[("domestic", "国内"), ("foreign", "国外")],
                default="domestic",
                max_length=20,
            ),
        ),
    ]
