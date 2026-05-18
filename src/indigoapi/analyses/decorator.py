import asyncio
import inspect
from functools import wraps

from indigoapi.analyses.registry import register_analysis


def analysis(name: str | None = None):
    """Decorator to register a function as an analysis.
    Converts sync functions to async."""

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            async_fn = func
        else:

            @wraps(func)
            async def async_fn(*args, **kwargs):
                return await asyncio.to_thread(func, *args, **kwargs)

        name_to_register = name or func.__name__

        register_analysis(name_to_register, async_fn)
        return async_fn

    return decorator
