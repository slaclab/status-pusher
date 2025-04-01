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
import pytest
from click.testing import CliRunner
import urllib

# mock and objects to mock out
from unittest.mock import MagicMock, patch
import requests_mock

# module under test
import status_pusher as sp


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

    # change but don't add an in-tree file
    in_tree_file_path = repo_path / "file_in_tree.txt"
    with open(in_tree_file_path, "w") as f:
        f.write("Overwritten test content")

    # check that changed file is in diffs
    actual = git_repo.index.diff(git_repo.head.commit.tree)[0].a_blob.name
    expected = "test_file.txt"

    assert actual == expected


### Function unit tests ###


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


def test_git_clone_with_existing_repo_dir(
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
    clone_path_str = str(clone_path)

    # first clone the repo normally so to create a repo directory we can pretend already existed
    cloned_repo: Repo = sp.git_clone(repo_path_str, repo_branch_str, clone_path_str)

    # now make a change to the original test repo so we have changes to pull to the
    # pre-existing (already a clone of the original repo) directory
    index = git_repo.index
    new_file_path = repo_path / "new_file.txt"
    new_file_content = "content of newly added file in parent repo"
    new_commit_message = (
        "Newly committed file in parent repo to test git pull: new_file.txt"
    )
    with open(new_file_path, "w") as f:
        f.write(new_file_content)
    git_repo.index.add(new_file_path)
    git_repo.index.commit(new_commit_message)

    # Now pretend we're calling git_clone for the first time, targeting the existing-repo
    # directory we created in the fist call; then we can test that the clone_repo() call
    # appropriately just pulls the new changes
    recloned_repo: Repo = sp.git_clone(repo_path_str, repo_branch_str, clone_path_str)

    # check that the new file is really there
    # check git log for our message committing the new file
    actual_latest_commit_msg = recloned_repo.git.log().splitlines()[4]
    expected_latest_commit_msg = "    " + new_commit_message
    assert actual_latest_commit_msg == expected_latest_commit_msg

    # read new file content
    with open(clone_path / "new_file.txt", "r") as f:
        actual_new_file_content = f.read()
    expected_new_file_content = new_file_content
    assert actual_new_file_content == expected_new_file_content


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


def test_commit(git_repo: Repo, repo_path: PosixPath):
    """
    Test commit function
    """
    """
    Test git_commit function by commiting a new file to the test repo fixture.
    """
    git_branch = "main"
    test_commit_message = "unit-test commit message"

    new_file_path = repo_path / "new_file.txt"

    new_file_content = "content of newly added file in parent repo"
    with open(new_file_path, "w") as f:
        f.write(new_file_content)

    # test call
    sp.commit(git_repo, git_branch, new_file_path, test_commit_message)

    # check for the expected new commit message in the log
    actual_latest_commit_msg = git_repo.git.log().splitlines()[4]
    expected_latest_commit_msg = "    " + test_commit_message
    assert actual_latest_commit_msg == expected_latest_commit_msg


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
    mock_url = "https://mock.prometheus.url.local"
    mock_query = "avg( avg_over_time(foo{service=`bar`}[5m]))"
    mock_return_val = [{"metric": {}, "value": [1729872285.678, "1"]}]

    with patch.object(
        sp.PrometheusConnect, "custom_query", return_value=mock_return_val
    ) as mock_prom_qry:
        actual = sp.prometheus_query(query=mock_query, prometheus_url=mock_url)
        mock_prom_qry.assert_called_with(query=mock_query)

    expected = (1729872285.678, 1.0)

    assert actual == expected


def test_influx_query():
    """
    Test influx_query() function
    """
    # mock influxdb api call
    # expected query output like:

    mock_return_val = {
        "results": [
            {
                "statement_id": 0,
                "series": [
                    {
                        "name": "squeue",
                        "columns": ["time", "last"],
                        "values": [["2025-02-01T03:11:34Z", 1]],
                    }
                ],
            }
        ]
    }
    mock_db_name = "mockdb"
    mock_query = 'SELECT last("foo") FROM "bar" LIMIT 1'
    mock_url = "https://mock.influxdb.url.local"

    expected_uri = (
        f"{mock_url}/query?q={urllib.parse.quote_plus(mock_query)}&db={mock_db_name}"
    )

    with requests_mock.Mocker() as req_mock:
        req_mock.register_uri("GET", expected_uri, json=mock_return_val)
        actual = sp.influx_query(
            db_name=mock_db_name, influx_url=mock_url, query=mock_query
        )

    expected = (1738379494.0, 1)

    assert actual == expected


#### End-to-end CLI invocation tests ###


def test_promq_cli(git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath):
    """
    Test promq() cli command method, mocking the Prometheus custom_query request,
    and using our git repo fixture.
    """
    # get a temp dir for the cloned repo
    clone_path = tmp_path / "cloned_repo"

    # prepare to use the test fixture repo
    repo_path_str = str(repo_path)
    repo_branch_str = "main"
    tmp_path_str = str(clone_path)

    # mock prometheus api call vals
    mock_url = "https://mock.prometheus.url.local"
    mock_query = "avg( avg_over_time(foo{service=`bar`}[5m]))"
    mock_return_val = [{"metric": {}, "value": [1729872285.678, "1"]}]

    # mock env vars
    os_environ = {
        "STATUS_PUSHER_GIT_DIR": tmp_path_str,
        "STATUS_PUSHER_GIT_URL": repo_path_str,
        "STATUS_PUSHER_PROMQ_URL": mock_url,
        "STATUS_PUSHER_QUERY": mock_query,
        "STATUS_PUSHER_FILEPATH": "test_report.log",
        "STATUS_PUSHER_GIT_BRANCH": "main",
    }
    runner = CliRunner()

    # mock prom connect; use our git fixture
    with patch.dict(os.environ, os_environ, clear=True) as mock_env, patch.object(
        sp.PrometheusConnect, "custom_query", return_value=mock_return_val
    ) as mock_prom_qry:

        cli_params = ["promq"]

        status_record = sp.StatusRecord()

        # invoke cli
        actual_result = runner.invoke(
            sp.cli, cli_params, obj=status_record, auto_envvar_prefix="STATUS_PUSHER"
        )

        print(actual_result.output)
        pprint.pprint(mock_prom_qry.mock_calls)

    # assert successful exit code
    assert actual_result.exit_code == 0

    # assert expected calls
    mock_prom_qry.assert_called_with(query=mock_query)

    # assert status record SUCCESS
    assert status_record.status == sp.Status.SUCCESS

    # assert status value 1.0
    assert status_record.value == 1.0

    # TODO check our temporary git log file was updated


def test_influxq_cli(
    git_repo: Repo, repo_path: PosixPath, tmp_path: PosixPath, monkeypatch
):
    """
    Test influxq() command method, mocking the http request and using our git repo fixture.
    """
    # get a temp dir for the cloned repo
    clone_path = tmp_path / "cloned_repo"

    # prepare to use the test fixture repo
    repo_path_str = str(repo_path)
    repo_branch_str = "main"
    tmp_path_str = str(clone_path)

    # mock influx api call vals
    mock_db_name = "mockdb"
    mock_query = 'SELECT last("foo") FROM "bar" LIMIT 1'
    mock_url = "https://mock.influxdb.url.local"
    mock_return_val = {
        "results": [
            {
                "statement_id": 0,
                "series": [
                    {
                        "name": "squeue",
                        "columns": ["time", "last"],
                        "values": [["2025-02-01T03:11:34Z", 1]],
                    }
                ],
            }
        ]
    }

    # mock env vars
    os_environ = {
        "STATUS_PUSHER_GIT_DIR": tmp_path_str,
        "STATUS_PUSHER_GIT_URL": repo_path_str,
        "STATUS_PUSHER_INFLUXQ_URL": mock_url,
        "STATUS_PUSHER_INFLUXQ_DB_NAME": mock_db_name,
        "STATUS_PUSHER_QUERY": mock_query,
        "STATUS_PUSHER_FILEPATH": "test_report.log",
        "STATUS_PUSHER_GIT_BRANCH": "main",
    }
    runner = CliRunner()

    # mock http req; use our git fixture
    expected_uri = (
        f"{mock_url}/query?q={urllib.parse.quote_plus(mock_query)}&db={mock_db_name}"
    )

    with patch.dict(
        os.environ, os_environ, clear=True
    ) as mock_env, requests_mock.Mocker() as req_mock:
        req_mock.register_uri("GET", expected_uri, json=mock_return_val)

        cli_params = ["influxq"]

        status_record = sp.StatusRecord()

        # invoke cli
        actual_result = runner.invoke(
            sp.cli, cli_params, obj=status_record, auto_envvar_prefix="STATUS_PUSHER"
        )

        # breakpoint()
        # self.exception.request.__str__()

        print(actual_result.output)

    # assert successful exit code
    assert actual_result.exit_code == 0

    # assert status record SUCCESS
    assert status_record.status == sp.Status.SUCCESS

    # assert status value 1.0
    assert status_record.value == 1.0

    # TODO check our temporary git log file was updated
