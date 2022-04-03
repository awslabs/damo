#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Record data access patterns of the target process.
"""

import argparse
import datetime
import os
import signal
import subprocess
import time

import _damon
import _damon_result
import _damo_paddr_layout

perf_pipe = None
rfile_path = None
rfile_format = None
def do_record(target, is_target_cmd, target_ids_prefix, init_regions, attrs,
        old_attrs):
    global perf_pipe
    global rfile_path

    rfile_path = attrs.rfile_path

    if os.path.isfile(attrs.rfile_path):
        os.rename(attrs.rfile_path, attrs.rfile_path + '.old')

    if attrs.apply():
        print('attributes (%s) failed to be applied' % attrs)
        cleanup_exit(old_attrs, -1)
    print('# damon attrs: %s' % attrs)
    if is_target_cmd:
        p = subprocess.Popen(target, shell=True, executable='/bin/bash')
        target = p.pid

    target_ids_input = '%s %s' % (target_ids_prefix, target)
    if _damon.set_target(target_ids_input.strip(), init_regions):
        print('target setting (%s, %s) failed' % (target, init_regions))
        cleanup_exit(old_attrs, -2)
    if _damon.turn_damon('on'):
        print('could not turn on damon' % target)
        cleanup_exit(old_attrs, -3)
    while not _damon.is_damon_running():
        time.sleep(1)

    if not _damon.feature_supported('record'):
        perf_pipe = subprocess.Popen(
                'perf record -e damon:damon_aggregated -a -o \'%s\'' %
                (attrs.rfile_path + '.perf.data'),
                shell=True, executable='/bin/bash')
    print('Press Ctrl+C to stop')

    wait_start = datetime.datetime.now()
    if is_target_cmd:
        p.wait()
    while True:
        if not _damon.is_damon_running():
            break
        time.sleep(1)

    cleanup_exit(old_attrs, 0)

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

    if _damon.is_damon_running():
        if _damon.turn_damon('off'):
            print('failed to turn damon off!')
        while _damon.is_damon_running():
            time.sleep(1)
    if orig_attrs:
        if orig_attrs.apply():
            print('original attributes (%s) restoration failed!' % orig_attrs)

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
    _damon.set_argparser(parser)
    parser.add_argument('target', type=str, metavar='<target>',
            help='the target command or the pid to record')
    parser.add_argument('--target_ids_prefix', type=str, metavar='<prefix>',
            default='', help='prefix for the target_ids input')
    parser.add_argument('-l', '--rbuf', metavar='<len>', type=int,
            help='length of record result buffer')
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='if target is \'paddr\', limit it to the numa node')
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
    global rfile_permission
    global remove_perf_data

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    err = _damon.initialize(args)
    if err != None:
        print(err)
        exit(1)

    if not _damon.feature_supported('record'):
        try:
            subprocess.check_output(['which', 'perf'])
        except:
            print('perf is not installed')
            exit(1)

    if args.rbuf and not _damon.feature_supported('record'):
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
    orig_attrs = _damon.current_attrs()

    new_attrs = _damon.cmd_args_to_attrs(args)
    init_regions = _damon.cmd_args_to_init_regions(args)
    numa_node = args.numa_node
    target = args.target

    if target == 'paddr':   # physical memory address space
        cmd_target = False
        if not init_regions:
            if numa_node != None:
                init_regions = _damo_paddr_layout.paddr_region_of(numa_node)
            else:
                init_regions = [_damo_paddr_layout.default_paddr_region()]
    elif not subprocess.call('which %s &> /dev/null' % target.split()[0],
            shell=True, executable='/bin/bash'):
        cmd_target = True
    else:
        try:
            pid = int(target)
        except:
            print('target \'%s\' is not supported' % target)
            exit(1)
        cmd_target = False
    do_record(target, cmd_target, args.target_ids_prefix, init_regions,
            new_attrs, orig_attrs)

if __name__ == '__main__':
    main()
