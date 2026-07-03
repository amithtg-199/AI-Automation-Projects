def __getattr__(name):
    if name == "RagasEvaluator":
        from .pipeline import RagasEvaluator
        return RagasEvaluator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["RagasEvaluator"]
