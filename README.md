# hydr8

Decorator-based config injection for [Hydra](https://hydra.cc/).

hydr8 lets you push Hydra config (or any config as long as it's a dict) values into function parameters automatically, so your functions stay clean and testable without manually threading `cfg` everywhere.

## Installation

```bash
pip install hydr8
# or
uv add hydr8
```

## Quick start

```python
import hydra
from omegaconf import DictConfig
import hydr8

@hydr8.use("db")
def connect(host: str, port: int):
    print(f"Connecting to {host}:{port}")

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig):
    hydr8.init(cfg)
    connect()  # host and port injected from cfg.db

if __name__ == "__main__":
    main()
```

With a config like:

```yaml
db:
  host: localhost
  port: 5432
```

## Usage

`hydr8.use()` is the core function. It can be used as a **decorator** to inject config into function parameters, or called **directly** to access a config sub-tree as a dict.

### As a decorator

#### Explicit path

Pass a dot-separated path to resolve a specific config node. Config keys are matched to function parameter names. Extra config keys that don't match any named parameter are silently ignored (unless the function accepts `**kwargs` — see below).

```python
@hydr8.use("db.postgres")
def connect(host: str, port: int, user: str):
    ...

connect()              # all three injected from cfg.db.postgres
connect(host="remote") # host overridden, port and user from config
```

List indexing is supported:

```python
@hydr8.use("db.replicas[0]")
def connect(host: str, port: int):
    ...
```

#### Implicit path (auto-resolve)

When no path is given, hydr8 derives it from the function's `__module__`. If the first segment of the module isn't a top-level config key, it's treated as the project name and stripped — so auto-resolve works whether you run with `python -m` or `python file.py`:

```python
# In myproject/data/loaders.py
@hydr8.use()
def build_loader(batch_size: int, shuffle: bool):
    ...
# Resolves to cfg.data.loaders
```

```yaml
# config.yaml
data:
  loaders:
    batch_size: 32
    shuffle: true
```

By default, `scope="module"` — the path resolves to the module's config node, and config keys are matched to function parameters. Multiple functions in the same module share the same config node.

With `scope="fn"`, the function's qualname is appended to the path:

```python
# In myproject/data/loaders.py
@hydr8.use(scope="fn")
def build_loader(batch_size: int, shuffle: bool):
    ...
# Resolves to cfg.data.loaders.build_loader
```

```yaml
# config.yaml
data:
  loaders:
    build_loader:
      batch_size: 32
      shuffle: true
```

This works with methods too:

```python
# In myproject/db/client.py
class Client:
    @hydr8.use(scope="fn")
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
# Resolves to cfg.db.client.Client.__init__
```

#### `as_dict` mode

Pass the entire resolved sub-config as a single dict argument instead of matching individual keys:

```python
@hydr8.use("db.postgres", as_dict="config")
def connect(config: dict):
    host = config["host"]
    port = config["port"]
    ...
```

#### `**kwargs` passthrough

When the decorated function accepts `**kwargs`, config keys that don't match any named parameter automatically flow into `**kwargs`:

```python
@hydr8.use("db")
def connect(host: str, **kwargs):
    # host matched by name; port and any other config keys land in kwargs
    print(host, kwargs)

connect()  # host="localhost", kwargs={"port": 5432}
```

#### Caller overrides

Caller-provided arguments always take precedence over injected config. If every required parameter is supplied by the caller, config is never accessed at all:

```python
@hydr8.use("db")
def connect(host: str, port: int):
    ...

connect(host="remote")       # port from config, host = "remote"
connect("localhost", 5432)   # config not accessed
```

### As a direct call

`hydr8.use("path")` returns a lazy, dict-like proxy. The config is resolved on first access, not at call time, so you can call `use()` before `init()`.

```python
import hydr8

db = hydr8.use("db")

hydr8.init(cfg)
db["host"]        # "localhost"
db["port"]        # 5432
```

This is useful when you want to read config values without decorating a function:

```python
def connect():
    db = hydr8.use("db")
    engine = create_engine(f"postgresql://{db['host']}:{db['port']}")
    ...
```

An explicit path is required when using `use()` as a direct call. Calling `use()` without a path and accessing it raises `TypeError`, since there is no function to derive the path from.

## Testing

### Option A: Supply all arguments directly

When every required parameter is provided by the caller, config injection is skipped entirely — no `init` needed:

```python
def test_connect():
    assert connect("localhost", 5432) == expected
```

### Option B: `override` context manager

Temporarily replace the global config for a test:

```python
from hydr8 import override

def test_connect():
    with override({"db": {"host": "test-host", "port": 9999}}):
        result = connect()
        assert result == expected
```

## API reference

| Function | Description |
|---|---|
| `init(cfg)` | Store the config globally (accepts any dict or OmegaConf DictConfig) |
| `get()` | Retrieve the stored config (raises `RuntimeError` if uninitialized) |
| `override(overrides)` | Context manager that temporarily replaces the config |
| `use(path, *, as_dict, scope)` | Decorator or direct config accessor for a config sub-tree |
