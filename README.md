# hydr8

Decorator-based config injection for [Hydra](https://hydra.cc/).

hydr8 lets you push Hydra config values into function parameters automatically, so your functions stay clean and testable without manually threading `cfg` everywhere.

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

### Explicit path with kwargs injection

Config keys are matched to function parameter names. Extra config keys that don't match any parameter are silently ignored.

```python
@hydr8.use("db.postgres")
def connect(host: str, port: int, user: str):
    ...
```

### Explicit path with `as_dict`

Pass the entire resolved sub-config as a single dict argument:

```python
@hydr8.use("db.postgres", as_dict="config")
def connect(config: dict):
    host = config["host"]
    ...
```

### Automatic path resolution

Derive the config path from the function's module and qualname. The top-level package is stripped:

```python
# In myproject/data/loaders.py
@hydr8.use()
def build_loader(batch_size: int, shuffle: bool):
    ...
# Resolves to cfg.data.loaders.build_loader
```

`path=None` is the default, so `@hydr8.use()` auto-resolves from the function's module and qualname.

### Caller overrides

Caller-provided arguments always take precedence over injected config:

```python
@hydr8.use("db")
def connect(host: str, port: int):
    ...

connect(host="remote")  # port from config, host = "remote"
```

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
| `init(cfg)` | Store the Hydra DictConfig globally |
| `get()` | Retrieve the stored config (raises `RuntimeError` if uninitialized) |
| `override(overrides)` | Context manager that temporarily replaces the config |
| `use(path, *, as_dict)` | Decorator that injects config values into function kwargs |
