#!/usr/env/python3
"""
Test module for status_pusher.py

See conftest.py for definition of git repo test fixture that is created per test method
"""
import git
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


def test_placeholder():
    """
    Just a placeholder for now
    """
    pass


def test_git_clone():
    """
    Test git_clone function
    """


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
    Test prometheus function
    """
    # mock prometheus api call


def test_influxdb_query():
    """
    Test influxdb function
    """
    # mock influxdb api call

def test_cli():
    """
    Test cli function
    """
    # mock git pull, push, prometheus api or influxdb call
