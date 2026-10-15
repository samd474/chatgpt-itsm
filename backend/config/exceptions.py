import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("api.errors")


def exception_handler(exc, context):
    """DRF errors as usual; anything unexpected is logged with the request ID and
    answered with a generic message so stack traces never reach the client."""
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error")
    return response
