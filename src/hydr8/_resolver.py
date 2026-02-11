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


def resolve_auto(cfg: DictConfig, fn: Callable[..., Any]) -> dict[str, Any]:
    """Derive the config path from *fn*'s module and qualname, then resolve.

    The first segment of ``__module__`` is stripped (the top-level package),
    and ``__qualname__`` is appended.  For example::

        myproject.data.loaders.build_loader
        -> data.loaders.build_loader
    """
    module = fn.__module__
    qualname = fn.__qualname__

    # Strip top-level package
    parts = module.split(".")
    if len(parts) > 1:
        module_tail = ".".join(parts[1:])
    else:
        module_tail = parts[0]

    path = f"{module_tail}.{qualname}"
    return resolve(cfg, path)
