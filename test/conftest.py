"""
conftest for status_pusher.py
Here we will create a temporary git repo as a test fixture that will be
reset on a per-test-method basis.
"""

from git import Repo
from pathlib import PosixPath
import pytest


@pytest.fixture(name="repo_path", scope="function")
def repo_path(tmp_path: PosixPath) -> PosixPath:
    """
    Fixture: init a temporary Git repository and yield its PosixPath.

    Note we need an initial commit to avoid git diff failing with "fatal: bad revision 'HEAD'"
    We will include a committed file in the tree, and an untracked file in the repo dir.
    """
    tmpdir = tmp_path / "status_pusher_test_repo"

    repo = Repo.init(tmpdir)

    # add a file in the tree
    intree_file_path = tmpdir / "file_in_tree.txt"
    with open(intree_file_path, "w") as f:
        f.write("content of file_in_tree.txt")
    repo.index.add(intree_file_path)
    repo.index.commit("init commit - file_in_tree.txt")

    # add an untracked file not in the tree
    untracked_file_path = tmpdir / "file_not_in_tree.txt"
    with open(untracked_file_path, "w") as f:
        f.write("content of file_not_in_tree.txt")
    # Note we will neither add nor commit this file

    # add a test_report.txt log file in the tree
    test_report_file_path = tmpdir / "test_report.log"
    with open(test_report_file_path, "w") as f:
        f.write("2024-11-23T01:23:40Z, success, 1.0")
    repo.index.add(test_report_file_path)
    repo.index.commit("commit test_report.log with 1 entry")

    yield PosixPath(repo.working_dir)


@pytest.fixture(name="git_repo", scope="function")
def git_repo(repo_path: PosixPath) -> Repo:
    """Fixture: Git repository."""
    yield Repo(repo_path)
