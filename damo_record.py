#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Record monitored data access patterns.
"""

import os
import signal
import subprocess
import sys

import _damon
import _damon_args
import _damon_result

class DataForCleanup:
    kdamonds_names = None
    target_is_ongoing = False
    orig_kdamonds = None
    rfile_path = None
    rfile_format = None
    rfile_permission = None
    perf_pipe = None

data_for_cleanup = DataForCleanup()

def cleanup_exit(exit_code):
    if not data_for_cleanup.target_is_ongoing:
        if _damon.any_kdamond_running():
            if data_for_cleanup.kdamonds_names == None:
                # turn on failed
                pass
            else:
                err = _damon.turn_damon_off(data_for_cleanup.kdamonds_names)
                if err:
                    print('failed to turn damon off (%s)' % err)
        err = _damon.apply_kdamonds(data_for_cleanup.orig_kdamonds)
        if err:
            print('failed restoring previous kdamonds setup (%s)' % err)

    if data_for_cleanup.perf_pipe:
        try:
            _damon.stop_monitoring_record(data_for_cleanup.perf_pipe)
        except:
            # perf might already finished
            pass

        rfile_current_format = 'perf_script'
        script_output = subprocess.check_output(
                ['perf', 'script', '-i', data_for_cleanup.rfile_path]).decode()
        with open(data_for_cleanup.rfile_path, 'w') as f:
            f.write(script_output)
    else:
        rfile_current_format = 'record'

    if rfile_current_format != data_for_cleanup.rfile_format:
        err = _damon_result.update_result_file(data_for_cleanup.rfile_path,
                data_for_cleanup.rfile_format,
                data_for_cleanup.rfile_permission)
        if err != None:
            print('setting format and permission failed (%s)' % err)

    if os.path.isfile(data_for_cleanup.rfile_path):
        os.chmod(data_for_cleanup.rfile_path,
                data_for_cleanup.rfile_permission)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def set_data_for_cleanup(data_for_cleanup, args, output_permission):
    data_for_cleanup.target_is_ongoing = _damon_args.is_ongoing_target(args)
    data_for_cleanup.rfile_format = args.output_type
    data_for_cleanup.rfile_path = args.out
    data_for_cleanup.rfile_permission = output_permission
    data_for_cleanup.orig_kdamonds = _damon.current_kdamonds()

def chk_handle_record_feature_support(args):
    damon_record_supported = _damon.feature_supported('record')
    if not damon_record_supported:
        if args.rbuf:
            print('# \'--rbuf\' will be ignored')

    if damon_record_supported or args.rbuf:
        sys.stderr.write('''
WARNING: --rbuf option and in-kernel record feature support will be deprecated
    by 2023-Q2.
    Please report your usecase to sj@kernel.org, damon@lists.linux.dev and
    linux-mm@kvack.org if you depend on those.
''')

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
    parser = _damon_args.set_argparser(parser, add_record_options=True)
    parser.add_argument('--output_type', choices=['record', 'perf_script'],
            default='perf_script', help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')
    return parser

def main(args=None):
    global data_for_cleanup

    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    # Check/handle the arguments and options
    damon_record_supported = chk_handle_record_feature_support(args)
    output_permission = chk_handle_output_permission(args.output_permission)
    backup_duplicate_output_file(args.out)

    # Setup for cleanup
    set_data_for_cleanup(data_for_cleanup, args, output_permission)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # Now the real works
    is_ongoing = _damon_args.is_ongoing_target(args)
    if not is_ongoing:
        # Turn DAMON on
        err, kdamonds = _damon_args.turn_damon_on(args)
        if err:
            print('could not turn DAMON on (%s)' % err)
            cleanup_exit(-2)
        data_for_cleanup.kdamonds_names = [k.name for k in kdamonds]

    if not damon_record_supported or is_ongoing:
        # Record the monitoring results using perf
        data_for_cleanup.perf_pipe, err = _damon.start_monitoring_record(
                data_for_cleanup.rfile_path)
        if err != None:
            print('could not start recording (%s)' % err)
            cleanup_exit(-3)
    print('Press Ctrl+C to stop')

    if _damon_args.self_started_target(args):
        os.waitpid(kdamonds[0].contexts[0].targets[0].pid, 0)
    _damon.wait_current_kdamonds_turned_off()

    cleanup_exit(0)

if __name__ == '__main__':
    main()
