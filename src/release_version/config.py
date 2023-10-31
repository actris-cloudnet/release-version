import re
from pathlib import Path

import tomli


class Config:
    changelog: Path | None = None

    def __init__(self, root: Path) -> None:
        with open("pyproject.toml", "rb") as file:
            config = tomli.load(file)["tool"]["release-version"]

        filenames = config["filename"]
        if isinstance(filenames, str):
            filenames = [filenames]
        self.filenames = [(root / filename).resolve() for filename in filenames]

        patterns = config["pattern"]
        if isinstance(patterns, str):
            patterns = [patterns]
        self.patterns = [re.compile(pattern) for pattern in patterns]

        if "changelog" in config:
            self.changelog = (root / config["changelog"]).resolve()
