#!/usr/env/python3
"""
Test module for status_pusher.py

See conftest.py for definition of git repo test fixture that is created per test method
"""
import datetime

import git
from git import Repo

import os
from pathlib import PosixPath
import pprint


# test tooling
import tempfile
import pytest
from click.testing import CliRunner

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

    # TODO fix this - how do we actually get the diff list and/or diffs?
    # may need to look at gitpython's unit tests - the docs point to them for
    # apparently undocumented stuff
    # assert "file_in_tree.txt" in git_repo.index.diff(git_repo.head.commit)


def test_git_clone_no_existing_dir(
    git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath
):
    """
    Test git_clone function by cloning the test repo fixture.
    case: no existing target dir exists
    """
    # get a temp dir for the cloned repo
    clone_path = tmp_path / "cloned_repo"

    # clone the test fixture repo

    repo_path_str = str(repo_path)
    repo_branch_str = "main"
    tmp_path_str = str(clone_path)

    print("\n################# Debug Output ####################################")
    print(repo_path_str)
    print(clone_path)
    print("################# /Debug Output ####################################")

    cloned_repo: Repo = sp.git_clone(repo_path_str, repo_branch_str, tmp_path_str)
    assert cloned_repo.git_dir.startswith(cloned_repo.working_tree_dir)
    # check it's where we intended it to be
    assert cloned_repo.working_tree_dir == str(clone_path)


def test_git_clone_with_existing_dir_not_a_repo(
    git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath
):
    """
    Test correct failure mode for git_clone function for existing target dir
    case: target dir already exists but is NOT existing repo
    """
    # get a temp dir for the cloned repo
    clone_path = tmp_path / "cloned_repo"

    # make the pre-existing dir  (empty)
    os.mkdir(clone_path)

    # clone the test fixture repo

    repo_path_str = str(repo_path)
    repo_branch_str = "main"
    tmp_path_str = str(clone_path)

    # This should raise git.exc.InvalidGitRepositoryError
    with pytest.raises(git.exc.InvalidGitRepositoryError):
        cloned_repo: Repo = sp.git_clone(repo_path_str, repo_branch_str, tmp_path_str)


# TODO complete this
def test_git_clone_with_existing_repo(
    git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath
):
    """
    Test git_clone function by cloning (or in this case updating) the test repo fixture.
    case: target dir already exists and IS an existing repo
    """
    # get a temp dir for the cloned repo
    clone_path = tmp_path / "cloned_repo"

    # clone the test fixture repo

    repo_path_str = str(repo_path)
    repo_branch_str = "main"
    tmp_path_str = str(clone_path)

    # first clone the repo normally so it exists
    cloned_repo: Repo = sp.git_clone(repo_path_str, repo_branch_str, tmp_path_str)

    # now make a change to the original test repo so we have changes to pull
    # TODO

    # test that the clone_repo() call appropriately pulls changes
    # TODO


def test_epoch_to_zulu():
    """
    Test function
    """
    epoch = 1742430572
    actual = sp.epoch_to_zulu(epoch)
    expected = "2025-03-20T00:29:32Z"
    assert actual == expected


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
    mock_return_val = [{"metric": {}, "value": [1729872285.678, "1"]}]
    mock_query = "avg( avg_over_time(foo{service=`bar`}[5m]))"
    mock_url = "https://mock.prometheus.url.local"

    with patch.object(
        sp.PrometheusConnect, "custom_query", return_value=mock_return_val
    ) as mock_prom:
        # sp.PrometheusConnect = MagicMock(return_value = mock_return_val)
        actual = sp.prometheus_query(query=mock_query, prometheus_url=mock_url)
        # assert mock_prom.called_with(query=mock_query)

    expected = (1729872285.678, 1.0)

    assert actual == expected


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

    #    runner = CliRunner()
    #    result = runner.invoke(sp.cli, ['promq'])
    #
    #    check result
    pass


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
