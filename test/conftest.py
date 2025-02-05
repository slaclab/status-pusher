"""
conftest for status_pusher.py
Here we will create a temporary git repo as a test fixture that will be
reset on a per-test-method basis.
"""

import tempfile
import shutil

from git import Repo
from pathlib import PosixPath
import pytest


@pytest.fixture(name="repo_path", scope="function")
def repo_path(tmpdir: PosixPath) -> PosixPath:
    """Fixture: init a temporary Git repository and yield its PosixPath."""
    repo = Repo.init(tmpdir)

    # add a file not in the tree
    file_path = tmpdir / "file_in_tree.txt"
    with open(file_path, "w") as f:
        f.write("content of file_in_tree.txt")

    # Note we need an initial commit to avoid git diff failing with "fatal: bad revision 'HEAD'"
    repo.index.commit("init commit - file_in_tree.txt")

    # add a file not in the tree
    file_path = tmpdir / "file_not_in_tree.txt"
    with open(file_path, "w") as f:
        f.write("content of file_not_in_tree.txt")

    yield PosixPath(repo.working_dir)


@pytest.fixture(name="git_repo", scope="function")
def git_repo(repo_path: PosixPath) -> Repo:
    """Fixture: Git repository."""
    yield Repo(repo_path)
