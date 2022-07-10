#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Apply given operation schemes to the target process.
"""

import argparse
import os
import signal
import subprocess
import time

import _convert_damos
import _damon
import _damon_dbgfs
import _damo_paddr_layout

def cleanup_exit(orig_attrs, exit_code):
    if _damon.is_damon_running():
        if _damon.turn_damon('off'):
            print('failed to turn damon off!')
        while _damon.is_damon_running():
            time.sleep(1)
    if orig_attrs:
        if _damon.damon_interface() != 'debugfs':
            print('damo_schemes/cleanup_exit: ' +
                    'BUG: none-debugfs is in use but orig_attrs is not None')
        _damon_dbgfs.apply_debugfs_inputs(orig_attrs)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(orig_attrs, signum)

def set_argparser(parser):
    _damon.set_implicit_target_schemes_argparser(parser)

def main(args=None):
    global orig_attrs
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    err = _damon.initialize(args)
    if err != None:
        print(err)
        exit(1)
    scheme_version = _convert_damos.get_scheme_version()

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    if _damon.damon_interface() == 'debugfs':
        orig_attrs = _damon_dbgfs.current_debugfs_inputs()
    else:
        orig_attrs = None

    _damon.set_implicit_target_args_explicit(args)
    ctx = _damon.damon_ctx_from_damon_args(args)
    kdamonds = [_damon.Kdamond('0', [ctx])]
    _damon.apply_kdamonds(kdamonds)
    if _damon.turn_damon('on'):
        print('could not turn DAMON on')
        cleanup_exit(orig_attrs, -3)

    while not _damon.is_damon_running():
        time.sleep(1)

    print('Press Ctrl+C to stop')
    if args.self_started_target == True:
        os.waitpid(ctx.targets[0].pid, 0)
    while True:
        # damon will turn it off by itself if the target tasks are terminated.
        if not _damon.is_damon_running():
            break
        time.sleep(1)

    cleanup_exit(orig_attrs, 0)

if __name__ == '__main__':
    main()
