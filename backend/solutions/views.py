from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, REQUESTER, STAFF_ROLES, TECHNICIAN
from core.numbering import assign_number
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from reports.audit import write_audit_event

from .access import can_publish, visible_articles
from .models import Article
from .serializers import ArticleSerializer

ArticleAccess = role_permission(
    read_roles=(REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR),
    write_roles=STAFF_ROLES,
)


class ArticleViewSet(AuditedModelViewSet):
    """Knowledge-base articles. Technicians write drafts; managers and administrators publish and retire."""

    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, ArticleAccess]
    audit_prefix = "article"
    http_method_names = ["get", "post", "patch", "head", "options"]  # retire instead of delete
    search_fields = ["number", "title", "summary", "body", "keywords"]
    filterset_fields = ["status", "visibility", "category", "service"]
    ordering_fields = ["updated_at", "published_at", "title"]

    def get_queryset(self):
        qs = Article.objects.select_related("category", "service", "author")
        return visible_articles(self.request.user, qs)

    def _stamp_published(self, serializer, previous_status=None):
        if serializer.validated_data.get("status") == Article.Status.PUBLISHED and previous_status != Article.Status.PUBLISHED:
            serializer.validated_data["published_at"] = timezone.now()

    def perform_create(self, serializer):
        if serializer.validated_data.get("status", Article.Status.DRAFT) != Article.Status.DRAFT and not can_publish(self.request.user):
            raise PermissionDenied("Only managers and administrators can publish articles.")
        self._stamp_published(serializer)
        article = serializer.save(author=self.request.user)
        assign_number(article, "KB")
        write_audit_event(self.request, "article.created", obj=article, before={}, after=self._snapshot(article))

    def perform_update(self, serializer):
        article = serializer.instance
        if not can_publish(self.request.user):
            new_status = serializer.validated_data.get("status", article.status)
            if article.status != Article.Status.DRAFT or new_status != Article.Status.DRAFT:
                raise PermissionDenied("Technicians can edit drafts; ask a manager to publish, retire or edit published articles.")
        self._stamp_published(serializer, previous_status=article.status)
        super().perform_update(serializer)
