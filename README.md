# Release version

[![Test](https://github.com/actris-cloudnet/release-version/actions/workflows/test.yml/badge.svg)](https://github.com/actris-cloudnet/release-version/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/release-version.svg)](https://badge.fury.io/py/release-version)

Yet another tool for bumping version number and updating changelog.

## Usage

Install by running:

```sh
pip install release-version
```

Add following in `pyproject.toml` file in the root directory of your project:

```toml
[tool.release-version]
filename = "pyproject.toml"
pattern = "version = \"(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)\""
changelog = "CHANGELOG.md" # optional
```

Release new versions by running:

```sh
release-version patch
release-version minor
release-version major
```

## License

MIT
