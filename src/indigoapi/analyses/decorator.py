import asyncio
import inspect
from functools import wraps

from indigoapi.analyses.registry import register_analysis


def analysis(name: str):
    """Decorator to register a function as an analysis.
    Converts sync functions to async."""

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            async_fn = func
        else:

            @wraps(func)
            async def async_fn(*args, **kwargs):
                return await asyncio.to_thread(func, *args, **kwargs)

        register_analysis(name, async_fn)
        return async_fn

    return decorator
