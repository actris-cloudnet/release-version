# pylint: disable=line-too-long,subprocess-run-check

import datetime
import os
import subprocess
from pathlib import Path

import pytest

from release_version.utils import Repo


@pytest.fixture(name="repo")
def fixture_repo(tmp_path: Path) -> Repo:
    remote_path = tmp_path / "git_remote"
    remote_path.mkdir()
    subprocess.check_call(["git", "init", "--bare"], cwd=remote_path)

    local_path = tmp_path / "git_local"
    local_path.mkdir()
    subprocess.check_call(["git", "init"], cwd=local_path)
    subprocess.check_call(
        ["git", "remote", "add", "origin", remote_path], cwd=local_path
    )

    return Repo(local_path)


def _env(replace: dict[str, str]) -> dict[str, str]:
    return {**os.environ, **replace}


def test_patch(repo: Repo):
    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")
    stdout = subprocess.check_output(
        ["release-version", "patch"],
        input="y\n",
        text=True,
        cwd=repo.path,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] Version 0.1.1 released!"
    )
    assert 'version = "0.1.1"' in pyproject.read_text()


def test_changelog(repo: Repo, tmp_path: Path):
    today = datetime.date.today().isoformat()

    scripts_path = tmp_path / "scripts"
    scripts_path.mkdir()
    editor_path = scripts_path / "editor.py"
    editor_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        'Path(sys.argv[1]).write_text("- Initial release!")\n'
    )
    editor_path.chmod(0o755)

    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
        'changelog = "CHANGELOG.md"\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")

    changelog = repo.path / "CHANGELOG.md"

    stdout = subprocess.check_output(
        ["release-version", "patch"],
        input="y\ny\n",
        text=True,
        env=_env({"EDITOR": str(editor_path)}),
        cwd=repo.path,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] "
        "Changelog entry for new version:\n"
        "\n"
        "- Initial release!\n"
        "\n"
        "Use this changelog entry? [y/n] "
        "Version 0.1.1 released!"
    )
    assert 'version = "0.1.1"' in pyproject.read_text()
    assert f"## 0.1.1 – {today}\n\n- Initial release!\n" in changelog.read_text()


def test_append_changelog(repo: Repo, tmp_path: Path):
    today = datetime.date.today().isoformat()

    scripts_path = tmp_path / "scripts"
    scripts_path.mkdir()
    editor_path = scripts_path / "editor.py"
    editor_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        'Path(sys.argv[1]).write_text("- Brand-new release!")\n'
    )
    editor_path.chmod(0o755)

    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
        'changelog = "CHANGELOG.md"\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")

    changelog = repo.path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 0.1.0 – 2023-10-31\n\n- Initial release!\n")

    stdout = subprocess.check_output(
        ["release-version", "minor"],
        input="y\ny\n",
        text=True,
        env=_env({"EDITOR": str(editor_path)}),
        cwd=repo.path,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.2.0. Continue? [y/n] "
        "Changelog entry for new version:\n"
        "\n"
        "- Brand-new release!\n"
        "\n"
        "Use this changelog entry? [y/n] "
        "Version 0.2.0 released!"
    )
    assert 'version = "0.2.0"' in pyproject.read_text()
    assert changelog.read_text() == (
        "# Changelog\n"
        "\n"
        f"## 0.2.0 – {today}\n"
        "\n"
        "- Brand-new release!\n"
        "\n"
        "## 0.1.0 – 2023-10-31\n"
        "\n"
        "- Initial release!\n"
    )


def test_changelog_from_commits(repo: Repo, tmp_path: Path):
    today = datetime.date.today().isoformat()

    scripts_path = tmp_path / "scripts"
    scripts_path.mkdir()
    editor_path = scripts_path / "editor.py"
    editor_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "import re\n"
        "from pathlib import Path\n"
        "path = Path(sys.argv[1])\n"
        "path.write_text(re.sub(r'^# -', '-', path.read_text(), flags=re.M))\n"
    )
    editor_path.chmod(0o755)

    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
        'changelog = "CHANGELOG.md"\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")
    repo.tag("v0.1.0")
    repo.commit("Implement feature", allow_empty=True)
    repo.commit("Fix test", allow_empty=True)
    repo.commit("Fix linter", allow_empty=True)

    changelog = repo.path / "CHANGELOG.md"

    stdout = subprocess.check_output(
        ["release-version", "patch"],
        input="y\ny\n",
        text=True,
        env=_env({"EDITOR": str(editor_path)}),
        cwd=repo.path,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] "
        "Changelog entry for new version:\n"
        "\n"
        "- Implement feature\n"
        "- Fix test\n"
        "- Fix linter\n"
        "\n"
        "Use this changelog entry? [y/n] "
        "Version 0.1.1 released!"
    )
    assert 'version = "0.1.1"' in pyproject.read_text()
    assert (
        f"## 0.1.1 – {today}\n\n- Implement feature\n- Fix test\n- Fix linter\n"
        in changelog.read_text()
    )


def test_changelog_precommit(repo: Repo, tmp_path: Path):
    today = datetime.date.today().isoformat()

    scripts_path = tmp_path / "scripts"
    scripts_path.mkdir()
    editor_path = scripts_path / "editor.py"
    editor_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        'Path(sys.argv[1]).write_text("- Initial release!           ")\n'
    )
    editor_path.chmod(0o755)

    precommit_path = repo.path / ".git/hooks/pre-commit"
    precommit_path.write_text(
        "#!/usr/bin/env python3\n"
        "import re\n"
        "import sys\n"
        "import subprocess\n"
        "from pathlib import Path\n"
        "fail = False\n"
        "args = ['git', 'diff', '--name-only', '--cached', '--diff-filter', 'ACMR']\n"
        "for p in subprocess.check_output(args, text=True).splitlines():\n"
        "    path = Path(p)\n"
        "    old_content = path.read_text()\n"
        "    new_content = re.sub(r' +$', '', old_content, flags=re.M)\n"
        "    if new_content != old_content:\n"
        "        path.write_text(new_content)\n"
        "        fail = True\n"
        "if fail:\n"
        "    sys.exit(1)\n"
    )
    precommit_path.chmod(0o755)

    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
        'changelog = "CHANGELOG.md"\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")

    changelog = repo.path / "CHANGELOG.md"

    stdout = subprocess.check_output(
        ["release-version", "patch"],
        input="y\ny\n",
        text=True,
        env=_env({"EDITOR": str(editor_path)}),
        cwd=repo.path,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] "
        "Changelog entry for new version:\n"
        "\n"
        "- Initial release!\n"
        "\n"
        "Use this changelog entry? [y/n] "
        "Version 0.1.1 released!"
    )
    assert 'version = "0.1.1"' in pyproject.read_text()
    assert f"## 0.1.1 – {today}\n\n- Initial release!\n" in changelog.read_text()


def test_in_subdir(repo: Repo):
    src = repo.path / "src"
    src.mkdir()

    version = src / "version.txt"
    version.write_text("0.1.0")

    pyproject = src / "pyproject.toml"
    pyproject.write_text(
        "[tool.release-version]\n"
        'filename = "src/version.txt"\n'
        'pattern = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)"\n'
    )
    repo.add(version)
    repo.add(pyproject)
    repo.commit("Add files")
    stdout = subprocess.check_output(
        ["release-version", "patch"],
        input="y\n",
        text=True,
        cwd=src,
    )
    assert stdout.startswith(
        "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] Version 0.1.1 released!"
    )
    assert version.read_text() == "0.1.1"


def test_precommit_failure(repo: Repo):
    pyproject = repo.path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "test"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.release-version]\n"
        'filename = "pyproject.toml"\n'
        'pattern = "version = \\"(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)\\""\n'
    )
    repo.add(pyproject)
    repo.commit("Add pyproject.toml")

    precommit_path = repo.path / ".git/hooks/pre-commit"
    precommit_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('ERROR FROM PRE-COMMIT HOOK', file=sys.stderr)\n"
        "sys.exit(1)\n"
    )
    precommit_path.chmod(0o755)

    process = subprocess.run(
        ["release-version", "patch"],
        input="y\n",
        text=True,
        cwd=repo.path,
        capture_output=True,
    )
    assert process.returncode != 0
    assert process.stdout == "Updating version 0.1.0 -> 0.1.1. Continue? [y/n] "
    assert (
        process.stderr
        == "ERROR: Running pre-commit hook failed:\nERROR FROM PRE-COMMIT HOOK\n"
    )
    assert 'version = "0.1.0"' in pyproject.read_text()
