from __future__ import annotations

from typing import Any, Callable

from omegaconf import DictConfig, OmegaConf


def resolve(cfg: DictConfig, path: str) -> dict[str, Any]:
    """Traverse *cfg* along the dot-separated *path* and return a plain dict.

    Raises ``KeyError`` if any segment is missing.
    """
    node = OmegaConf.select(cfg, path, throw_on_missing=True)
    if node is None:
        raise KeyError(f"Config path {path!r} not found")
    if not OmegaConf.is_dict(node):
        raise TypeError(
            f"Config path {path!r} resolved to a leaf value, not a mapping"
        )
    return OmegaConf.to_container(node, resolve=True)  # type: ignore[return-value]


def resolve_auto(
    cfg: DictConfig, fn: Callable[..., Any], scope: str = "module"
) -> dict[str, Any]:
    """Derive the config path from *fn*'s module (and optionally qualname), then resolve.

    If the first segment of ``__module__`` is not a top-level key in *cfg*,
    it is assumed to be the project/package name and is stripped.  This makes
    auto-resolve work regardless of whether the code was invoked with
    ``python -m`` (which includes the package prefix) or ``python file.py``
    (which does not).

    When *scope* is ``"module"`` (the default), only the module path is used::

        myproject.data.loaders -> data.loaders

    When *scope* is ``"fn"``, the function's ``__qualname__`` is appended::

        myproject.data.loaders + build_loader -> data.loaders.build_loader
    """
    parts = fn.__module__.split(".")

    # If the first segment isn't a top-level config key, it's the project
    # name — strip it.
    if len(parts) > 1 and parts[0] not in cfg:
        parts = parts[1:]

    if scope == "fn":
        path = ".".join(parts) + "." + fn.__qualname__
    else:
        path = ".".join(parts)

    return resolve(cfg, path)
