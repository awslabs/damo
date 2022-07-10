#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Record data access patterns of the target process.
"""

import argparse
import os
import signal
import subprocess
import time

import _damon
import _damon_dbgfs
import _damon_result
import _damo_paddr_layout

perf_pipe = None
rfile_path = None
rfile_format = None
target_is_ongoing = False

remove_perf_data = False
rfile_permission = None
def cleanup_exit(orig_attrs, exit_code):
    rfile_mid_format = 'record'
    if perf_pipe:
        perf_data = rfile_path + '.perf.data'
        perf_pipe.send_signal(signal.SIGINT)
        perf_pipe.wait()
        subprocess.call('perf script -i \'%s\' > \'%s\'' %
                (perf_data, rfile_path),
                shell=True, executable='/bin/bash')
        rfile_mid_format = 'perf_script'

        if remove_perf_data:
            os.remove(perf_data)

    if not target_is_ongoing and _damon.is_damon_running():
        if _damon.turn_damon('off'):
            print('failed to turn damon off!')
        while _damon.is_damon_running():
            time.sleep(1)
    if not target_is_ongoing and orig_attrs:
        if _damon.damon_interface() != 'debugfs':
            print('damo_record/cleanup_exit: ' +
                    'BUG: none-debugfs is in use but orig_attrs is not None')
        _damon_dbgfs.apply_debugfs_inputs(orig_attrs)

    if rfile_format != None and rfile_mid_format != rfile_format:
        rfile_path_mid = rfile_path + '.mid'
        os.rename(rfile_path, rfile_path_mid)
        result = _damon_result.parse_damon_result(rfile_path_mid,
                rfile_mid_format)
        _damon_result.write_damon_result(result, rfile_path, rfile_format,
                rfile_permission)
        os.remove(rfile_path_mid)

    os.chmod(rfile_path, rfile_permission)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(orig_attrs, signum)

def set_argparser(parser):
    _damon.set_implicit_target_monitoring_argparser(parser)
    parser.add_argument('-l', '--rbuf', metavar='<len>', type=int,
            help='length of record result buffer')
    parser.add_argument('-o', '--out', metavar='<file path>', type=str,
            default='damon.data', help='output file path')
    parser.add_argument('--output_type', choices=['record', 'perf_script'],
            default=None, help='output file\'s type')
    parser.add_argument('--leave_perf_data', action='store_true',
            default=False, help='don\'t remove the perf.data file')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')

def main(args=None):
    global orig_attrs
    global rfile_format
    global rfile_path
    global rfile_permission
    global remove_perf_data
    global perf_pipe
    global target_is_ongoing

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    target_is_ongoing = args.target == 'ongoing'
    if target_is_ongoing:
        skip_dirs_population = True
    else:
        skip_dirs_population = False
    err = _damon.initialize(args, skip_dirs_population)
    if err != None:
        print(err)
        exit(1)

    damon_record_supported = _damon.feature_supported('record')

    if not damon_record_supported:
        try:
            subprocess.check_output(['which', 'perf'])
        except:
            print('perf is not installed')
            exit(1)

        if args.rbuf:
            print('# \'--rbuf\' will be ignored')
    if not args.rbuf:
        args.rbuf = 1024 * 1024

    rfile_format = args.output_type
    remove_perf_data = not args.leave_perf_data
    rfile_permission = int(args.output_permission, 8)
    if rfile_permission < 0o0 or rfile_permission > 0o777:
        print('wrong --output_permission (%s)' % rfile_permission)
        exit(1)

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    if _damon.damon_interface() == 'debugfs':
        orig_attrs = _damon_dbgfs.current_debugfs_inputs()
    else:
        orig_attrs = None

    if not target_is_ongoing:
        _damon.set_implicit_target_args_explicit(args)
        ctx = _damon.damon_ctx_from_damon_args(args)
        if damon_record_supported:
            ctx.set_record(args.rbuf, args.out)
        kdamonds = [_damon.Kdamond('0', [ctx])]
        _damon.apply_kdamonds(kdamonds)

    rfile_path = args.out
    if os.path.isfile(rfile_path):
        os.rename(rfile_path, rfile_path + '.old')

    if not target_is_ongoing:
        if _damon.turn_damon('on'):
            print('could not turn DAMON on')
            cleanup_exit(orig_attrs, -2)

        while not _damon.is_damon_running():
            time.sleep(1)

    if not damon_record_supported:
        perf_pipe = subprocess.Popen(['perf', 'record', '-a',
            '-e', 'damon:damon_aggregated', '-o', rfile_path + '.perf.data'])
    print('Press Ctrl+C to stop')

    if args.self_started_target == True:
        os.waitpid(ctx.targets[0].pid, 0)
    while _damon.is_damon_running():
        time.sleep(1)

    cleanup_exit(orig_attrs, 0)

if __name__ == '__main__':
    main()
