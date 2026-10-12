import sys
from typing import Callable

import adsk.core

from .general_utils import handle_error

# Fusion only calls handlers that stay referenced from Python.
_handlers = []


def add_handler(event: adsk.core.Event, callback: Callable, *,
                name: str = None, local_handlers: list = None):
    """Wrap a plain function as a handler for `event` and connect it.

    The handler class is found from the event's type: e.g. CommandCreatedEvent
    -> adsk.core.CommandCreatedEventHandler.
    """
    module = sys.modules[event.__module__]
    try:
        # same lookup as Fusion's own template: the type named in event.add()'s signature
        handler_type = module.__dict__[event.add.__annotations__['handler']]
    except Exception:
        handler_type = getattr(module, type(event).__name__ + 'Handler')
    handler = _create_handler(handler_type, callback, event, name, local_handlers)
    event.add(handler)
    return handler


def clear_handlers():
    """Drop all global handler references (call from stop())."""
    global _handlers
    _handlers = []


def _create_handler(handler_type, callback, event, name, local_handlers):
    handler = _define_handler(handler_type, callback, name)()
    (local_handlers if local_handlers is not None else _handlers).append(handler)
    return handler


def _define_handler(handler_type, callback, name):
    name = name or handler_type.__name__

    class Handler(handler_type):
        def __init__(self):
            super().__init__()

        def notify(self, args):
            try:
                callback(args)
            except:
                handle_error(name, show_message_box=True)

    return Handler
