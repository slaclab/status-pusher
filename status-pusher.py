#!/usr/bin/env python3

import time
import timeit
import tempfile
import os
import datetime
from loguru import logger
from  prometheus_pandas.query import Prometheus 
from prometheus_api_client import PrometheusConnect
from git import Repo
import click
import shutil
from typing import Tuple


def git_clone( git_url: str, git_branch: str, git_dir, clear=True ):
  """create the local git clone"""
  logger.debug(f'setting up git clone of {git_url}:{git_branch} to {git_dir}')
  if os.path.isdir( git_dir ) and clear:
    logger.debug(f'removing existing git directory {git_dir}')
    shutil.rmtree( git_dir )
  cloned_repo = Repo.clone_from( git_url, git_dir )
  return cloned_repo

# TODO: deprecate
def prometheus_pandas_query( query: str, prometheus_url: str ):
  """query prometheus using prometheus_pands"""
  logger.debug(f'querying {prometheus_url} with "{query}"')
  p = Prometheus( prometheus_url )
  return p.query( query )

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
@click.option( '--prometheus-url', envvar='PROMETHEUS_URL', default='http://prometheus:8086/', show_default=True, help='url for prometheus endpoint' )
@click.option( '--git-url', envvar='GIT_URL', default='http://github.com/org/repo/', show_default=True, help='git repo for status files' )
@click.option( '--git-branch', envvar='GIT_BRANCH', default='main', show_default=True, help='git branch to use' )
@click.option( '--git-dir', envvar='GIT_DIR', default='/tmp/repo', show_default=True, help='local path for git cloned repo' )
@click.option( '--verbose', envvar='VERBOSE', default=False, is_flag=True, show_default=True, help='add debug output' )
def cli( query: str, prometheus_url: str, git_url: str, git_branch: str, git_dir: str, verbose: bool ) -> bool:
  """Queries a metrics source and updates a status file in git"""
  g = git_clone( git_url, git_branch, git_dir )
  epoch_ts, value = prometheus_query( query, prometheus_url )
  logger.info( f'got data at ts {epoch_ts}: {value}' )

if __name__ == '__main__':
  cli( auto_envvar_prefix='STATUS_PUSHER' )
