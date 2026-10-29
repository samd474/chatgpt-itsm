from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, has_role, is_staff_user

from .models import Article


def visible_articles(user, qs):
    """Staff and auditors see every article, drafts included; everyone else only published public ones."""
    if is_staff_user(user) or has_role(user, AUDITOR):
        return qs
    return qs.filter(status=Article.Status.PUBLISHED, visibility=Article.Visibility.PUBLIC)


def can_publish(user):
    """Publishing, retiring and editing beyond drafts is a knowledge-manager decision."""
    return has_role(user, MANAGER, ADMINISTRATOR)
