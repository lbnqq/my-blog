from django.db import models


class DoubanChartMovie(models.Model):
    douban_id = models.CharField(max_length=32, unique=True, db_index=True)
    rank = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    info_text = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    poster_url = models.URLField(blank=True)
    subject_url = models.URLField()
    fetched_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "title"]
        verbose_name = "douban chart movie"
        verbose_name_plural = "douban chart movies"

    def __str__(self):
        return f"#{self.rank} {self.title}"


class DoubanWeeklyReputationMovie(models.Model):
    douban_id = models.CharField(max_length=32, unique=True, db_index=True)
    rank = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    info_text = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    poster_url = models.URLField(blank=True)
    subject_url = models.URLField()
    fetched_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "title"]
        verbose_name = "douban weekly reputation movie"
        verbose_name_plural = "douban weekly reputation movies"

    def __str__(self):
        return f"#{self.rank} {self.title}"


class UpcomingMovieNews(models.Model):
    class ContentType(models.TextChoices):
        UPCOMING = "upcoming", "近期预告"
        NOW_SHOWING = "now_showing", "正在热播"

    class Region(models.TextChoices):
        DOMESTIC = "domestic", "国内"
        FOREIGN = "foreign", "国外"

    title = models.CharField(max_length=120)
    original_title = models.CharField(max_length=160, blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.UPCOMING)
    region = models.CharField(max_length=20, choices=Region.choices, default=Region.DOMESTIC)
    event_date = models.DateField()
    event_label = models.CharField(max_length=40)
    genre_text = models.CharField(max_length=120, blank=True)
    poster_url = models.URLField(blank=True)
    trailer_url = models.URLField(blank=True)
    source_name = models.CharField(max_length=80, blank=True)
    source_url = models.URLField(blank=True)
    highlight = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event_date", "sort_order", "title"]
        verbose_name = "upcoming movie news"
        verbose_name_plural = "upcoming movie news"

    def __str__(self):
        return self.title
