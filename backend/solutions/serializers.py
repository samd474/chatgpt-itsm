from rest_framework import serializers

from .models import Article


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class ArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    service_name = serializers.CharField(source="service.name", default=None, read_only=True)
    author_name = serializers.SerializerMethodField()
    body = serializers.CharField(max_length=50000)

    class Meta:
        model = Article
        fields = ["id", "number", "title", "summary", "body", "keywords", "status", "visibility", "category",
                  "category_name", "service", "service_name", "author", "author_name", "published_at",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "number", "author", "published_at", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return _name(obj.author)


class TicketArticleLinkSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    unlink = serializers.BooleanField(default=False)
