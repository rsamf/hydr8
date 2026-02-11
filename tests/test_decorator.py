from __future__ import annotations

import pytest
from omegaconf import OmegaConf

from hydr8._store import init
import hydr8._store as _store_mod
from hydr8._decorator import use


@pytest.fixture(autouse=True)
def _reset_cfg():
    _store_mod._CFG = None
    yield
    _store_mod._CFG = None


# ---------- basic injection ----------


def test_injects_kwargs():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect() == ("localhost", 5432)


def test_caller_overrides_injected():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect(host="remote") == ("remote", 5432)


def test_partial_override():
    init(OmegaConf.create({
        "db": {"host": "localhost", "port": 5432, "user": "admin"},
    }))

    @use("db")
    def connect(host: str, port: int, user: str):
        return host, port, user

    assert connect(host="remote") == ("remote", 5432, "admin")


def test_all_kwargs_supplied_skips_config():
    """When every required param is supplied, config is never accessed."""
    # Don't even initialize config — should not raise.

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect("localhost", 5432) == ("localhost", 5432)


# ---------- as_dict mode ----------


def test_as_dict_mode():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(config: dict):
        return config

    result = connect()
    assert result == {"host": "localhost", "port": 5432}


# ---------- auto ----------


def test_auto():
    # The test function lives in module "tests.test_decorator" with qualname
    # "test_auto.<locals>.process". After stripping top-level package
    # ("tests"), the path is "test_decorator.test_auto.<locals>.process".
    cfg = OmegaConf.create({
        "test_decorator": {
            "test_auto": {"<locals>": {"process": {"x": 42}}},
        },
    })
    init(cfg)

    @use()
    def process(x: int):
        return x

    assert process() == 42


# ---------- functools.wraps ----------


def test_preserves_metadata():
    init(OmegaConf.create({"db": {"host": "localhost"}}))

    @use("db")
    def connect(host: str):
        """Docstring."""
        return host

    assert connect.__name__ == "connect"
    assert connect.__doc__ == "Docstring."


# ---------- extra config keys silently ignored ----------


def test_extra_config_keys_ignored():
    init(OmegaConf.create({
        "db": {"host": "localhost", "port": 5432, "password": "secret"},
    }))

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect() == ("localhost", 5432)


# ---------- class method decoration ----------


def test_class_method():
    cfg = OmegaConf.create({
        "test_decorator": {
            "test_class_method": {
                "<locals>": {
                    "Client": {"__init__": {"host": "localhost", "port": 5432}},
                },
            },
        },
    })
    init(cfg)

    class Client:
        @use()
        def __init__(self, host: str, port: int):
            self.host = host
            self.port = port

    c = Client()
    assert c.host == "localhost"
    assert c.port == 5432


# ---------- function mode (dict-like access) ----------


def test_function_getitem():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))
    db = use("db")
    assert db["host"] == "localhost"
    assert db["port"] == 5432


def test_function_dict_conversion():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))
    db = use("db")
    assert dict(db) == {"host": "localhost", "port": 5432}


def test_function_contains():
    init(OmegaConf.create({"db": {"host": "localhost"}}))
    db = use("db")
    assert "host" in db
    assert "missing" not in db


def test_function_len():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))
    db = use("db")
    assert len(db) == 2


def test_function_items_keys_values():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))
    db = use("db")
    assert set(db.keys()) == {"host", "port"}
    assert set(db.values()) == {"localhost", 5432}
    assert set(db.items()) == {("host", "localhost"), ("port", 5432)}


def test_function_no_path_raises():
    init(OmegaConf.create({"a": 1}))
    proxy = use()
    with pytest.raises(TypeError, match="explicit path"):
        proxy["a"]


def test_function_lazy_resolution():
    """Config is resolved lazily, not at use() call time."""
    db = use("db")
    # Config not initialized yet — no error until access
    init(OmegaConf.create({"db": {"host": "localhost"}}))
    assert db["host"] == "localhost"
