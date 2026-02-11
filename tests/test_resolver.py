from __future__ import annotations
import pytest
from omegaconf import OmegaConf

from hydr8._resolver import resolve, resolve_auto


# ---------- resolve() ----------


def test_resolve_nested():
    cfg = OmegaConf.create({"db": {"postgres": {"host": "localhost", "port": 5432}}})
    result = resolve(cfg, "db.postgres")
    assert result == {"host": "localhost", "port": 5432}


def test_resolve_single_level():
    cfg = OmegaConf.create({"server": {"port": 8080}})
    result = resolve(cfg, "server")
    assert result == {"port": 8080}


def test_resolve_missing_segment_raises():
    cfg = OmegaConf.create({"db": {"host": "localhost"}})
    with pytest.raises(KeyError, match="not found"):
        resolve(cfg, "db.missing")


def test_resolve_leaf_raises():
    cfg = OmegaConf.create({"db": {"host": "localhost"}})
    with pytest.raises(TypeError, match="leaf value"):
        resolve(cfg, "db.host")


# ---------- resolve_auto() ----------


def _make_fn(module: str, qualname: str):
    """Create a dummy function with the given __module__ and __qualname__."""
    def dummy():
        pass
    dummy.__module__ = module
    dummy.__qualname__ = qualname
    return dummy


def test_resolve_auto_function():
    cfg = OmegaConf.create({
        "data": {"loaders": {"build_loader": {"batch_size": 32}}},
    })
    fn = _make_fn("myproject.data.loaders", "build_loader")
    result = resolve_auto(cfg, fn)
    assert result == {"batch_size": 32}


def test_resolve_auto_method():
    cfg = OmegaConf.create({
        "db": {"client": {"Client": {"__init__": {"host": "localhost", "port": 5432}}}},
    })
    fn = _make_fn("myproject.db.client", "Client.__init__")
    result = resolve_auto(cfg, fn)
    assert result == {"host": "localhost", "port": 5432}


def test_resolve_list_index():
    cfg = OmegaConf.create({
        "db": {"foo": [{"host": "a"}, {"host": "b"}, {"host": "c", "port": 5432}]},
    })
    result = resolve(cfg, "db.foo[2]")
    assert result == {"host": "c", "port": 5432}


def test_resolve_auto_missing_raises():
    cfg = OmegaConf.create({"a": 1})
    fn = _make_fn("pkg.sub", "func")
    with pytest.raises(KeyError):
        resolve_auto(cfg, fn)
