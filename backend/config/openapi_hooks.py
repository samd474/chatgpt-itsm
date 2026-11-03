"""Post-processing for the generated OpenAPI schema (dev/CI only; see SPECTACULAR_SETTINGS)."""

# Response fields a serializer leaves out for some viewers, so they stay optional in the schema.
SOMETIMES_OMITTED = {
    "Contract": {"value", "currency", "billing_frequency"},  # hidden from technicians
    "Article": {"helpful_count", "not_helpful_count"},  # hidden from requesters
}


def require_response_fields(result, generator, request, public):
    """Mark every response field required.

    drf-spectacular only marks fields required when they're read-only or required on input, so a
    writable field with a default (e.g. `status`) looks optional. DRF always serialises every field,
    and the frontend types rely on that. Request components (named "<X>Request" or "Patched<X>")
    are left alone.
    """
    schemas = result.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        is_request = name.startswith("Patched") or (name.endswith("Request") and name[: -len("Request")] in schemas)
        if is_request or schema.get("type") != "object" or "properties" not in schema:
            continue
        optional = SOMETIMES_OMITTED.get(name, set())
        schema["required"] = sorted(p for p in schema["properties"] if p not in optional)
    return result
