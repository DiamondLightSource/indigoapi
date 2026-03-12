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
            async def async_fn(inputs):
                return await asyncio.to_thread(func, inputs)

        register_analysis(name, async_fn)
        return async_fn

    return decorator
