"""User and role administration for the React admin console.

Escalation guards (enforced here, not in the UI):
- Only superusers can see/edit superuser accounts or grant superuser/staff flags.
- Administrators can assign roles but cannot change their own roles or disable themselves,
  so nobody can lock out or quietly re-privilege their own account.
- Role assignment is limited to the known role groups plus admin-created custom groups;
  Django model permissions are never assignable through this API.
"""
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdministrator
from core.viewsets import AuditedModelViewSet
from helprequests.models import SupportGroups
from reports.audit import write_audit_event

from .models import User
from .roles import ADMINISTRATOR, AUDITOR, MANAGER, REQUESTER, TECHNICIAN

BUILT_IN_ROLES = (REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR, "CAB")


class UserAdminSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(source="groups", slug_field="name", many=True, queryset=Group.objects.all(), required=False)
    support_groups = serializers.PrimaryKeyRelatedField(many=True, queryset=SupportGroups.objects.all(), required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=128)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "department", "location", "title",
                  "is_enabled", "is_superuser", "last_login", "date_joined", "roles", "support_groups", "password"]
        read_only_fields = ["id", "is_superuser", "last_login", "date_joined"]

    def validate(self, attrs):
        request = self.context["request"]
        actor = request.user
        target = self.instance
        if target is not None and target.pk == actor.pk:
            if "groups" in attrs and set(g.name for g in attrs["groups"]) != set(target.groups.values_list("name", flat=True)):
                raise serializers.ValidationError({"roles": "You cannot change your own roles."})
            if attrs.get("is_enabled") is False:
                raise serializers.ValidationError({"is_enabled": "You cannot disable your own account."})
        if (target is not None and target.pk != actor.pk and attrs.get("password") and not actor.is_superuser
                and target.groups.filter(name=ADMINISTRATOR).exists()):
            raise serializers.ValidationError({"password": "Only a superuser can reset another administrator's password."})
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Set an initial password."})
        if attrs.get("password"):
            try:
                validate_password(attrs["password"], user=target)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        groups = validated_data.pop("groups", [])
        support_groups = validated_data.pop("support_groups", [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.groups.set(groups)
        user.support_groups.set(support_groups)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        groups = validated_data.pop("groups", None)
        support_groups = validated_data.pop("support_groups", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
            instance.__dict__.pop("_role_names_cache", None)
        if support_groups is not None:
            instance.support_groups.set(support_groups)
        return instance


class UserAdminViewSet(AuditedModelViewSet):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdministrator]
    http_method_names = ["get", "post", "patch", "head", "options"]  # disable instead of delete
    audit_prefix = "admin.user"
    search_fields = ["username", "email", "first_name", "last_name", "department"]
    filterset_fields = ["is_enabled", "groups__name", "support_groups"]
    ordering_fields = ["username", "last_login", "date_joined"]

    def get_queryset(self):
        qs = User.objects.prefetch_related("groups", "support_groups").order_by("username")
        if not getattr(self.request.user, "is_superuser", False):
            qs = qs.filter(is_superuser=False)
        return qs

    def _snapshot(self, instance):
        data = dict(self.get_serializer(instance).data)
        data.pop("password", None)
        return data

    @action(detail=True, methods=["post"])
    def end_sessions(self, request, pk=None):
        """Sign the user out everywhere (e.g. after a suspected compromise)."""
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        user = self.get_object()
        ended = 0
        for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
            if session.get_decoded().get("_auth_user_id") == str(user.pk):
                session.delete()
                ended += 1
        write_audit_event(request, "admin.user.sessions_ended", obj=user, metadata={"sessions": ended})
        return Response({"sessions_ended": ended}, status=status.HTTP_200_OK)


class RoleSerializer(serializers.ModelSerializer):
    built_in = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(source="user_set.count", read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "built_in", "member_count"]

    def get_built_in(self, obj):
        return obj.name in BUILT_IN_ROLES


class RoleViewSet(AuditedModelViewSet):
    """Roles are Django auth groups. Built-in roles can't be renamed or deleted."""

    serializer_class = RoleSerializer
    permission_classes = [IsAdministrator]
    pagination_class = None
    audit_prefix = "admin.role"
    queryset = Group.objects.order_by("name")

    def perform_update(self, serializer):
        if serializer.instance.name in BUILT_IN_ROLES:
            raise serializers.ValidationError({"name": "Built-in roles cannot be renamed."})
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.name in BUILT_IN_ROLES:
            raise serializers.ValidationError({"detail": "Built-in roles cannot be deleted."})
        super().perform_destroy(instance)
