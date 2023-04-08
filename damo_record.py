#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Record monitored data access patterns.
"""

import os
import signal
import sys

import _damon
import _damon_args
import _damon_result

class DataForCleanup:
    kdamonds_names = None
    orig_kdamonds = None
    rfile_path = None
    rfile_format = None
    rfile_permission = None
    perf_pipe = None

data_for_cleanup = DataForCleanup()

def cleanup_exit(exit_code):
    if data_for_cleanup.kdamonds_names != None:
        # ignore returning error, as kdamonds may already finished
        _damon.turn_damon_off(data_for_cleanup.kdamonds_names)
        err = _damon.stage_kdamonds(data_for_cleanup.orig_kdamonds)
        if err:
            print('failed restoring previous kdamonds setup (%s)' % err)

    if exit_code in [-2, -3]:
        exit(exit_code)

    if data_for_cleanup.perf_pipe:
        _damon_result.stop_monitoring_record(data_for_cleanup.perf_pipe)
        exit(exit_code)

    if data_for_cleanup.rfile_format != 'record':
        err = _damon_result.update_result_file(data_for_cleanup.rfile_path,
                data_for_cleanup.rfile_format)
        if err != None:
            print('converting format from record to %s failed (%s)' %
                    (data_for_cleanup.rfile_format, err))
    os.chmod(data_for_cleanup.rfile_path, data_for_cleanup.rfile_permission)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_data_for_cleanup(data_for_cleanup, args, output_permission):
    data_for_cleanup.rfile_format = args.output_type
    data_for_cleanup.rfile_path = args.out
    data_for_cleanup.rfile_permission = output_permission
    data_for_cleanup.orig_kdamonds = _damon.current_kdamonds()

def chk_handle_record_feature_support(args):
    # Comment below line if --rbuf dependent user found
    return False

    damon_record_supported = _damon.feature_supported('record')
    if not damon_record_supported:
        if args.rbuf:
            print('# \'--rbuf\' will be ignored')

    if damon_record_supported or args.rbuf:
        sys.stderr.write('''
WARNING: --rbuf option and in-kernel record feature support is deprecated.
    The support will be removed by 2023-Q2.
    Please report your usecase to sj@kernel.org, damon@lists.linux.dev and
    linux-mm@kvack.org if you depend on those.
''')

    if not args.rbuf:
        args.rbuf = 1024 * 1024

    return damon_record_supported

def chk_handle_output_permission(output_permission_option):
    output_permission, err = _damon_result.parse_file_permission_str(
            output_permission_option)
    if err != None:
        print('wrong --output_permission (%s) (%s)' %
                (output_permission_option, err))
        exit(1)
    return output_permission

def backup_duplicate_output_file(output_file):
    if os.path.isfile(output_file):
        os.rename(output_file, output_file + '.old')

def set_argparser(parser):
    parser = _damon_args.set_argparser(parser, add_record_options=True)
    parser.add_argument('--output_type',
            choices=['record', 'perf_data', 'perf_script'],
            default='record', help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')
    parser.add_argument('--perf_path', type=str, default='perf',
            help='path of perf tool ')
    return parser

def main(args=None):
    global data_for_cleanup

    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    # Check/handle the arguments and options
    if _damon.any_kdamond_running() and not args.deducible_target:
        args.deducible_target = 'ongoing'
    damon_record_supported = chk_handle_record_feature_support(args)
    output_permission = chk_handle_output_permission(args.output_permission)
    backup_duplicate_output_file(args.out)

    err = _damon_result.set_perf_path(args.perf_path)
    if err != None:
        print(err)
        cleanup_exit(-3)

    # Setup for cleanup
    set_data_for_cleanup(data_for_cleanup, args, output_permission)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # Now the real works
    is_ongoing = _damon_args.is_ongoing_target(args)
    if not is_ongoing:
        err, kdamonds = _damon_args.turn_damon_on(args)
        if err:
            print('could not turn DAMON on (%s)' % err)
            cleanup_exit(-2)
        data_for_cleanup.kdamonds_names = [k.name for k in kdamonds]

    if not damon_record_supported or is_ongoing:
        data_for_cleanup.perf_pipe = _damon_result.start_monitoring_record(
                data_for_cleanup.rfile_path, data_for_cleanup.rfile_format,
                data_for_cleanup.rfile_permission)
    print('Press Ctrl+C to stop')

    if _damon_args.self_started_target(args):
        os.waitpid(kdamonds[0].contexts[0].targets[0].pid, 0)
    _damon.wait_current_kdamonds_turned_off()

    cleanup_exit(0)

if __name__ == '__main__':
    main()
