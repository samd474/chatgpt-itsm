from django.contrib import admin

from .models import Contract, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "email", "phone", "active")
    search_fields = ("name",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "vendor", "contract_type", "status", "start_date", "end_date", "auto_renew")
    list_filter = ("status", "contract_type", "vendor")
    search_fields = ("number", "name")
    filter_horizontal = ("assets", "services")
