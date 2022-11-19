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

import _damon
import _damon_args
import _damo_paddr_layout

def cleanup_exit(exit_code):
    kdamonds_names_to_turn_off = []
    if kdamonds_names != None:
        for kdamond_name in kdamonds_names:
            if _damon.is_kdamond_running(kdamond_name):
                kdamonds_names_to_turn_off.append(kdamond_name)
    if _damon.turn_damon('off', kdamonds_names_to_turn_off):
        print('failed to turn damon off!')
    _damon.apply_kdamonds(orig_kdamonds)
    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_argparser(parser):
    _damon_args.set_implicit_target_schemes_argparser(parser)

def main(args=None):
    global orig_kdamonds
    global kdamonds_names

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    orig_kdamonds = _damon.current_kdamonds()
    kdamonds_names = None

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    err, kdamonds = _damon_args.turn_implicit_args_damon_on(args,
            record_request=None)
    if err:
        print('could not turn DAMON on')
        cleanup_exit(-3)

    kdamonds_names = [k.name for k in kdamonds]

    print('Press Ctrl+C to stop')
    if args.self_started_target == True:
        os.waitpid(kdamonds[0].contexts[0].targets[0].pid, 0)
    # damon will turn it off by itself if the target tasks are terminated.
    _damon.wait_current_kdamonds_turned('off')

    cleanup_exit(0)

if __name__ == '__main__':
    main()
