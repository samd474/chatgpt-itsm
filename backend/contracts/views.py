from rest_framework.permissions import IsAuthenticated

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, TECHNICIAN, has_role
from core.numbering import assign_number
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from reports.audit import write_audit_event

from .models import Contract, Vendor
from .serializers import ContractSerializer, VendorSerializer

ContractAccess = role_permission(read_roles=(TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR), write_roles=(MANAGER, ADMINISTRATOR))


class VendorViewSet(AuditedModelViewSet):
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated, ContractAccess]
    queryset = Vendor.objects.all()
    audit_prefix = "vendor"
    search_fields = ["name", "contact_name", "email"]
    filterset_fields = ["active"]
    ordering_fields = ["name"]


class ContractViewSet(AuditedModelViewSet):
    """Technicians can read contracts (e.g. vendor support details) but never see financial terms."""

    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, ContractAccess]
    queryset = Contract.objects.select_related("vendor", "owner").prefetch_related("assets", "services")
    audit_prefix = "contract"
    search_fields = ["number", "name", "vendor__name"]
    filterset_fields = ["status", "contract_type", "vendor", "owner", "auto_renew", "assets"]
    ordering_fields = ["end_date", "start_date", "name", "number"]
    http_method_names = ["get", "post", "patch", "head", "options"]  # terminate instead of delete

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", self.get_serializer_context())
        kwargs["show_financials"] = has_role(self.request.user, MANAGER, ADMINISTRATOR, AUDITOR)
        return ContractSerializer(*args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        assign_number(instance, "CTR")
        write_audit_event(self.request, "contract.created", obj=instance, before={}, after=self._snapshot(instance))
