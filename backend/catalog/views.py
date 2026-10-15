from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from helprequests.permissions import NotReadOnlyAuditor
from helprequests.serializers import HelpRequestsReadSerializer

from .models import CatalogItem
from .serializers import CatalogItemSerializer, CatalogSubmitSerializer
from .services import submit_catalog_item


class CatalogItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CatalogItemSerializer
    queryset = CatalogItem.objects.filter(active=True)
    lookup_field = "slug"
    search_fields = ["name", "short_description"]

    @action(detail=True, methods=["post"], permission_classes=[NotReadOnlyAuditor])
    def submit(self, request, slug=None):
        item = self.get_object()
        serializer = CatalogSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        help_request = submit_catalog_item(
            item, requester=request.user, answers=serializer.validated_data["request_payload"], request=request,
        )
        return Response(HelpRequestsReadSerializer(help_request).data, status=status.HTTP_201_CREATED)
