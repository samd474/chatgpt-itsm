from django.conf import settings
from django.db import models

from helprequests.models import Category, HelpRequests, Services


class Article(models.Model):
    """A knowledge-base solution. Plain text only: the frontend renders the body as text, never as HTML."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"  # requesters can read it once published
        INTERNAL = "internal", "Internal"  # staff only

    # Filled in after insert (KB-000001); null until then so unsaved rows never collide on "".
    number = models.CharField(max_length=24, unique=True, null=True, blank=True, editable=False)
    title = models.CharField(max_length=240)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    keywords = models.CharField(max_length=500, blank=True, help_text="Extra search terms, e.g. error messages.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.INTERNAL)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_articles")
    help_requests = models.ManyToManyField(HelpRequests, blank=True, related_name="articles")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["status", "visibility"])]

    def __str__(self):
        return f"{self.number} {self.title}" if self.number else self.title


class ArticleFeedback(models.Model):
    """One "was this helpful?" vote per person per article; voting again changes it."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_feedback")
    helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["article", "user"], name="one_feedback_per_user_per_article")]
