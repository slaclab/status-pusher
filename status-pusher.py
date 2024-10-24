#!/usr/bin/env python3

import time
import timeit
import tempfile
import os
import datetime
import logging
from prometheus_pandas import query

INTERVAL = int(os.environ.get("STATUS_PUSHER_INTERVAL",300))
QUERY = os.environ.get("STATUS_PUSHER_QUERY", None)
TIME_RANGE = int(os.environ.get("STATUS_PUSHER_TIME_RANGE",300)) # TODO
PROMETHEUS_URL = os.environ.get("STATUS_PUSHER_PROMETHEUS_URL", 'http://prometheus:8086/')
GIT_URL = os.environ.get("STATUS_PUSHER_GIT_URL", 'http://github.com/org/repo/')
GIT_BRANCH = os.environ.get("STATUS_PUSHER_GIT_BRANCH", 'dev')

VERBOSE = bool(os.environ.get("STATUS_PUSHER_VERBOSE",False))

logging.basicConfig(level=logging.DEBUG if VERBOSE else logging.INFO)


def main():
  p = query.Prometheus( PROMETHEUS_URL )
  out = p.query( QUERY )
  logging.info( f'{out}' )

if __name__ == '__main__':
  main()
