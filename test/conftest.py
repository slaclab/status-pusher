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


@pytest.fixture(name="test-repo", scope="session")
def repo(tmp_path: PosixPath) -> Repo:
    """
    Create temp git repo fixture for testing
    """
    pass


import pytest
import git


@pytest.fixture
def repo_path(tmpdir) -> PosixPath:
    """Fixture: init a temporary Git repository and yield its PosixPath."""
    repo = git.Repo.init(tmpdir)
    # Note we need an initial commit to avoid git diff failing with "fatal: bad revision 'HEAD'"
    repo.index.commit("init commit")

    # add a file not in the tree
    file_path = tmpdir / "not_in_git.txt"
    with open(file_path, "w") as f:
        f.write("content")

    yield PosixPath(repo.working_dir)


@pytest.fixture
def git_repo(repo_path) -> Repo:
    """Fixture: Git repository."""
    yield Repo(repo_path)
