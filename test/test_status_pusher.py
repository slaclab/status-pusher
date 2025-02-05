#!/usr/env/python3
"""
Test module for status_pusher.py

See conftest.py for definition of git repo test fixture that is created per test method
"""
import git
from git import Repo

from pathlib import PosixPath
import pprint

import tempfile
import pytest

from unittest.mock import MagicMock, patch

# module under test
import status_pusher as sp

#
TEST_REPO_PATH = "./temp"
GIT_URL = "https://github.com/slaclab/s3df-status"
PROMETHEUS_URL = "https://prometheus.slac.stanford.edu"
QUERY = "avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )"
FILEPATH = "public/status/test_report.log"
GIT_BRANCH = "test_branch"
GIT_PUSH_URL = "https://$(shell cat $(SECRET_TEMPFILE)/s3df-status-pusher)@github.com/slaclab/s3df-status"


def test_conftest_fixtures(git_repo: Repo, repo_path: PosixPath):
    """Test the conftest git repo fixture and its correct usage."""

    # check the fixture's untracked file
    assert "file_not_in_tree.txt" in git_repo.untracked_files

    # stage a file without committing it and check it's in the diff
    file_path = repo_path / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("Test content")

    git_repo.index.add([str(file_path)])
    assert git_repo.index.diff(git_repo.head.commit)[0].a_path == "test_file.txt"

    print("\n################# Debug Output ####################################")
    print(file_path)
    print("################# /Debug Output #####################################")

    # change but don't add an in-tree file
    in_tree_file_path = repo_path / "file_in_tree.txt"
    with open(in_tree_file_path, "w") as f:
        f.write("Overwritten test content")

    print("\n################# Debug Output ####################################")
    pprint.pprint(git_repo.index.diff(git_repo.head.commit)[0].a_path)
    print("################# /Debug Output #####################################")

    # TODO fix this - how do we actually get the diff list and/or diffs?
    # may need to look at gitpython's unit tests - the docs point to them for
    # apparently undocumented stuff
    # assert "file_in_tree.txt" in git_repo.index.diff(git_repo.head.commit)


def test_git_clone(git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath):
    """
    Test git_clone function by cloning the test fixture
    """
    # get a temp dir
    tmp_path
    # clone the test fixture repo

    # sp.git_clone(repo_path,'main', tmp_path, clear=False, depth=1)


def test_epoch_to_zulu():
    """
    Test function
    """


def test_update_log_file():
    """
    Test update_log_file  function
    """


def test_commit():
    """
    Test commit function
    """


def test_push():
    """
    Test push function
    """
    # mock git push call


def test_prometheus_query():
    """
    Test promtheus_query() function
    """
    # mock prometheus api call


def test_influxdb_query():
    """
    Test influxdb_query() function
    """
    # mock influxdb api call


def test_promq():
    """
    Test promq() cli command method
    """
    # mock prometheus api call


def test_influxq():
    """
    Test influxq() command method
    """
    # mock influxdb api call


def test_cli():
    """
    Test cli function
    """
    # mock git pull, push, prometheus api or influxdb call
