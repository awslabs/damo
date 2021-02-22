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
import _paddr_layout

def pidfd_open(pid):
    import ctypes
    libc = ctypes.CDLL(None)
    syscall = libc.syscall
    syscall.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    syscall.restype = ctypes.c_long

    NR_pidfd_open = 434

    return syscall(NR_pidfd_open, pid, 0)

def do_record(target, is_target_cmd, init_regions, attrs, old_attrs, pidfd):
    if os.path.isfile(attrs.rfile_path):
        os.rename(attrs.rfile_path, attrs.rfile_path + '.old')

    if attrs.apply():
        print('attributes (%s) failed to be applied' % attrs)
        cleanup_exit(old_attrs, -1)
    print('# damon attrs: %s %s' % (attrs.attr_str(), attrs.record_str()))
    if is_target_cmd:
        p = subprocess.Popen(target, shell=True, executable='/bin/bash')
        target = p.pid

    if pidfd:
        fd = pidfd_open(int(target))
        if fd < 0:
            print('failed getting pidfd of %s: %s' % (target, fd))
            cleanup_exit(old_attrs, -1)

        # NOTE: The race is still possible because the pid might be already
        # reused before above pidfd_open() returned.  Eliminating the race is
        # impossible unless we drop the pid support.  This option handling is
        # only for reference of the pidfd usage.
        target = 'pidfd %s' % fd

    if _damon.set_target(target, init_regions):
        print('target setting (%s, %s) failed' % (target, init_regions))
        cleanup_exit(old_attrs, -2)
    if _damon.turn_damon('on'):
        print('could not turn on damon' % target)
        cleanup_exit(old_attrs, -3)
    while not _damon.is_damon_running():
        time.sleep(1)
    print('Press Ctrl+C to stop')
    if is_target_cmd:
        p.wait()
    while True:
        # damon will turn it off by itself if the target tasks are terminated.
        if not _damon.is_damon_running():
            break
        time.sleep(1)

    if pidfd:
        os.close(fd)
    cleanup_exit(old_attrs, 0)

def cleanup_exit(orig_attrs, exit_code):
    if _damon.is_damon_running():
        if _damon.turn_damon('off'):
            print('failed to turn damon off!')
        while _damon.is_damon_running():
            time.sleep(1)
    if orig_attrs:
        if orig_attrs.apply():
            print('original attributes (%s) restoration failed!' % orig_attrs)
    exit(exit_code)

def sighandler(signum, frame):
    print('\nsignal %s received' % signum)
    cleanup_exit(orig_attrs, signum)

def chk_permission():
    if os.geteuid() != 0:
        print("Run as root")
        exit(1)

def set_argparser(parser):
    _damon.set_attrs_argparser(parser)
    _damon.set_init_regions_argparser(parser)
    parser.add_argument('target', type=str, metavar='<target>',
            help='the target command or the pid to record')
    parser.add_argument('--pidfd', action='store_true',
            help='use pidfd type target id')
    parser.add_argument('-l', '--rbuf', metavar='<len>', type=int,
            default=1024*1024, help='length of record result buffer')
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='if target is \'paddr\', limit it to the numa node')
    parser.add_argument('-o', '--out', metavar='<file path>', type=str,
            default='damon.data', help='output file path')

def default_paddr_region():
    "Largest System RAM region becomes the default"
    ret = []
    with open('/proc/iomem', 'r') as f:
        # example of the line: '100000000-42b201fff : System RAM'
        for line in f:
            fields = line.split(':')
            if len(fields) != 2:
                continue
            name = fields[1].strip()
            if name != 'System RAM':
                continue
            addrs = fields[0].split('-')
            if len(addrs) != 2:
                continue
            start = int(addrs[0], 16)
            end = int(addrs[1], 16)

            sz_region = end - start
            if not ret or sz_region > (ret[1] - ret[0]):
                ret = [start, end]
    return ret

def paddr_region_of(numa_node):
    regions = []
    paddr_ranges = _paddr_layout.paddr_ranges()
    for r in paddr_ranges:
        if r.nid == numa_node and r.name == 'System RAM':
            regions.append([r.start, r.end])

    return regions

def main(args=None):
    global orig_attrs
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    chk_permission()
    _damon.chk_update_debugfs(args.debugfs)

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    orig_attrs = _damon.current_attrs()

    args.schemes = ''
    pidfd = args.pidfd
    new_attrs = _damon.cmd_args_to_attrs(args)
    init_regions = _damon.cmd_args_to_init_regions(args)
    numa_node = args.numa_node
    target = args.target

    target_fields = target.split()
    if target == 'paddr':   # physical memory address space
        if not init_regions:
            if numa_node:
                init_regions = paddr_region_of(numa_node)
            else:
                init_regions = [default_paddr_region()]
        do_record(target, False, init_regions, new_attrs, orig_attrs, pidfd)
    elif not subprocess.call('which %s &> /dev/null' % target_fields[0],
            shell=True, executable='/bin/bash'):
        do_record(target, True, init_regions, new_attrs, orig_attrs, pidfd)
    else:
        try:
            pid = int(target)
        except:
            print('target \'%s\' is neither a command, nor a pid' % target)
            exit(1)
        do_record(target, False, init_regions, new_attrs, orig_attrs, pidfd)

if __name__ == '__main__':
    main()
