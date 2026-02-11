from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Iterator, TypeVar

from ._store import get
from ._resolver import resolve, resolve_auto

F = TypeVar("F", bound=Callable[..., Any])


class _ConfigProxy:
    """Returned by ``use()``. Acts as both a decorator and a lazy config dict."""

    def __init__(self, path: str | None, as_dict: str | None, scope: str) -> None:
        self._path = path
        self._as_dict = as_dict
        self._scope = scope
        self._resolved: dict[str, Any] | None = None

    def _resolve(self) -> dict[str, Any]:
        if self._resolved is None:
            cfg = get()
            if self._path is None:
                raise TypeError(
                    "Cannot resolve config as a function without an explicit path. "
                    "Pass a path to use(), e.g. use('db')."
                )
            self._resolved = resolve(cfg, self._path)
        return self._resolved

    # -- decorator mode --

    def __call__(self, fn: F) -> F:
        path = self._path
        as_dict = self._as_dict
        scope = self._scope
        sig = inspect.signature(fn)
        param_names = set(sig.parameters)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = sig.bind_partial(*args, **kwargs)
            supplied = set(bound.arguments)

            required = {
                name
                for name, p in sig.parameters.items()
                if p.default is inspect.Parameter.empty
                and p.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            }
            if required <= supplied:
                return fn(*args, **kwargs)

            cfg = get()
            if path is None:
                resolved = resolve_auto(cfg, fn, scope)
            else:
                resolved = resolve(cfg, path)

            if as_dict is not None:
                if as_dict not in supplied:
                    kwargs[as_dict] = resolved
            else:
                for key, value in resolved.items():
                    if key in param_names and key not in supplied:
                        kwargs[key] = value

            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    # -- dict-like mode --

    def __getitem__(self, key: str) -> Any:
        return self._resolve()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._resolve()

    def __iter__(self) -> Iterator[str]:
        return iter(self._resolve())

    def __len__(self) -> int:
        return len(self._resolve())

    def keys(self) -> Any:
        return self._resolve().keys()

    def values(self) -> Any:
        return self._resolve().values()

    def items(self) -> Any:
        return self._resolve().items()

    def __repr__(self) -> str:
        try:
            return repr(self._resolve())
        except Exception:
            return f"_ConfigProxy(path={self._path!r})"


def use(
    path: str | None = None,
    *,
    as_dict: str | None = None,
    scope: str = "module",
) -> _ConfigProxy:
    """Access a config sub-tree — as a decorator or a function.

    Returns a proxy that can be used in two ways:

    **As a decorator** — injects config values into function parameters::

        @use("db")
        def connect(host: str, port: int):
            ...

        connect()              # host and port injected from cfg.db
        connect(host="other")  # caller args take precedence

    When ``path`` is ``None`` (the default), the config path is derived
    automatically from the function's module path.  If the first segment
    of ``__module__`` isn't a top-level config key it is treated as the
    project name and stripped, so auto-resolve works whether you run with
    ``python -m`` or ``python file.py``::

        # In myproject/data/loaders.py
        @use()
        def build_loader(batch_size: int, shuffle: bool):
            ...
        # resolves to cfg.data.loaders (scope="module", the default)

    With ``scope="fn"``, the function's ``__qualname__`` is appended::

        @use(scope="fn")
        def build_loader(batch_size: int, shuffle: bool):
            ...
        # resolves to cfg.data.loaders.build_loader

    With ``as_dict``, the entire sub-config is passed as a single kwarg
    instead of matching individual keys to parameters::

        @use("db", as_dict="config")
        def connect(config: dict):
            host = config["host"]

    **As a function** — returns a lazy, dict-like view of the config node.
    Requires an explicit ``path``::

        db = use("db")
        db["host"]        # "localhost"
        dict(db)          # {"host": "localhost", "port": 5432}
        "host" in db      # True

    The config is resolved lazily on first access, so ``use("db")`` can be
    called before ``init()``.

    Calling ``use()`` without a path and accessing it as a function raises
    ``TypeError``, since there is no function to derive the path from.

    Args:
        path: Dot-separated config path (e.g. ``"db.postgres"``). When
            ``None``, the path is derived from the decorated function's
            module (decorator mode only).
        as_dict: When set, the resolved sub-config is passed as a single
            kwarg with this name (decorator mode only).
        scope: Controls auto-resolve granularity (decorator mode only).
            ``"module"`` (default) resolves to the module's config node.
            ``"fn"`` appends the function's qualname.
    """
    return _ConfigProxy(path, as_dict, scope)
