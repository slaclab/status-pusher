#!/usr/bin/env python3

from dataclasses import dataclass
import datetime
import click
import git
from loguru import logger
from pathlib import PosixPath
from pprint import pprint
from prometheus_api_client import PrometheusConnect
import os
import shutil
import tempfile
import time
import timeit
from typing import Tuple, Optional

@dataclass
class StatusRecord:
    """
    Status record values.

    Note Fettle maps status string vals to Operational Status
    https://github.com/slaclab/s3df-status/blob/main/src/services/hooks/useSystemStatus.tsx#L30
      "success" -> Status.OPERATIONAL
      "failure" -> Status.OUTAGE
      All other values map to Status.UNKNOWN
    """
    value: Optional[float] = None
    epoch_ts: datetime.datetime = datetime.datetime.now().astimezone().timestamp()
    status: str = "UNKNOWN"


def git_clone(git_url: str, git_branch: str, git_dir, clear=False) -> git.Repo:
    """create the local git clone"""
    logger.debug(f"git_clone checking for existing directory")
    if os.path.isdir(git_dir):
        if clear:
            logger.debug(f"removing existing git directory {git_dir}")
            shutil.rmtree(git_dir)
        else:
            # Pull to be sure we're up to date
            logger.debug(f"found existing directory {git_dir}")
            logger.debug(f"checking that existing directory is a valid repo")

            git_repo = git.Repo(git_dir)
            logger.debug(f"loaded existing git repo {git_repo}")

            origin = git_repo.remotes.origin
            logger.debug(f"existing git repo has origin {origin}")

            origin_urls = list(git_repo.remotes.origin.urls)
            logger.debug(f"{origin} has urls {origin_urls}")

            logger.debug(f"pulling from origin {origin}")

            # TODO handle branch that doesn't exist yet on remote
            # TODO we need to handle the case that an existing dir has a different branch checked out -
            # ie, always do a checkout of the specified branch.
            # TODO we should separate the pull/checkout logic from the git_clone function for clarity
            # as git clone normally doesn't do either for an existing local repo
            # We might even consider doing the git handling in shell in the Makefile for simplicity...
            # unless we really may need this level of programmatic repo control in a module importing us.
            origin.pull()

            git_repo = git.Repo(git_dir)
    else:
        git_repo = git.Repo.clone_from(git_url, git_dir)

    # check out branch
    # TODO handle branch that doesn't exist yet on remote
    #  gitcmd=git_repo.git
    #  if not hasattr(git_repo.branches, git_branch):
    #    gitcmd.checkout('-b', git_branch)
    #  else:
    #    gitcmd.checkout(git_branch)
    #
    return git_repo


def epoch_to_zulu(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def update_log_file(
    filepath: PosixPath, timestamp: float, value: float, state: str
) -> bool:
    """append measurement to the text file"""
    line = f"{epoch_to_zulu(timestamp)}, {state}, {value}"
    logger.debug(f"appending to {filepath}: {line}")
    with filepath.open(mode="a+") as report:
        report.write(line + "\n")
    return True


def commit(
    git_repo: git.Repo,
    git_branch: str,
    filepath: str,
    commit_message="[automated] update health report",
) -> git.objects.commit.Commit:
    """commit and push changes to git"""
    # TODO check out desired branch prior to committing
    logger.debug(f"committing updates to {filepath}")
    index = git_repo.index
    index.add([filepath])
    return index.commit(commit_message)


def push(git_repo: git.Repo, git_branch: str, git_push_url) -> git.remote.PushInfo:
    # we can just use the gitcmd (git_repo.git) directly for everything if we want, if it's easier,
    # but we must do so for things that aren't wrapped
    gitcmd = git_repo.git
    # check if we already have a remote named 'push_origin', (with the magic token url we got)
    if not hasattr(git_repo.remotes, "push_origin"):
        gitcmd.remote("add", "push_origin", git_push_url)
    origin = git_repo.remotes.origin

    # TODO check out desired branch prior to pushing
    # TODO set up remote tracking branch if it doesn't already exist
    # TODO retry if fails eg due to race condition push interleaved from another checker instance
    push_origin = git_repo.remotes.push_origin

    # always pull before push
    origin_urls = list(git_repo.remotes.origin.urls)
    logger.debug(f"{origin} has urls {origin_urls}")

    logger.debug(f"pulling from origin {origin}")
    pull_res: git.remote.FetchInfo = origin.pull()

    push_origin_urls = list(git_repo.remotes.origin.urls)
    logger.debug(f"{push_origin} has urls {push_origin_urls}")

    logger.debug(f"pushing to push_origin <REDACTED URL CONTAINING TOKEN>")
    push_res: git.remote.PushInfo = push_origin.push()

    return push_res


def prometheus_query(query: str, prometheus_url: str) -> Tuple[float, float]:
    """query prometheus using stock libraries"""
    logger.debug(f'querying {prometheus_url} with "{query}"')
    p = PrometheusConnect(url=prometheus_url, disable_ssl=False)
    data = p.custom_query(query=query)
    # expect that only a single value is returned from the query
    assert len(data) == 1
    # expected query output is [{'metric': {}, 'value': [1729872285.678, '1']}]
    return data[0]["value"][0], float(data[0]["value"][1])

def influx_query(query: str, prometheus_url: str) -> Tuple[float, float]:
    """query influx using stock libraries"""
    pass

@click.group()
@click.option(
    "--query", envvar="QUERY", required=True, help="query to gather metrics with"
)
@click.option(
    "--filepath",
    envvar="FILEPATH",
    required=True,
    help="filepath to append measurements to relative to root of git repo directory",
)
@click.option(
    "--prometheus-url",
    envvar="PROMETHEUS_URL",
    default="http://prometheus:8086/",
    show_default=True,
    help="url for prometheus endpoint",
)
@click.option(
    "--git-url",
    envvar="GIT_URL",
    default="http://github.com/org/repo/",
    show_default=True,
    help="git repo for status files",
)
@click.option(
    "--git-branch",
    envvar="GIT_BRANCH",
    default="main",
    show_default=True,
    help="git branch to use",
)
@click.option(
    "--git-dir",
    envvar="GIT_DIR",
    default="/tmp/repo",
    show_default=True,
    help="local path for git cloned repo",
)
@click.option(
    "--verbose",
    envvar="VERBOSE",
    default=False,
    is_flag=True,
    show_default=True,
    help="add debug output",
)
@click.option(
    "--git-push-url",
    envvar="GIT_PUSH_URL",
    default=None,
    show_default=True,
    help="URL to push to remote after commiting results. If not provided, updates will still be committed locally, but they will not be pushed to the remote.",
)
@click.pass_context
def cli(ctx,
    query: str,
    prometheus_url: str,
    git_url: str,
    git_branch: str,
    git_dir: str,
    filepath: str,
    verbose: bool,
    git_push_url: str,
) -> bool:
    """Queries a metrics source and updates a status file in git"""

    git_repo = git_clone(git_url, git_branch, git_dir)
    logger.info(f"git_repo: {git_repo}")

    @ctx.call_on_close
    def git_commit_and_push():
        logger.info(f"writing report file at {filepath}")
        logger.info(f"Data record:\n{ctx.obj.epoch_ts}: {ctx.obj.value}")

        report_file = PosixPath(git_dir, filepath)
        update_log_file(report_file, ctx.obj.epoch_ts, ctx.obj.value, ctx.obj.status)

        logger.info(f"updated log file: {report_file}")

        commit_res = commit(git_repo, git_branch, report_file)
        logger.info(f"commit result: {commit_res}")

        # push repo
        # Note that auth implementation will vary between types of remote and auth mechanism.
        # Note also that Github PAT token can (and may actually have to be) incorporated into
        # the URL itself, but it's not permitted to include it in the URL just for pulling
        if git_push_url:
            push_res = push(git_repo, git_branch, git_push_url)
            logger.info(f"push result: {push_res}")

@cli.command()
@click.pass_context
def promq(ctx):
    """
    Prometheus_query command wrapped to do pre and post git actions.
    Performs checkout, pull, prometheus_query, commit, push.
    """
    ######################################
    # DEBUG
    # Why don't we get ctx.params populated here?
    # simple example of command group passing context:
    # https://click.palletsprojects.com/en/stable/commands/
    pprint(ctx)
    breakpoint()
    #####################################

    logger.debug(f"promq_command called with {ctx.params}")

    prom_query = ctx.params['query']
    prom_url = ctx.params['prometheus_url']

    logger.debug(f'calling prometheus_query({"prom_query"}, {"prom_url"})')
    epoch_ts, value = prometheus_query(prom_query, prom_url)
    logger.info(f"got data at ts {ctx.obj.epoch_ts}: {ctx.obj.value}")

    ctx.obj(epoch_ts=epoch_ts, value=value, status="success")


@click.command()
def influxq(ctx):
    """
    InfluxDB command wrapped to do pre and post git actions.
    Performs checkout, pull, prometheus_query, commit, push.
    """
    pass

if __name__ == "__main__":
    # shared context object for subcommands to pass vals back
    status_record = StatusRecord()
    cli(obj=status_record, auto_envvar_prefix="STATUS_PUSHER")
