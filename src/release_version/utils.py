from __future__ import annotations  # No typing.Self in Python 3.10

import os
import random
import re
import subprocess
import sys
from pathlib import Path
from subprocess import STDOUT, CalledProcessError
from tempfile import NamedTemporaryFile
from typing import NamedTuple, Sequence

EDITOR = os.environ.get("EDITOR", "vi")
CHANGELOG_UNRELEASED = re.compile(r"^## Unreleased$", re.M)
CHANGELOG_SECTION = re.compile(r"^##[^#]", re.M)
INITIAL_CHANGELOG = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""


def sub_named_groups(
    pattern: re.Pattern[str], repl: dict[str, str], string: str
) -> str:
    def replfun(match: re.Match[str]) -> str:
        output = match.string[match.start(0) : match.start(1)] + values[0]
        for i in range(1, len(values)):
            output += match.string[match.end(i) : match.start(i + 1)] + values[i]
        return output + match.string[match.end(len(values)) : match.end(0)]

    values = [""] * pattern.groups
    for key, value in pattern.groupindex.items():
        values[value - 1] = repl[key]
    return re.sub(pattern, replfun, string)


class Version(NamedTuple):
    major: int
    minor: int
    patch: int

    def next_major(self) -> Version:
        return Version(self.major + 1, 0, 0)

    def next_minor(self) -> Version:
        return Version(self.major, self.minor + 1, 0)

    def next_patch(self) -> Version:
        return Version(self.major, self.minor, self.patch + 1)

    @property
    def tag(self) -> str:
        return f"v{self}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def read_version(contents: str, patterns: list[re.Pattern[str]]) -> Version:
    comps = {}
    for pattern in patterns:
        if match := re.search(pattern, contents):
            for key, value in match.groupdict().items():
                comps[key] = int(value)
    return Version(**comps)


def write_version(
    contents: str, patterns: list[re.Pattern[str]], version: Version
) -> str:
    repl = {key: str(value) for key, value in version._asdict().items()}
    for pattern in patterns:
        contents = sub_named_groups(pattern, repl, contents)
    return contents


def confirm(msg: str) -> bool:
    while True:
        match input(f"{msg} [y/n] ").lower():
            case "y":
                return True
            case "n":
                return False
        print("ERROR: Please answer either 'y' or 'n'.", file=sys.stderr)


class Repo:
    def __init__(self, path: Path | None = None):
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, cwd=path
        )
        self.path = Path(root.strip())

    def _git(self, args: Sequence[str | Path]) -> str:
        return subprocess.check_output(["git", *args], text=True, cwd=self.path)

    def add(self, path: str | Path) -> None:
        self._git(["add", path])

    def commit(self, message: str, allow_empty: bool = False) -> None:
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self._git(args)

    def tag(self, tag: str) -> None:
        self._git(["tag", tag])

    def commits_since(self, obj: str) -> list[str]:
        try:
            self._git(["rev-parse", "--quiet", "--verify", obj])
        except CalledProcessError:
            return []
        return self._git(
            ["log", "--pretty=format:%s", "--reverse", f"{obj}.."]
        ).splitlines()

    def push(self, repo: str, *refs: str, atomic: bool) -> None:
        args = ["push", repo]
        if atomic:
            args.append("--atomic")
        args.extend(refs)
        self._git(args)

    def current_branch(self) -> str:
        return self._git(["branch", "--show-current"]).strip()

    def changed_files(self, staged: bool) -> set[Path]:
        args = ["diff", "--name-only"]
        if staged:
            args.append("--staged")
        return set(
            (self.path / line).resolve() for line in self._git(args).splitlines()
        )

    def run_hook(self, name: str) -> None:
        script = self.path / ".git/hooks/" / name
        subprocess.check_output(script, text=True, stderr=STDOUT, cwd=self.path)

    def restore(
        self, file: Path | str, staged: bool = False, worktree: bool = False
    ) -> None:
        args: list[str | Path] = ["restore"]
        if staged:
            args.append("--staged")
        if worktree:
            args.append("--worktree")
        args.append("--")
        args.append(file)
        self._git(args)


def read_changelog(path: Path) -> tuple[str, str, str]:
    try:
        changelog = path.read_text()
    except FileNotFoundError:
        changelog = INITIAL_CHANGELOG
    start = CHANGELOG_UNRELEASED.search(changelog)
    if start is not None:
        start_index = start.start()
        middle_index = start.end()
        end = CHANGELOG_SECTION.search(changelog, start.end())
        end_index = end.start() if end is not None else None
    else:
        start = CHANGELOG_SECTION.search(changelog)
        start_index = middle_index = end_index = (
            start.start() if start is not None else len(changelog)
        )
    return (
        changelog[:start_index].rstrip(),
        changelog[middle_index:end_index].strip(),
        changelog[end_index:].lstrip(),
    )


def open_editor(content: str) -> str:
    with NamedTemporaryFile(suffix=".md", mode="w+", encoding="utf8") as temp:
        temp.write(content)
        temp.flush()
        subprocess.check_call([EDITOR, temp.name])
        temp.seek(0)
        return temp.read()


def congrats() -> str:
    adj = random.choice(
        [
            "Amazing",
            "Astounding",
            "Awe-inspiring",
            "Awesome",
            "Beautiful",
            "Breathtaking",
            "Brilliant",
            "Cracking",
            "Cunning",
            "Dazzling",
            "Enchanting",
            "Excellent",
            "Exceptional",
            "Exquisite",
            "Extraordinary",
            "Fabulous",
            "Fantastic",
            "Fine",
            "First-rate",
            "Great",
            "Groovy",
            "Impeccable",
            "Impressive",
            "Incredible",
            "Ingenious",
            "Inspiring",
            "Lovely",
            "Magnificent",
            "Marvelous",
            "Masterful",
            "Miraculous",
            "Neat",
            "Nice",
            "Outstanding",
            "Phenomenal",
            "Remarkable",
            "Sensational",
            "Significant",
            "Smashing",
            "Spectacular",
            "Splendid",
            "Stellar",
            "Striking",
            "Stunning",
            "Stupendous",
            "Substantial",
            "Superb",
            "Supreme",
            "Terrific",
            "Top-notch",
            "Tremendous",
            "Unbelievable",
            "Unreal",
            "Wicked",
            "Wonderful",
            "World-class",
        ]
    )
    noun = random.choice(
        [
            random.choice(
                [
                    "accomplishment",
                    "achievement",
                    "feat",
                ]
            ),
            "additions",
            "bugfixes" if random.random() < 0.9 else "bugs",
            "changes",
            "code",
            "commits",
            "effort",
            "features",
            "job",
            "patch",
            "release",
            "update",
            "version",
            "work",
        ]
    )
    return f"{adj} {noun}!"
