from django.core.management.base import BaseCommand

from catalog.models import CatalogItem

ITEMS = [
    {
        "slug": "new-starter",
        "name": "New starter setup",
        "short_description": "Accounts and equipment for a new employee.",
        "requires_approval": True,
        "form_schema": [
            {"key": "employee_name", "label": "Employee name", "type": "text", "required": True},
            {"key": "start_date", "label": "Start date", "type": "date", "required": True},
            {"key": "needs_laptop", "label": "Laptop required", "type": "boolean", "required": False},
            {"key": "laptop_type", "label": "Laptop type", "type": "select", "options": ["Standard", "Developer"],
             "required": True, "show_when": {"field": "needs_laptop", "equals": True}},
        ],
    },
    {
        "slug": "software-install",
        "name": "Software installation",
        "short_description": "Request an approved application.",
        "form_schema": [
            {"key": "application", "label": "Application", "type": "text", "required": True},
            {"key": "business_reason", "label": "Business reason", "type": "textarea", "required": True},
        ],
    },
    {
        "slug": "shared-mailbox",
        "name": "Shared mailbox access",
        "short_description": "Get access to an existing shared mailbox.",
        "form_schema": [
            {"key": "mailbox", "label": "Mailbox address", "type": "text", "required": True},
            {"key": "access", "label": "Access level", "type": "select", "options": ["Read", "Send as"], "required": True},
        ],
    },
]


class Command(BaseCommand):
    help = "Create example catalog items (safe to run more than once)."

    def handle(self, *args, **kwargs):
        for data in ITEMS:
            _, created = CatalogItem.objects.get_or_create(slug=data["slug"], defaults=data)
            self.stdout.write(f"{'created' if created else 'exists '} {data['slug']}")
