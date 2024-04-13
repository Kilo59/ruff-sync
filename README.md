[![codecov](https://codecov.io/gh/Kilo59/ruff-sync/graph/badge.svg?token=kMZw0XtoFW)](https://codecov.io/gh/Kilo59/ruff-sync)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Kilo59/ruff-sync/main.svg)](https://results.pre-commit.ci/latest/github/Kilo59/ruff-sync/main)
[![Wily](https://img.shields.io/badge/%F0%9F%A6%8A%20wily-passing-brightgreen.svg)](https://wily.readthedocs.io/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

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
Or with [`pipx`](https://pipx.pypa.io/stable/) (recommended)
```console
pipx install git+https://github.com/Kilo59/ruff-sync
```

```console
$ ruff-sync --help
usage: ruff-sync [-h] [--source SOURCE] [--exclude EXCLUDE [EXCLUDE ...]] upstream

positional arguments:
  upstream              The URL to download the pyproject.toml file from.

optional arguments:
  -h, --help            show this help message and exit
  --source SOURCE       The directory to sync the pyproject.toml file to. Default: .
  --exclude EXCLUDE [EXCLUDE ...]
                        Exclude certain ruff configs. Default: per-file-ignores
```
