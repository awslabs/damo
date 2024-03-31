# SPDX-License-Identifier: GPL-2.0

"""
Record monitored data access patterns.
"""

import json
import os
import signal
import subprocess
import time

import _damon
import _damon_args
import _damon_records

class DataForCleanup:
    kdamonds_idxs = None
    orig_kdamonds = None
    record_handle = None
    footprint_snapshots = None

data_for_cleanup = DataForCleanup()

cleaning = False

def save_mem_footprint(snapshots, filepath, file_permission):
    with open(filepath, 'w') as f:
        json.dump([s.to_kvpairs() for s in snapshots], f, indent=4)
    os.chmod(filepath, file_permission)

def cleanup_exit(exit_code):
    global cleaning
    if cleaning == True:
        return
    cleaning = True
    if data_for_cleanup.kdamonds_idxs != None:
        # ignore returning error, as kdamonds may already finished
        _damon.turn_damon_off(data_for_cleanup.kdamonds_idxs)
        err = _damon.stage_kdamonds(data_for_cleanup.orig_kdamonds)
        if err:
            print('failed restoring previous kdamonds setup (%s)' % err)

    if data_for_cleanup.record_handle:
        _damon_records.finish_recording(data_for_cleanup.record_handle)

        if data_for_cleanup.footprint_snapshots is not None:
            save_mem_footprint(
                    data_for_cleanup.footprint_snapshots, '%s.mem_footprint' %
                    data_for_cleanup.record_handle.file_path,
                    data_for_cleanup.record_handle.file_permission)

    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(signum)

def handle_args(args):
    if _damon.any_kdamond_running() and not args.deducible_target:
        args.deducible_target = 'ongoing'

    args.output_permission, err = _damon_records.parse_file_permission_str(
            args.output_permission)
    if err != None:
        print('wrong --output permission (%s) (%s)' %
                (args.output_permission, err))
        exit(1)

    # backup duplicate output file
    if os.path.isfile(args.out):
        os.rename(args.out, args.out + '.old')

    if args.footprint is True:
        footprint_file_path = '%s.mem_footprint' % args.out
        if os.path.isfile(footprint_file_path):
            os.rename(footprint_file_path, footprint_file_path + '.old')

    err = _damon_records.set_perf_path(args.perf_path)
    if err != None:
        print(err)
        exit(-3)

def pid_running(pid):
    '''pid should be string'''
    try:
        subprocess.check_output(['ps', '--pid', pid])
        return True
    except:
        return False

def all_targets_terminated(targets):
    for target in targets:
        if pid_running('%s' % target.pid):
            return False
    return True

def poll_target_pids(kdamonds, add_childs):
    '''Return if polling should continued'''
    current_targets = kdamonds[0].contexts[0].targets
    if all_targets_terminated(current_targets):
        return False
    if not add_childs:
        return True

    for target in current_targets:
        if target.pid == None:
            continue
        try:
            childs_pids = subprocess.check_output(
                    ['ps', '--ppid', '%s' % target.pid, '-o', 'pid=']
                    ).decode().split()
        except:
            childs_pids = []
        if len(childs_pids) == 0:
            continue

        # TODO: Commit all at once, out of this loop
        new_targets = []
        for child_pid in childs_pids:
            # skip the child if already in the targets
            if child_pid in ['%s' % t.pid for t in current_targets]:
                continue
            # remove already terminated targets, since committing already
            # terminated targets to DAMON fails
            new_targets = [target for target in current_targets
                    if pid_running('%s' % target.pid)]
            new_targets.append(_damon.DamonTarget(pid=child_pid, regions=[]))
        if new_targets == []:
            continue

        # commit the new set of targets
        kdamonds[0].contexts[0].targets = new_targets
        err = _damon.commit(kdamonds)
        if err != None:
            # this might be not a problem; some of processes might
            # finished meanwhile
            print('adding child as target failed (%s)' % err)
            cleanup_exit(1)
    return True

# Meaning of the fileds of MemFootprint are as below.
#
# ======== ===============================       ==============================
# Field    Content
# ======== ===============================       ==============================
# size     total program size (pages)            (same as VmSize in status)
# resident size of memory portions (pages)       (same as VmRSS in status)
# shared   number of pages that are shared       (i.e. backed by a file, same
#                                                as RssFile+RssShmem in status)
# trs      number of pages that are 'code'       (not including libs; broken,
#                                                includes data segment)
# lrs      number of pages of library            (always 0 on 2.6)
# drs      number of pages of data/stack         (including libs; broken,
#                                                includes library text)
# dt       number of dirty pages                 (always 0 on 2.6)
# ======== ===============================       ==============================
#
# The above table is tolen from Documentation/filesystems/proc.rst file of
# Linux
class MemFootprint:
    size = None
    resident = None
    shared = None
    trs = None
    lrs = None
    drs = None
    dt = None

    def __init__(self, pid):
        with open('/proc/%s/statm' % pid, 'r') as f:
            fields = [int(x) for x in f.read().split()]
        self.size = fields[0]
        self.resident = fields[1]
        self.shared = fields[2]
        self.trs = fields[3]
        self.lrs = fields[4]
        self.drs = fields[5]
        self.dt = fields[6]

    def to_kvpairs(self):
        return self.__dict__

class MemFootprintsSnapshot:
    time = None
    footprints = None

    def __init__(self, pids):
        self.time = time.time()
        self.footprints = {}
        for pid in pids:
            self.footprints[pid] = MemFootprint(pid)

    def to_kvpairs(self):
        footprints = []
        for pid, fp in self.footprints.items():
            footprints.append({'pid': pid, 'footprint': fp.to_kvpairs()})
        return {'time': self.time, 'footprints': footprints}

def record_mem_footprint(kdamonds, snapshots):
    pids = []
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for target in ctx.targets:
                if target.pid is None:
                    continue
                pids.append(target.pid)
    snapshots.append(MemFootprintsSnapshot(pids))

def main(args):
    global data_for_cleanup

    is_ongoing = _damon_args.is_ongoing_target(args)
    _damon.ensure_root_and_initialized(args,
            load_feature_supports=is_ongoing,
            save_feature_supports=not is_ongoing)

    handle_args(args)

    # Setup for cleanup
    data_for_cleanup.orig_kdamonds = _damon.current_kdamonds()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # Now the real works
    if not is_ongoing:
        err, kdamonds = _damon_args.turn_damon_on(args)
        if err:
            print('could not turn DAMON on (%s)' % err)
            cleanup_exit(-2)
        data_for_cleanup.kdamonds_idxs = ['%d' % idx
                for idx, k in enumerate(kdamonds)]
        # TODO: Support multiple kdamonds, multiple contexts
        monitoring_intervals = kdamonds[0].contexts[0].intervals
    else:
        if not _damon.any_kdamond_running():
            print('DAMON is not turned on')
            exit(1)

        # TODO: Support multiple kdamonds, multiple contexts
        monitoring_intervals = data_for_cleanup.orig_kdamonds[
                0].contexts[0].intervals

    if args.schemes_target_regions == False:
        tracepoint = _damon_records.perf_event_damon_aggregated
    else:
        tracepoint = _damon_records.perf_event_damos_before_apply

    data_for_cleanup.record_handle = _damon_records.start_recording(
            tracepoint, args.out, args.output_type, args.output_permission,
            monitoring_intervals,
            profile=args.profile is True, profile_target_pid=None)
    if args.footprint is True:
        footprint_snapshots = []
        data_for_cleanup.footprint_snapshots = footprint_snapshots
    print('Press Ctrl+C to stop')

    if _damon_args.self_started_target(args):
        while poll_target_pids(kdamonds, args.include_child_tasks):
            if args.footprint:
                record_mem_footprint(kdamonds, footprint_snapshots)
            time.sleep(1)

    _damon.wait_kdamonds_turned_off()

    cleanup_exit(0)

def set_argparser(parser):
    parser = _damon_args.set_argparser(parser, add_record_options=True)
    parser.add_argument('--output_type',
                        choices=_damon_records.file_types,
                        default=_damon_records.file_type_json_compressed,
                        help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
                        help='permission of the output file')
    parser.add_argument('--perf_path', type=str, default='perf',
                        help='path of perf tool ')
    parser.add_argument('--include_child_tasks', action='store_true',
                        help='record accesses of child processes')
    parser.add_argument('--schemes_target_regions', action='store_true',
                        help='record schemes tried to be applied regions')
    parser.add_argument('--profile', action='store_true',
                        help='record profiling information together')
    parser.add_argument('--footprint', action='store_true',
                        help='record memory footprint')
    parser.description = 'Record monitoring results'
    return parser
