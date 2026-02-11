from __future__ import annotations

import pytest
from omegaconf import OmegaConf

from hydr8._store import get, init, override
import hydr8._store as _store_mod


@pytest.fixture(autouse=True)
def _reset_cfg():
    """Reset the global config before each test."""
    _store_mod._CFG = None
    yield
    _store_mod._CFG = None


def test_init_and_get():
    cfg = OmegaConf.create({"db": {"host": "localhost"}})
    init(cfg)
    assert get() is cfg


def test_get_before_init_raises():
    with pytest.raises(RuntimeError, match="not initialized"):
        get()


def test_override_restores():
    cfg = OmegaConf.create({"db": {"host": "localhost"}})
    init(cfg)

    with override({"db": {"host": "override-host"}}) as tmp:
        assert get()["db"]["host"] == "override-host"
        assert tmp["db"]["host"] == "override-host"

    assert get()["db"]["host"] == "localhost"


def test_override_nested():
    cfg = OmegaConf.create({"a": 1})
    init(cfg)

    with override({"b": 2}):
        assert get()["b"] == 2
        with override({"c": 3}):
            assert get()["c"] == 3
        assert get()["b"] == 2

    assert get()["a"] == 1
