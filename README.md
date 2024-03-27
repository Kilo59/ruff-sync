[![codecov](https://codecov.io/gh/Kilo59/ruff-sync/graph/badge.svg?token=kMZw0XtoFW)](https://codecov.io/gh/Kilo59/ruff-sync)

# ruff-sync

CLI tool for keeping multiple project in sync with a single ruff config.

## Quick start


<!-- ### PyPi Install

```console
pip install ruff-sync
``` -->

### VCS Install

```console
pip install git+https://github.com/Kilo59/ruff-sync
```

```console
$ ruff-sync --help
usage: ruff-sync [-h] [--source SOURCE] upstream

positional arguments:
  upstream         The URL to download the pyproject.toml file from.

options:
  -h, --help       show this help message and exit
  --source SOURCE  The directory to sync the pyproject.toml file to.
```
