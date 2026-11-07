"""OpenAPI annotations that work with or without drf-spectacular installed.

The schema (and the frontend types generated from it) is built in development and CI, where
drf-spectacular is installed. The production image doesn't ship it, so there these decorators
are no-ops and the views behave exactly the same.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the type checker runs with dev dependencies, so it sees the real signatures
    from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_field
else:
    try:
        from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_field
    except ImportError:  # production: schema tooling isn't installed
        class OpenApiParameter:
            def __init__(self, *args, **kwargs):
                pass

        def extend_schema(*args, **kwargs):
            return lambda target: target

        def extend_schema_field(*args, **kwargs):
            return lambda target: target

__all__ = ["OpenApiParameter", "extend_schema", "extend_schema_field"]
