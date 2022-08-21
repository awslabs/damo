#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Apply given operation schemes.
"""

import argparse
import os
import signal
import subprocess
import time

import _convert_damos
import _damon
import _damo_paddr_layout

def cleanup_exit(exit_code):
    if _damon.is_damon_running():
        if _damon.turn_damon('off'):
            print('failed to turn damon off!')
    _damon.restore_attrs(orig_attrs)
    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_argparser(parser):
    _damon.set_implicit_target_schemes_argparser(parser)

def main(args=None):
    global orig_attrs
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, False)

    orig_attrs = _damon.attrs_to_restore()

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    err, ctx = _damon.turn_implicit_args_damon_on(args, record_request=None)
    if err:
        print('could not turn DAMON on')
        cleanup_exit(-3)

    print('Press Ctrl+C to stop')
    if args.self_started_target == True:
        os.waitpid(ctx.targets[0].pid, 0)
    # damon will turn it off by itself if the target tasks are terminated.
    while _damon.is_damon_running():
        time.sleep(1)

    cleanup_exit(0)

if __name__ == '__main__':
    main()
