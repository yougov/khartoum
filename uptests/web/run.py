#!/usr/bin/env python
"""
This file contains 'uptests'.  Unlike unit and functional tests, uptests are
run on a production instance to ensure that it's ready to serve traffic.  They
shouldn't create/modify/delete any production data (or other state).

An uptests file may be in any language, should be executable, and should accept
two command line arguments for host and port.  If the program exits with status
0, the tests were successful.  Anything else is a failure and the instance
should be considered down.
"""

from __future__ import print_function

import sys
import random

import requests


def random_404(host, port, protocol='http'):
    file = ''.join([random.choice('abcdefghijklmnop') for x in range(20)])
    resp = requests.get('%(protocol)s://%(host)s:%(port)s/%(file)s' % locals())
    assert resp.status_code == 404


def main(host, port):
    # Pretty stupid and possibly dangerous test runner.  Look for all callables
    # in the current file except self, and call them with the host and port
    # passed in on the command line.
    g = globals()
    for i in g:
        if callable(g[i]) and i != 'main':
            g[i](host, port)
            print(i, 'passed')


if __name__ == '__main__':
    main(*sys.argv[1:])
