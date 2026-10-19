from django.db.models import Q

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, has_role

from .models import ProjectMember


def visible_projects(user, qs):
    """Managers, administrators and auditors see every project; others only their own."""
    if has_role(user, MANAGER, ADMINISTRATOR, AUDITOR):
        return qs
    member_of = ProjectMember.objects.filter(user=user).values("project_id")
    return qs.filter(Q(manager=user) | Q(pk__in=member_of))


def can_manage(user, project):
    """Edit project details, members and milestones."""
    return project.manager_id == user.pk or has_role(user, ADMINISTRATOR)


def can_contribute(user, project):
    """Create and update tasks."""
    if can_manage(user, project):
        return True
    return ProjectMember.objects.filter(project=project, user=user, role=ProjectMember.Role.CONTRIBUTOR).exists()
