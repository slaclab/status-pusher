#!/usr/bin/env python3
"""
status_pusher.py

cli utility to make status checks, eg against prometheus and influxdb; commit the result to
a log file in a repo, and push the changeset upstream to a repo checked by a Fettle dashboard.
"""

# standard imports
import datetime
from enum import Enum
import operator
import os
from pathlib import PosixPath
import pprint
from typing import Tuple, Optional

# 3rd party imports
import requests
from pydantic.dataclasses import dataclass
import click
import git

from loguru import logger
from prometheus_api_client import PrometheusConnect


class Status(Enum):
    """
    Status string enum for use in StatusRecord; as expected by frontend Fettle UI
    """

    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"


class ConditionComparitor(Enum):
    """
    Comparison Operator to be specified as a CLI option along with condition value (float)
    that will be used to evaluate success/failure criteria.
    """

    eq = operator.eq
    lt = operator.lt
    lte = operator.le
    gt = operator.gt
    gte = operator.ge


@dataclass
class StatusRecord:
    """
    Status record consisting of a value, an epoch timestamp and a status enum.

    Note Fettle maps status string vals to Operational Status
    https://github.com/slaclab/s3df-status/blob/main/src/services/hooks/useSystemStatus.tsx#L30
      "success" -> Status.OPERATIONAL
      "failure" -> Status.OUTAGE
      All other values map to Status.UNKNOWN
    """

    value: Optional[float] = None
    epoch_ts: datetime.datetime = datetime.datetime.now().astimezone().timestamp()
    status: Status = Status.UNKNOWN.value


def git_clone(git_url: str, git_branch: str, git_dir, depth=10) -> git.Repo:
    """create the local git clone"""
    if git_branch != "main":
        raise NotImplementedError(
            "git_clone method currently always uses the default branch"
        )

    if os.path.isdir(git_dir):
        # Pull to be sure we're up to date
        logger.debug(f"found existing directory {git_dir}")
        logger.debug("checking that existing directory is a valid repo")

        git_repo = git.Repo(git_dir)
        logger.debug(f"loaded existing git repo {git_repo}")

        origin = git_repo.remotes.origin
        logger.debug(f"existing git repo has origin {origin}")

        origin_urls = list(git_repo.remotes.origin.urls)
        logger.debug(f"{origin} has urls {origin_urls}")

        logger.debug(f"pulling from origin {origin} with depth {depth}")

        # TODO
        # - implement git_branch option
        # - handle branch that doesn't exist yet on remote
        # - we need to handle the case that an existing dir has a different branch checked
        #   out - ie, always do a checkout of the specified branch.
        # - we should separate the pull/checkout logic from the git_clone function for clarity
        #   as git clone normally doesn't do either for an existing local repo
        origin.pull(depth=depth)

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
    """Convert an epoch float to a zulu datetime in ISO format"""
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
    if git_branch != "main":
        raise NotImplementedError(
            "commit method currently always uses the default branch"
        )

    logger.debug(f"committing updates to {filepath}")
    index = git_repo.index
    index.add([filepath])
    return index.commit(commit_message)


def push(git_repo: git.Repo, git_branch: str, git_push_url) -> git.remote.PushInfo:
    """
    Pull from remote, then push changes in a local git repo to remote.
    NOTE: git_branch is NOT implemented, and the current local branch will always be used.
    """
    # we can just use the gitcmd (git_repo.git) directly for everything if we want, if it's easier,
    # but we must do so for things that aren't wrapped
    gitcmd = git_repo.git
    # check if we already have a remote named 'push_origin', (with the magic token url we got)
    if not hasattr(git_repo.remotes, "push_origin"):
        gitcmd.remote("add", "push_origin", git_push_url)
    origin = git_repo.remotes.origin

    # TODO
    # - check out desired branch prior to pushing
    #  - set up remote tracking branch if it doesn't already exist
    # - retry if fails eg due to race condition push interleaved from another checker instance
    if git_branch != "main":
        raise NotImplementedError(
            "commit method currently always uses the default branch"
        )
    push_origin = git_repo.remotes.push_origin

    # always pull before push
    origin_urls = list(git_repo.remotes.origin.urls)
    logger.debug(f"{origin} has urls {origin_urls}")

    logger.debug(f"pulling from origin {origin}")
    _pull_res: git.remote.FetchInfo = origin.pull()

    push_origin_urls = list(git_repo.remotes.origin.urls)
    logger.debug(f"{push_origin} has urls {push_origin_urls}")

    logger.debug("pushing to push_origin <REDACTED URL CONTAINING TOKEN>")
    push_res: git.remote.PushInfo = push_origin.push()

    return push_res


def prometheus_query(query: str, prometheus_url: str) -> Tuple[float, float]:
    """query prometheus using stock libraries"""
    logger.debug(f'querying {prometheus_url} with "{query}"')
    p = PrometheusConnect(url=prometheus_url, disable_ssl=False)
    data = p.custom_query(query=query)
    # expect that only a single value is returned from the query
    assert len(data) == 1
    # expected query output like [{'metric': {}, 'value': [1729872285.678, '1']}]

    (epoch_ts, value) = (data[0]["value"][0], float(data[0]["value"][1]))
    logger.debug(f"returned (epoch_ts, value) {(epoch_ts, value)}")

    return (epoch_ts, value)


def influx_query(db_name: str, influx_url: str, query: str) -> Tuple[float, float]:
    """query influx using http api"""
    qry_timeout = 15
    path = "/query?"
    url_qry_path = influx_url + path

    # TODO Determine if we can know all potentially required url params in advance?
    # If not, we could either provide arbitrary cli params to be passed in, or simply
    # permit the user to build the complete query url with params themselves.

    # NOTE influxdb query api seems to require q param to be FIRST
    url_params = {"q": query, "db": db_name}

    logger.debug(f"querying {url_qry_path} with db_name: {db_name}, query: {query}")
    response = requests.get(url_qry_path, params=url_params, timeout=qry_timeout)

    # raise an HTTPError exception if call failed
    response.raise_for_status()

    # expected query output like:
    #   {
    #       "results": [
    #           {
    #               "statement_id": 0,
    #               "series": [
    #                   {
    #                       "name": "squeue",
    #                       "columns": ["time", "last"],
    #                       "values": [["2025-02-01T03:11:34Z", 1]],
    #                   }
    #               ],
    #           }
    #       ]
    #   }

    logger.debug(f"got response {response}")

    logger.debug(f"response.text:\n{response.text}")

    logger.debug(f"got data {response.text}")

    # Remember the json() method actually returns a dictionary
    data = response.json()

    logger.debug(f"interpreted data as {pprint.pformat(data)}")

    # TODO
    # expect only a single value
    assert len(data["results"]) == 1

    (epoch_ts, value) = (
        datetime.datetime.fromisoformat(
            data["results"][0]["series"][0]["values"][0][0]
        ).timestamp(),
        data["results"][0]["series"][0]["values"][0][1],
    )

    return (epoch_ts, value)


@click.group()
@click.option("--query", required=True, help="query to gather metrics with")
@click.option(
    "--success-condition",
    #    required=True,
    help="Comparison operator to determine success.\n"
    "Metric value produced by query will be compared with the value provided by --success-value\n"
    "to determine success vs failure.",
    type=click.Choice(ConditionComparitor.__members__),
    default=ConditionComparitor.eq.name,
    show_default=True,
)
@click.option(
    "--success-value",
    #    required=True,
    help="Value with which to compare query metric result to determine success.\n"
    "Metric value produced by query will be compared this value using the comparitor operator\n"
    "provided with --success-condition",
    type=float,
    default=1,
    show_default=True,
)
@click.option(
    "--filepath",
    required=True,
    help="filepath to append measurements to relative to root of git repo directory",
)
@click.option(
    "--git-url",
    default="http://github.com/org/repo/",
    show_default=True,
    help="git repo for status files",
)
@click.option(
    "--git-branch",
    default="main",
    show_default=True,
    help="NOT IMPLEMENTED! `main` git branch will be used.",
)
@click.option(
    "--git-dir",
    default="/tmp/repo",
    show_default=True,
    help="local path for git cloned repo",
)
@click.option(
    "--verbose",
    default=False,
    is_flag=True,
    show_default=True,
    help="add debug output",
)
@click.option(
    "--git-push-url",
    default=None,
    show_default=True,
    help="URL to push to remote after commiting results."
    "If not provided, updates will still be committed locally, but they will not be pushed "
    "to the remote.",
)
@click.pass_context
def cli(
    ctx,
    query: str,
    success_condition: ConditionComparitor,
    success_value: float,
    git_url: str,
    git_branch: str,
    git_dir: str,
    filepath: str,
    verbose: bool,
    git_push_url: str,
) -> bool:
    """Queries a metrics source, evaluates success criterion, and updates a status file in git"""

    # ensure we got a StatusRecord object in case we were invoked outside __main__
    ctx.ensure_object(StatusRecord)

    # TODO handle non-default branch
    if git_branch != "main":
        raise NotImplementedError(
            "status_pusher currently always uses the default branch"
        )

    git_repo = git_clone(git_url, git_branch, git_dir)
    logger.info(f"git_repo: {git_repo}")

    # queries specified by subcommand now are executed, populating ctx.obj:StatusRecord
    # and finally the call_on_close handler below does the commit and push

    # note that click call_on_close even if subcommand raises an exception, resulting in
    # in an "Unknown" status being recorded

    @ctx.call_on_close
    def eval_success_git_commit_and_push():
        logger.debug(
            f"evaluating success condition:\n"
            f"success_condition: {success_condition}\n"
            f"ctx.obj.value: {ctx.obj.value}\n"
            f"success_value: {success_value}\n"
        )

        # handle success/failure criteria
        ctx.obj.status = (
            Status.SUCCESS.value
            if ConditionComparitor[success_condition].value(
                ctx.obj.value, success_value
            )
            else Status.FAILED.value
        )
        logger.debug(
            f"Computed {ConditionComparitor[success_condition].value}"
            f"({ctx.obj.value}, {success_value})"
            f" == {ctx.obj.status}"
        )

        logger.debug(f"writing report file at {filepath}")
        logger.debug(f"Data record:\n{pprint.pformat(ctx.obj)}")

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
        else:
            logger.info("Will not push because git_push_url == False")


@click.option(
    "--url",
    default="http://prometheus:8086/",
    show_default=True,
    help="url for prometheus endpoint",
)
@cli.command()
@click.pass_context
def promq(ctx, url: str):
    """
    Prometheus query command wrapped to do pre and post git actions.
    Performs checkout, pull, prometheus_query, success condition evaluation, log result,
    commit, push.
    """
    logger.debug(
        f"promq command called with parent params {ctx.parent.params} "
        f"and command params {ctx.params}"
    )

    prom_url = ctx.params["url"]
    prom_query = ctx.parent.params["query"]

    logger.debug(f'calling prometheus_query({"prom_query"}, {"prom_url"})')
    epoch_ts, value = prometheus_query(prom_query, prom_url)
    logger.info(f"prometheus_query returned (epoch_ts, value): ({epoch_ts}, {value})")

    # populate context object for cli handler to access
    ctx.obj.epoch_ts = epoch_ts
    ctx.obj.value = value


@click.option(
    "--db-name",
    default="mydb",
    show_default=True,
    help="database name to target with InfluxDB query",
)
@click.option(
    "--url",
    default="http://influxdb:8086/",
    show_default=True,
    help="url for influxdb endpoint",
)
@cli.command()
@click.pass_context
def influxq(ctx, db_name, url):
    """
    InfluxDB query command wrapped to do pre and post git actions.
    Performs checkout, pull, prometheus_query, success condition evaluation, log result,
    commit, push.
    """
    logger.debug(
        f"influxq command called with parent cli params {pprint.pformat(ctx.parent.params)} "
        f"and command params {pprint.pformat(ctx.params)}"
    )

    influxdb_db_name = ctx.params["db_name"]
    influxdb_url = ctx.params["url"]
    influxdb_qry = ctx.parent.params["query"]

    logger.debug(f'calling influxdb_query({"influxdb_qry"}, {"influxdb_url"})')
    epoch_ts, value = influx_query(influxdb_db_name, influxdb_url, influxdb_qry)
    logger.info(f"influx_query returned (epoch_ts, value): ({epoch_ts}, {value})")

    # populate context object for cli handler to access
    ctx.obj.epoch_ts = epoch_ts
    ctx.obj.value = value


if __name__ == "__main__":
    # shared context object for subcommands to pass vals back
    status_record = StatusRecord()
    cli(obj=status_record, auto_envvar_prefix="STATUS_PUSHER")
