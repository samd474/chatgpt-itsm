from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from reports.audit import write_audit_event


class AuditedModelViewSet(viewsets.ModelViewSet):
    """CRUD where every create/update/delete appends an AuditEvent with before/after data."""

    audit_prefix = ""

    def _snapshot(self, instance):
        return self.get_serializer(instance).data

    def perform_create(self, serializer):
        instance = serializer.save()
        write_audit_event(self.request, f"{self.audit_prefix}.created", obj=instance, before={}, after=self._snapshot(instance))

    def perform_update(self, serializer):
        before = self._snapshot(serializer.instance)
        instance = serializer.save()
        write_audit_event(self.request, f"{self.audit_prefix}.updated", obj=instance, before=before, after=self._snapshot(instance))

    def perform_destroy(self, instance):
        before = self._snapshot(instance)
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "This record is in use. Deactivate it instead of deleting it."})
        write_audit_event(self.request, f"{self.audit_prefix}.deleted", object_type=instance._meta.label_lower,
                          object_id=str(before.get("id", "")), before=before, after={})
