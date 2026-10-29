from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "status", "visibility", "author", "updated_at")
    list_filter = ("status", "visibility", "category", "service")
    search_fields = ("number", "title", "summary", "keywords")
    readonly_fields = ("number", "published_at", "created_at", "updated_at")
    filter_horizontal = ("help_requests",)
