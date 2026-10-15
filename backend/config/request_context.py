from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(value):
    _request_id.set(value)


def get_request_id():
    return _request_id.get()
