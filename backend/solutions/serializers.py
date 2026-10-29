from rest_framework import serializers

from accounts.roles import AUDITOR, has_role, is_staff_user

from .models import Article


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class ArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    service_name = serializers.CharField(source="service.name", default=None, read_only=True)
    author_name = serializers.SerializerMethodField()
    body = serializers.CharField(max_length=50000)
    # Annotated by ArticleViewSet; absent (None) elsewhere, e.g. on a ticket's linked articles.
    helpful_count = serializers.IntegerField(read_only=True, default=None)
    not_helpful_count = serializers.IntegerField(read_only=True, default=None)
    my_feedback = serializers.BooleanField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = Article
        fields = ["id", "number", "title", "summary", "body", "keywords", "status", "visibility", "category",
                  "category_name", "service", "service_name", "author", "author_name", "published_at",
                  "created_at", "updated_at", "helpful_count", "not_helpful_count", "my_feedback"]
        read_only_fields = ["id", "number", "author", "published_at", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return _name(obj.author)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None
        # Vote counts are for the people who maintain the knowledge base.
        if user is None or not (is_staff_user(user) or has_role(user, AUDITOR)):
            data.pop("helpful_count", None)
            data.pop("not_helpful_count", None)
        return data


class ArticleSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "number", "title", "summary"]


class ArticleFeedbackSerializer(serializers.Serializer):
    helpful = serializers.BooleanField()


class TicketArticleLinkSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    unlink = serializers.BooleanField(default=False)
