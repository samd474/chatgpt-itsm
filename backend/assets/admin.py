from django.contrib import admin

from .models import Asset, AssetRelationship, AssetType, Location


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "active")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "asset_type", "status", "assigned_to", "location", "warranty_expires")
    list_filter = ("status", "asset_type", "location")
    search_fields = ("asset_tag", "name", "serial_number")


@admin.register(AssetRelationship)
class AssetRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source", "kind", "target")
