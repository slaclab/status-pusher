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


def git_clone( git_url: str, git_branch: str, git_dir, clear=False ):
  """create the local git clone"""
  logger.debug(f'setting up git clone of {git_url}:{git_branch} to {git_dir}')
  if os.path.isdir( git_dir ):
    if clear:
      logger.debug(f'removing existing git directory {git_dir}')
      shutil.rmtree( git_dir )
    else:
      # TODO: validate real git repo
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
  ) -> bool:

  """commit and push changes to git"""
  logger.debug(f'committing updates to {filepath}')
  index = git_repo.index
  index.add( [filepath] )
  index.commit( commit_message )

  return True

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
@click.option( '--git-token', envvar='GIT_TOKEN', required=True, help='git PAT (Personal Access Token)' )
@click.option( '--git-branch', envvar='GIT_BRANCH', default='main', show_default=True, help='git branch to use' )
@click.option( '--git-dir', envvar='GIT_DIR', default='/tmp/repo', show_default=True, help='local path for git cloned repo' )
@click.option( '--verbose', envvar='VERBOSE', default=False, is_flag=True, show_default=True, help='add debug output' )
@click.option( '--do-git-push', envvar='GIT_PUSH', default=False, is_flag=True, show_default=True, help='Push to remote after commiting results' )
def cli(
  query: str,
  prometheus_url: str,
  git_url: str,
  git_token: str,
  git_branch: str,
  git_dir: str,
  filepath: str,
  verbose: bool,
  do_git_push: bool ) -> bool:
  """Queries a metrics source and updates a status file in git"""
  git_repo = git_clone( git_url, git_branch, git_dir )
  epoch_ts, value = prometheus_query( query, prometheus_url )
  logger.info( f'got data at ts {epoch_ts}: {value}' )
  report_file = PosixPath( git_dir, filepath )
  update_log_file( report_file, epoch_ts, value, 'success' ) 
  commit( git_repo, report_file )

  # TODO push repo
  if do_git_push:
    git_repo.remote.push(git_branch)

if __name__ == '__main__':
  cli( auto_envvar_prefix='STATUS_PUSHER' )
