import argparse
import datetime
import sys
from pathlib import Path
from subprocess import CalledProcessError

from .config import Config
from .utils import (
    Repo,
    Version,
    confirm,
    congrats,
    open_editor,
    read_changelog,
    read_version,
    write_version,
)


def update_changelog(
    repo: Repo, path: Path, old_version: Version, new_version: Version
) -> None:
    changelog_prefix, changelog, changelog_suffix = read_changelog(path)
    content = (
        f"# Please enter the changelog entry for version {new_version}.\n"
        "# Lines starting with '#' will be ignored.\n"
    )
    if commits := repo.commits_since(old_version.tag):
        content += f"#\n# Commits since version {old_version}:\n#\n"
        for commit in commits:
            content += f"# - {commit}\n"
    if changelog:
        content += "\n" + changelog
    lines = open_editor(content).splitlines()
    while lines and lines[0].startswith("#"):
        lines.pop(0)
    entry = "\n".join(lines).strip()
    if not entry:
        print("ERROR: Changelog entry is empty!", file=sys.stderr)
        sys.exit(1)
    print("Changelog entry for new version:")
    print()
    print(entry)
    print()
    if not confirm("Use this changelog entry?"):
        return
    today = datetime.date.today().isoformat()
    new_changelog = (
        changelog_prefix
        + f"\n\n## {new_version} – {today}\n\n{entry}\n\n"
        + changelog_suffix
    )
    path.write_text(new_changelog)


def precommit(repo: Repo) -> None:
    try:
        repo.run_hook("pre-commit")
    except FileNotFoundError:
        pass
    except CalledProcessError as exc:
        updated_files = repo.changed_files(staged=False)
        if not updated_files or not updated_files.issubset(
            repo.changed_files(staged=True)
        ):
            repo.restore(".", staged=True, worktree=True)
            print("ERROR: Running pre-commit hook failed:", file=sys.stderr)
            print(exc.stdout, end="", file=sys.stderr)
            sys.exit(1)
        for file in updated_files:
            repo.add(file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump version number.")
    parser.add_argument(
        "component",
        choices=["major", "minor", "patch"],
        type=str,
        help="Version number component to update.",
    )
    args = parser.parse_args()

    repo = Repo()
    default_branch = "main"
    if repo.current_branch() != default_branch:
        print(f"FATAL: Not in '{default_branch}' branch!", file=sys.stderr)
        sys.exit(1)
    if repo.changed_files(staged=False) or repo.changed_files(staged=True):
        print("FATAL: Uncommitted changes detected!", file=sys.stderr)
        sys.exit(1)

    config = Config(repo.path)
    contents = [f.read_text() for f in config.filenames]
    old_version = read_version(contents[0], config.patterns)
    new_version = getattr(old_version, f"next_{args.component}")()

    if not confirm(f"Updating version {old_version} -> {new_version}. Continue?"):
        return

    for filename, old_content in zip(config.filenames, contents):
        new_content = write_version(old_content, config.patterns, new_version)
        filename.write_text(new_content)
        repo.add(filename)
    precommit(repo)

    if config.changelog:
        update_changelog(repo, config.changelog, old_version, new_version)
        repo.add(config.changelog)
        precommit(repo)

    repo.commit(f"Release version {new_version}")
    repo.tag(new_version.tag)
    repo.push("origin", default_branch, new_version.tag, atomic=True)

    print(f"Version {new_version} released! {congrats()}")
