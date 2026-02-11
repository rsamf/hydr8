from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from omegaconf import DictConfig, OmegaConf

_CFG: DictConfig | None = None


def init(cfg: DictConfig) -> None:
    """Store the Hydra config globally."""
    global _CFG
    _CFG = cfg


def get() -> DictConfig:
    """Retrieve the stored config. Raises RuntimeError if uninitialized."""
    if _CFG is None:
        raise RuntimeError(
            "hydr8 config not initialized. Call init(cfg) first."
        )
    return _CFG


@contextmanager
def override(overrides: dict[str, Any]) -> Iterator[DictConfig]:
    """Temporarily replace the global config with *overrides* merged in.

    Restores the previous config on exit.
    """
    global _CFG
    previous = _CFG
    _CFG = OmegaConf.create(overrides)
    try:
        yield _CFG
    finally:
        _CFG = previous
