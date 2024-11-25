#!/usr/bin/env python3

import time
import timeit
import tempfile
import os
import datetime
from loguru import logger
from prometheus_api_client import PrometheusConnect
import git
import click
import shutil
from pathlib import PosixPath
from typing import Tuple


def git_clone( git_url: str, git_branch: str, git_dir, clear=False ) -> git.Repo:
  """create the local git clone"""
  logger.debug(f'git_clone checking for existing directory')
  if os.path.isdir( git_dir ):
    if clear:
      logger.debug(f'removing existing git directory {git_dir}')
      shutil.rmtree( git_dir )
    else:
      # Pull to be sure we're up to date
      logger.debug(f'found existing directory {git_dir}')
      logger.debug(f'checking that existing directory is a valid repo')

      git_repo=git.Repo( git_dir )
      logger.debug(f'loaded existing git repo {git_repo}')

      origin=git_repo.remotes.origin
      logger.debug(f'existing git repo has origin {origin}')

      logger.debug(f'pulling from origin {origin}')
      origin.pull()
      return git.Repo( git_dir )

  cloned_repo = git.Repo.clone_from( git_url, git_dir )

  # TODO: check out branch

  return cloned_repo

def epoch_to_zulu( ts: float ) -> str:
  dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
  return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def update_log_file( filepath: PosixPath, timestamp: float, value: float, state: str ) -> bool:
  """append measurement to the text file"""
  line = f'{epoch_to_zulu(timestamp)}, {state}, {value}'
  logger.debug(f'appending to {filepath}: {line}')
  with filepath.open(mode='a+') as report:
    report.write( line + "\n" )
  return True

def commit(
  git_repo: git.Repo,
  filepath: str,
  commit_message='[automated] update health report',
  ) -> git.objects.commit.Commit:

  """commit and push changes to git"""
  logger.debug(f'committing updates to {filepath}')
  index = git_repo.index
  index.add( [filepath] )
  return  index.commit( commit_message )

def push( git_repo: git.Repo, git_push_url ) -> git.remote.PushInfo:
  # we can just use the gitcmd (git_repo.git) directly for everything if we want, if it's easier,
  # but we must do so for things that aren't wrapped
  gitcmd=git_repo.git
  # check if we already have a remote named 'push_origin', (with the magic token url we got)
  if not hasattr(git.remotes, 'push_origin'):
      gitcmd.remote('add', 'push_origin', git_push_url)
  origin=gr.remotes._origin
  push_origin=gr.remotes.push_origin

  # always pull before push
  logger.debug(f'pulling from origin {origin}')
  pull_res: git.remote.FetchInfo = origin.pull()

  logger.debug(f'pushing to push_origin <REDACTED URL CONTAINING TOKEN>')
  push_res: git.remote.PushInfo = push_origin.push()
  return push_res

def prometheus_query( query: str, prometheus_url: str ) -> Tuple[ float, float ]:
  """query prometheus using stock libraries"""
  logger.debug(f'querying {prometheus_url} with "{query}"')
  p = PrometheusConnect(url=prometheus_url, disable_ssl=False)
  data = p.custom_query( query=query )
  # expect that only a single value is returned from the query
  assert len(data) == 1
  # expected query output is [{'metric': {}, 'value': [1729872285.678, '1']}]
  return data[0]['value'][0], float( data[0]['value'][1])


@click.command()
@click.option( '--query', envvar='QUERY', required=True, help='query to gather metrics with' )
@click.option( '--filepath', envvar='FILEPATH', required=True, help='filepath to append measurements to relative to root of git repo directory' )
@click.option( '--prometheus-url', envvar='PROMETHEUS_URL', default='http://prometheus:8086/', show_default=True, help='url for prometheus endpoint' )
@click.option( '--git-url', envvar='GIT_URL', default='http://github.com/org/repo/', show_default=True, help='git repo for status files' )
@click.option( '--git-branch', envvar='GIT_BRANCH', default='main', show_default=True, help='git branch to use' )
@click.option( '--git-dir', envvar='GIT_DIR', default='/tmp/repo', show_default=True, help='local path for git cloned repo' )
@click.option( '--verbose', envvar='VERBOSE', default=False, is_flag=True, show_default=True, help='add debug output' )
@click.option( '--git-push-url', envvar='GIT_PUSH_URL', default=None ,show_default=True, help='URL to push to remote after commiting results. If not provided, updates will still be committed locally, but they will not be pushed to the remot.' )
def cli(
  query: str,
  prometheus_url: str,
  git_url: str,
  git_branch: str,
  git_dir: str,
  filepath: str,
  verbose: bool,
  git_push_url: str) -> bool:
  """Queries a metrics source and updates a status file in git"""
  git_repo = git_clone( git_url, git_branch, git_dir )
  logger.info(f'git_repo: {git_repo}')

  epoch_ts, value = prometheus_query( query, prometheus_url )
  logger.info( f'got data at ts {epoch_ts}: {value}' )
  report_file = PosixPath( git_dir, filepath )
  update_log_file( report_file, epoch_ts, value, 'success' )

  commit_res = commit( git_repo, report_file )
  logger.info(f'commit result: {commit_res}')

  # push repo
  # Note that auth implementation will vary between types of remote and auth mechanism.
  # Note also that Github PAT token can (and may actually have to be) incorporated into
  # the URL itself, but it's not permitted to include it in the URL just for pulling
  if git_push_url:
    push_res = push(git_repo, git_push_url)
    logger.info(f'push result: {push_res}')

if __name__ == '__main__':
  cli( auto_envvar_prefix='STATUS_PUSHER' )
