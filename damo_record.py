#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Record monitored data access patterns.
"""

import argparse
import os
import signal
import subprocess
import time

import _damon
import _damon_result
import _damo_paddr_layout

class DataForCleanup:
    target_is_ongoing = False
    orig_attrs = None
    rfile_path = None
    rfile_format = None
    rfile_permission = None
    remove_perf_data = False
    perf_pipe = None

data_for_cleanup = DataForCleanup()

def change_rfile_format(rfile_path, src_format, dst_format, dst_permission):
    rfile_path_mid = rfile_path + '.mid'
    os.rename(rfile_path, rfile_path_mid)
    result = _damon_result.parse_damon_result(rfile_path_mid, src_format)
    _damon_result.write_damon_result(result, rfile_path, dst_format,
            dst_permission)
    os.remove(rfile_path_mid)

def cleanup_exit(exit_code):
    if data_for_cleanup.perf_pipe:
        data_for_cleanup.perf_pipe.send_signal(signal.SIGINT)
        data_for_cleanup.perf_pipe.wait()

        rfile_current_format = 'perf_script'
        perf_data = data_for_cleanup.rfile_path + '.perf.data'
        subprocess.call('perf script -i \'%s\' > \'%s\'' %
                (perf_data, data_for_cleanup.rfile_path),
                shell=True, executable='/bin/bash')
        if data_for_cleanup.remove_perf_data:
            os.remove(perf_data)
    else:
        rfile_current_format = 'record'

    if not data_for_cleanup.target_is_ongoing:
        if _damon.is_damon_running():
            if _damon.turn_damon('off'):
                print('failed to turn damon off!')
        _damon.restore_attrs(data_for_cleanup.orig_attrs)

    if (data_for_cleanup.rfile_format != None and
            rfile_current_format != data_for_cleanup.rfile_format):
        change_rfile_format(data_for_cleanup.rfile_path, rfile_current_format,
                data_for_cleanup.rfile_format,
                data_for_cleanup.rfile_permission)

    os.chmod(data_for_cleanup.rfile_path, data_for_cleanup.rfile_permission)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_data_for_cleanup(data_for_cleanup, args, output_permission):
    data_for_cleanup.target_is_ongoing = _damon.is_ongoing_target(args)
    data_for_cleanup.rfile_format = args.output_type
    data_for_cleanup.rfile_path = args.out
    data_for_cleanup.remove_perf_data = not args.leave_perf_data
    data_for_cleanup.rfile_permission = output_permission
    data_for_cleanup.orig_attrs = _damon.attrs_to_restore()

def chk_handle_record_feature_support(args):
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

    return damon_record_supported

def chk_handle_output_permission(output_permission_option):
    output_permission = int(output_permission_option, 8)
    if output_permission < 0o0 or output_permission > 0o777:
        print('wrong --output_permission (%s)' % output_permission_option)
        exit(1)
    return output_permission

def backup_duplicate_output_file(output_file):
    if os.path.isfile(output_file):
        os.rename(output_file, output_file + '.old')

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
    global data_for_cleanup

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Check system requirements
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, _damon.is_ongoing_target(args))

    # Check/handle the arguments and options
    damon_record_supported = chk_handle_record_feature_support(args)
    output_permission = chk_handle_output_permission(args.output_permission)
    backup_duplicate_output_file(args.out)

    # Setup for cleanup
    set_data_for_cleanup(data_for_cleanup, args, output_permission)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # Now the real works
    if not _damon.is_ongoing_target(args):
        # Turn DAMON on
        err, ctx = _damon.turn_implicit_args_damon_on(args,
                record_request=_damon.DamonRecord(args.rbuf, args.out))
        if err:
            print('could not turn DAMON on')
            cleanup_exit(-2)

    if not damon_record_supported:
        # Record the monitoring results using perf
        data_for_cleanup.perf_pipe = subprocess.Popen([
            'perf', 'record', '-a', '-e', 'damon:damon_aggregated',
            '-o', data_for_cleanup.rfile_path + '.perf.data'])
    print('Press Ctrl+C to stop')

    if not _damon.is_ongoing_target(args) and args.self_started_target == True:
        os.waitpid(ctx.targets[0].pid, 0)
    while _damon.is_damon_running():
        time.sleep(1)

    cleanup_exit(0)

if __name__ == '__main__':
    main()
