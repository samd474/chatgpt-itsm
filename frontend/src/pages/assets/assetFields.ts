import type { FieldDef } from "../../components/form";

export const ASSET_STATUSES = [
  { value: "in_stock", label: "In stock" }, { value: "in_use", label: "In use" }, { value: "in_repair", label: "In repair" },
  { value: "retired", label: "Retired" }, { value: "disposed", label: "Disposed" }, { value: "lost", label: "Lost/stolen" },
];

export const ASSET_FIELDS: FieldDef[] = [
  { name: "name", label: "Name", required: true },
  { name: "asset_tag", label: "Asset tag", hint: "Leave blank to generate one" },
  { name: "asset_type", label: "Type", type: "select", lookup: "assetTypes", required: true },
  { name: "status", label: "Status", type: "select", options: ASSET_STATUSES, required: true },
  { name: "manufacturer", label: "Manufacturer" },
  { name: "model", label: "Model" },
  { name: "serial_number", label: "Serial number" },
  { name: "location", label: "Location", type: "select", lookup: "locations" },
  { name: "assigned_to", label: "Assigned to", type: "select", lookup: "people", hint: "They'll see it under My equipment" },
  { name: "owner", label: "Owner", type: "select", lookup: "people" },
  { name: "support_group", label: "Support group", type: "select", lookup: "groups" },
  { name: "purchase_date", label: "Purchase date", type: "date" },
  { name: "purchase_cost", label: "Purchase cost", type: "number" },
  { name: "warranty_expires", label: "Warranty expires", type: "date" },
  { name: "notes", label: "Notes", type: "textarea" },
];
