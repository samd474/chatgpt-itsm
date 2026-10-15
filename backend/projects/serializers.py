from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.customfields import clean_custom_fields

from .models import Milestone, Project, ProjectMember, ProjectTask

User = get_user_model()


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ["user", "name", "role"]

    def get_name(self, obj):
        return _name(obj.user)


class ProjectSerializer(serializers.ModelSerializer):
    manager = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    manager_name = serializers.SerializerMethodField()
    members = ProjectMemberSerializer(source="memberships", many=True, required=False)
    progress = serializers.SerializerMethodField()
    custom_fields = serializers.DictField(required=False)

    class Meta:
        model = Project
        fields = ["id", "key", "name", "description", "status", "manager", "manager_name", "members", "start_date",
                  "target_date", "completed_at", "budget", "custom_fields", "progress", "created_at", "updated_at"]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]

    def get_manager_name(self, obj):
        return _name(obj.manager)

    def get_progress(self, obj):
        tasks = list(obj.tasks.values_list("status", flat=True))
        done = sum(1 for s in tasks if s == ProjectTask.Status.DONE)
        return {"total": len(tasks), "done": done, "percent": round(100 * done / len(tasks)) if tasks else 0}

    def validate_key(self, value):
        value = value.upper()
        if self.instance is not None and value != self.instance.key:
            raise serializers.ValidationError("A project key can't change once tasks are numbered with it.")
        return value

    def validate_custom_fields(self, value):
        return clean_custom_fields("project", value, existing=self.instance.custom_fields if self.instance else None)

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        target = attrs.get("target_date", getattr(self.instance, "target_date", None))
        if start and target and target < start:
            raise serializers.ValidationError({"target_date": "The target date can't be before the start date."})
        members = attrs.get("memberships")
        if members is not None and len({m["user"].pk for m in members}) != len(members):
            raise serializers.ValidationError({"members": "Each person can only be listed once."})
        return attrs

    def _save_members(self, project, members):
        if members is None:
            return
        project.memberships.all().delete()
        ProjectMember.objects.bulk_create([ProjectMember(project=project, user=m["user"], role=m["role"]) for m in members])

    def create(self, validated_data):
        members = validated_data.pop("memberships", None)
        project = Project.objects.create(**validated_data)
        self._save_members(project, members)
        return project

    def update(self, instance, validated_data):
        members = validated_data.pop("memberships", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._save_members(instance, members)
        return instance


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ["id", "project", "name", "due_date", "completed"]


class ProjectTaskSerializer(serializers.ModelSerializer):
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    assignee_name = serializers.SerializerMethodField()
    depends_on = serializers.PrimaryKeyRelatedField(queryset=ProjectTask.objects.all(), many=True, required=False)

    class Meta:
        model = ProjectTask
        fields = ["id", "project", "number", "title", "description", "status", "priority", "assignee", "assignee_name",
                  "milestone", "depends_on", "due_date", "estimate_hours", "position", "created_at", "completed_at"]
        read_only_fields = ["id", "number", "created_at", "completed_at"]

    def get_assignee_name(self, obj):
        return _name(obj.assignee)

    def validate_priority(self, value):
        if value not in (1, 2, 3, 4):
            raise serializers.ValidationError("Priority must be 1-4.")
        return value

    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        if self.instance is not None and "project" in attrs and attrs["project"] != self.instance.project:
            raise serializers.ValidationError({"project": "Tasks can't move between projects."})
        milestone = attrs.get("milestone")
        if milestone is not None and milestone.project_id != project.pk:
            raise serializers.ValidationError({"milestone": "That milestone belongs to another project."})
        assignee = attrs.get("assignee")
        if assignee is not None and assignee.pk != project.manager_id and not project.memberships.filter(user=assignee).exists():
            raise serializers.ValidationError({"assignee": "Assign tasks to project members only."})
        deps = attrs.get("depends_on")
        if deps:
            if any(d.project_id != project.pk for d in deps):
                raise serializers.ValidationError({"depends_on": "Dependencies must be in the same project."})
            if self.instance is not None and _creates_cycle(self.instance, deps):
                raise serializers.ValidationError({"depends_on": "That dependency would create a cycle."})
        return attrs


def _creates_cycle(task, deps):
    """Walk the dependency graph from the proposed dependencies looking for `task`."""
    seen, stack = set(), list(deps)
    while stack:
        current = stack.pop()
        if current.pk == task.pk:
            return True
        if current.pk in seen:
            continue
        seen.add(current.pk)
        stack.extend(current.depends_on.all())
    return False
