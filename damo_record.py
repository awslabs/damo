# SPDX-License-Identifier: GPL-2.0

"""
Record monitored data access patterns.
"""

import os
import signal
import subprocess
import time

import _damon
import _damon_args
import _damon_result

class DataForCleanup:
    kdamonds_idxs = None
    orig_kdamonds = None
    perf_pipe = None

data_for_cleanup = DataForCleanup()

def cleanup_exit(exit_code):
    if data_for_cleanup.kdamonds_idxs != None:
        # ignore returning error, as kdamonds may already finished
        _damon.turn_damon_off(data_for_cleanup.kdamonds_idxs)
        err = _damon.stage_kdamonds(data_for_cleanup.orig_kdamonds)
        if err:
            print('failed restoring previous kdamonds setup (%s)' % err)

    if data_for_cleanup.perf_pipe:
        _damon_result.stop_monitoring_record(data_for_cleanup.perf_pipe)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def handle_args(args):
    if _damon.any_kdamond_running() and not args.deducible_target:
        args.deducible_target = 'ongoing'

    args.output_permission, err = _damon_result.parse_file_permission_str(
            args.output_permission)
    if err != None:
        print('wrong --output permission (%s) (%s)' %
                (args.output_permission, err))
        exit(1)

    # backup duplicate output file
    if os.path.isfile(args.out):
        os.rename(args.out, args.out + '.old')

    err = _damon_result.set_perf_path(args.perf_path)
    if err != None:
        print(err)
        exit(-3)

def poll_add_childs(kdamonds):
    while True:
        pid = '%s' % kdamonds[0].contexts[0].targets[0].pid
        try:
            subprocess.check_output(['ps', '--pid', pid])
            alive = True
        except Exception as e:
            print(e)
            alive = False
        if not alive:
            break

        targets = kdamonds[0].contexts[0].targets
        for target in targets:
            if target.pid == None:
                continue
            pid = '%s' % target.pid
            try:
                childs_pids = subprocess.check_output(
                        ['ps', '--ppid', pid, '-o', 'pid=']).decode().split()
            except:
                childs_pids = []
            if len(childs_pids) == 0:
                break
            need_commit = False
            for child_pid in childs_pids:
                if child_pid in ['%s' % t.pid for t in targets]:
                    continue
                targets.append(_damon.DamonTarget(pid=child_pid, regions=[]))
                need_commit = True
            if need_commit:
                err = _damon.commit(kdamonds)
                if err != None:
                    print('adding child as target failed (%s)' % err)
                    cleanup_exit(1)
        time.sleep(1)

def set_argparser(parser):
    parser = _damon_args.set_argparser(parser, add_record_options=True)
    parser.add_argument('--output_type',
            choices=_damon_result.file_types,
            default=_damon_result.file_type_json_compressed,
            help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')
    parser.add_argument('--perf_path', type=str, default='perf',
            help='path of perf tool ')
#    parser.add_argument('--include_childs', action='store_true',
#            help='record accesses of child processes')
    return parser

def main(args=None):
    global data_for_cleanup

    if not args:
        parser = set_argparser(None)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    handle_args(args)

    # Setup for cleanup
    data_for_cleanup.orig_kdamonds = _damon.current_kdamonds()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # Now the real works
    is_ongoing = _damon_args.is_ongoing_target(args)
    if not is_ongoing:
        err, kdamonds = _damon_args.turn_damon_on(args)
        if err:
            print('could not turn DAMON on (%s)' % err)
            cleanup_exit(-2)
        data_for_cleanup.kdamonds_idxs = ['%d' % idx
                for idx, k in enumerate(kdamonds)]

    data_for_cleanup.perf_pipe = _damon_result.start_monitoring_record(
            args.out, args.output_type, args.output_permission)
    print('Press Ctrl+C to stop')

    if _damon_args.self_started_target(args):
        if not args.include_childs:
            os.waitpid(kdamonds[0].contexts[0].targets[0].pid, 0)
        else:
            poll_add_childs(kdamonds)

    _damon.wait_current_kdamonds_turned_off()

    cleanup_exit(0)

if __name__ == '__main__':
    main()
