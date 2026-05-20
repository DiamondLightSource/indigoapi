from indigoapi.analyses.loader import get_async_function
from indigoapi.analyses.registry import register_analysis


def analysis(name: str | None = None):
    """Decorator to register a function as an analysis.
    Converts sync functions to async."""

    def decorator(func):
        async_fn = get_async_function(func)
        name_to_register = name or func.__name__

        register_analysis(name_to_register, async_fn)
        return async_fn

    return decorator
