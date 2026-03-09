import importlib
from collections.abc import Callable

ANALYSIS_REGISTRY = {}


def register_analysis(name: str, fn: Callable) -> None:
    if name in ANALYSIS_REGISTRY:
        raise ValueError(f"Analysis '{name}' already registered")
    ANALYSIS_REGISTRY[name] = fn


def get_analysis(name: str) -> Callable:
    if name not in ANALYSIS_REGISTRY:
        try:
            mod = importlib.import_module(f"indigoapi.analyses.{name}")
            func = getattr(mod, name)
            ANALYSIS_REGISTRY[name] = func
        except (ImportError, AttributeError) as e:
            print(f"Unknown analysis '{name}': {e}")
    return ANALYSIS_REGISTRY[name]


def list_analyses() -> list[str]:

    return list(ANALYSIS_REGISTRY.keys())
