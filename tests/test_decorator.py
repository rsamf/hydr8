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


def test_auto_module_scope():
    # The test function lives in module "tests.test_decorator".
    # "tests" is not a top-level config key, so it gets stripped.
    # scope="module" (default) resolves to cfg.test_decorator.
    cfg = OmegaConf.create({
        "test_decorator": {"x": 42},
    })
    init(cfg)

    @use()
    def process(x: int):
        return x

    assert process() == 42


def test_auto_fn_scope():
    # scope="fn" appends qualname: test_decorator.test_auto_fn_scope.<locals>.process
    cfg = OmegaConf.create({
        "test_decorator": {
            "test_auto_fn_scope": {"<locals>": {"process": {"x": 42}}},
        },
    })
    init(cfg)

    @use(scope="fn")
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


def test_class_method_module_scope():
    # scope="module" (default) resolves to cfg.test_decorator.
    # Both host and port are at the module level.
    cfg = OmegaConf.create({
        "test_decorator": {"host": "localhost", "port": 5432},
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


def test_class_method_fn_scope():
    # scope="fn" resolves to cfg.test_decorator.test_class_method_fn_scope.<locals>.Client.__init__
    cfg = OmegaConf.create({
        "test_decorator": {
            "test_class_method_fn_scope": {
                "<locals>": {
                    "Client": {"__init__": {"host": "localhost", "port": 5432}},
                },
            },
        },
    })
    init(cfg)

    class Client:
        @use(scope="fn")
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


# ---------- keyword argument edge cases ----------


def test_single_kwarg_override():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect(port=9999) == ("localhost", 9999)


def test_positional_first_kwarg_second():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432, "timeout": 30}}))

    @use("db")
    def connect(host: str, port: int, timeout: int):
        return host, port, timeout

    assert connect("remote", timeout=60) == ("remote", 5432, 60)


def test_all_kwargs():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int):
        return host, port

    assert connect(host="remote", port=9999) == ("remote", 9999)


def test_as_dict_caller_kwarg_override():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(config: dict):
        return config

    assert connect(config={"custom": True}) == {"custom": True}


def test_as_dict_with_other_params_kwarg():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(name: str, config: dict):
        return name, config

    result = connect(name="mydb")
    assert result == ("mydb", {"host": "localhost", "port": 5432})


def test_as_dict_with_positional_and_kwarg():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(name: str, config: dict):
        return name, config

    result = connect("mydb", config={"custom": True})
    assert result == ("mydb", {"custom": True})


def test_method_kwarg_override():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    class Client:
        @use("db")
        def connect(self, host: str, port: int):
            return host, port

    c = Client()
    assert c.connect(host="remote") == ("remote", 5432)


def test_method_all_kwargs():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    class Client:
        @use("db")
        def connect(self, host: str, port: int):
            return host, port

    c = Client()
    assert c.connect(host="remote", port=9999) == ("remote", 9999)


def test_keyword_only_params():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(*, host: str, port: int):
        return host, port

    assert connect(host="remote") == ("remote", 5432)


def test_default_params_with_kwarg():
    """Config should still inject into params with defaults when not all params supplied."""
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int = 3306):
        return host, port

    # port has a default, but config value should override it
    assert connect(host="remote") == ("remote", 5432)


def test_default_params_positional_with_kwarg():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432, "timeout": 30}}))

    @use("db")
    def connect(host: str, port: int, timeout: int = 10):
        return host, port, timeout

    # timeout has default, but config should still inject it
    assert connect("remote", port=9999) == ("remote", 9999, 30)


def test_all_params_supplied_skips_config():
    """When every param (including optional) is supplied, skip config entirely."""
    @use("db")
    def connect(host: str, port: int = 3306):
        return host, port

    assert connect("localhost", 5432) == ("localhost", 5432)
    assert connect(host="localhost", port=5432) == ("localhost", 5432)


# ---------- **kwargs parameter ----------


def test_var_kwargs_no_injection():
    """Config keys flow into **kwargs when there are no named params."""
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(**kwargs):
        return kwargs

    assert connect() == {"host": "localhost", "port": 5432}


def test_var_kwargs_with_named_params():
    """Named params get injected; extra config keys flow into **kwargs."""
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, **kwargs):
        return host, kwargs

    assert connect() == ("localhost", {"port": 5432})
    assert connect(extra="val") == ("localhost", {"port": 5432, "extra": "val"})
    assert connect(host="remote") == ("remote", {"port": 5432})
    assert connect(host="remote", extra="val") == ("remote", {"port": 5432, "extra": "val"})


def test_var_kwargs_caller_kwarg_passed_through():
    """Caller kwargs that don't match named params pass through to **kwargs."""
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db")
    def connect(host: str, port: int, **kwargs):
        return host, port, kwargs

    assert connect(extra="val") == ("localhost", 5432, {"extra": "val"})
    assert connect(host="remote", extra="val") == ("remote", 5432, {"extra": "val"})


def test_as_dict_with_var_kwargs():
    """as_dict injects into **kwargs as a named kwarg when the param doesn't exist."""
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(**kwargs):
        return kwargs

    result = connect()
    assert result == {"config": {"host": "localhost", "port": 5432}}


def test_as_dict_with_named_and_var_kwargs():
    init(OmegaConf.create({"db": {"host": "localhost", "port": 5432}}))

    @use("db", as_dict="config")
    def connect(name: str, **kwargs):
        return name, kwargs

    assert connect("mydb") == ("mydb", {"config": {"host": "localhost", "port": 5432}})
    assert connect("mydb", config={"custom": True}) == ("mydb", {"config": {"custom": True}})
    assert connect("mydb", extra="val") == ("mydb", {"config": {"host": "localhost", "port": 5432}, "extra": "val"})
