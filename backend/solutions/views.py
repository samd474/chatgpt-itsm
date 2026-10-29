from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, REQUESTER, STAFF_ROLES, TECHNICIAN
from core.numbering import assign_number
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from reports.audit import write_audit_event

from .access import can_publish, visible_articles
from .models import Article, ArticleFeedback
from .search import suggest
from .serializers import ArticleFeedbackSerializer, ArticleSerializer, ArticleSuggestionSerializer

ArticleAccess = role_permission(
    read_roles=(REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR),
    write_roles=STAFF_ROLES,
)
# Anyone who can read an article may say whether it helped; auditors stay read-only.
FeedbackAccess = role_permission(
    read_roles=(REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR),
    write_roles=(REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR),
)


class ArticleViewSet(AuditedModelViewSet):
    """Knowledge-base articles. Technicians write drafts; managers and administrators publish and retire."""

    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, ArticleAccess]
    audit_prefix = "article"
    http_method_names = ["get", "post", "patch", "head", "options"]  # retire instead of delete
    search_fields = ["number", "title", "summary", "body", "keywords"]
    filterset_fields = ["status", "visibility", "category", "service"]
    ordering_fields = ["updated_at", "published_at", "title", "helpful_count", "not_helpful_count"]

    def get_queryset(self):
        mine = ArticleFeedback.objects.filter(article=OuterRef("pk"), user=self.request.user).values("helpful")[:1]
        qs = Article.objects.select_related("category", "service", "author").annotate(
            helpful_count=Count("feedback", filter=Q(feedback__helpful=True)),
            not_helpful_count=Count("feedback", filter=Q(feedback__helpful=False)),
            my_feedback=Subquery(mine),
        ).order_by("-updated_at")  # aggregating drops Meta.ordering; paging needs a stable order
        return visible_articles(self.request.user, qs)

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        """Published articles matching free text (e.g. a ticket subject being typed), best first."""
        q = request.query_params.get("q", "")[:300]
        return Response(ArticleSuggestionSerializer(suggest(request.user, q), many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, FeedbackAccess])
    def feedback(self, request, pk=None):
        article = self.get_object()
        if article.status != Article.Status.PUBLISHED:
            raise ValidationError({"detail": "Only published articles take feedback."})
        serializer = ArticleFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ArticleFeedback.objects.update_or_create(article=article, user=request.user,
                                                 defaults={"helpful": serializer.validated_data["helpful"]})
        return Response(self.get_serializer(self.get_queryset().get(pk=article.pk)).data)

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
