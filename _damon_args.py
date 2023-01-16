#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Command line arguments handling
"""

import json
import subprocess

import _damo_schemes_input
import _damo_paddr_layout
import _damon

# Kdamonds construction from command line arguments

def damos_from_args(args):
    schemes = []
    if not 'schemes' in args or args.schemes == None:
        return schemes, None

    schemes, err = _damo_schemes_input.damo_schemes_to_damos(args.schemes)
    if err:
        return None, 'failed damo schemes arguents parsing (%s)' % err
    return schemes, None

def init_regions_from_damon_args(args):
    init_regions = []
    if args.regions:
        for region in args.regions.split():
            addrs = region.split('-')
            try:
                if len(addrs) != 2:
                    raise Exception ('two addresses not given')
                region = _damon.DamonRegion(addrs[0], addrs[1])
                if region.start >= region.end:
                    raise Exception('start >= end')
                if init_regions and init_regions[-1].end > region.start:
                    raise Exception('regions overlap')
            except Exception as e:
                return None, 'Wrong \'--regions\' argument (%s)' % e
            init_regions.append(region)

    if args.ops == 'paddr' and not init_regions:
        if args.numa_node != None:
            init_regions = _damo_paddr_layout.paddr_region_of(args.numa_node)
        else:
            init_regions = [_damo_paddr_layout.default_paddr_region()]
        try:
            init_regions = [_damon.DamonRegion(r[0], r[1])
                    for r in init_regions]
        except Exception as e:
            return None, 'Wrong \'--regions\' argument (%s)' % e

    return init_regions, None

def damon_ctx_from_damon_args(args):
    try:
        intervals = _damon.DamonIntervals(args.sample, args.aggr, args.updr)
    except Exception as e:
        return None, 'invalid intervals arguments (%s)' % e
    try:
        nr_regions = _damon.DamonNrRegionsRange(args.minr, args.maxr)
    except Exception as e:
        return None, 'invalid nr_regions arguments (%s)' % e
    ops = args.ops
    if not _damon.feature_supported(ops):
        return None, '%s unsupported' % ops

    init_regions, err = init_regions_from_damon_args(args)
    if err:
        return None, err

    try:
        target = _damon.DamonTarget('0', args.target_pid
                if _damon.target_has_pid(ops) else None, init_regions)
    except Exception as e:
        return 'Wrong \'--target_pid\' argument (%s)' % e

    record_request = None
    if _damon.feature_supported('record') and 'rbuf' in args:
        try:
            record_request = _damon.DamonRecord(args.rbuf, args.out)
        except Exception as e:
            return 'Wrong record arguments (%s)' % e

    schemes, err = damos_from_args(args)
    if err:
        return err

    try:
        ctx = _damon.DamonCtx('0', intervals, nr_regions, ops, [target],
                schemes, record_request)
        return ctx, None
    except Exception as e:
        return None, 'Creating context from arguments failed (%s)' % e

def uncomment_kvpairs_str(string):
    lines = []
    for line in string.split('\n'):
        if line.strip().startswith('#'):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()

def kdamonds_from_damon_args(args):
    if args.kdamonds:
        if os.path.isfile(args.kdamonds):
            with open(args.kdamonds, 'r') as f:
                kdamonds_str = f.read()
        else:
            kdamonds_str = args.kdamonds
        kdamonds_kvpairs = json.loads(uncomment_kvpairs_str(kdamonds_str))
        return [kvpairs_to_Kdamond(kvpair)
                for kvpair in kdamonds_kvpairs], None
    ctx, err = damon_ctx_from_damon_args(args)
    if err:
        return None, err
    return [_damon.Kdamond(name='0', state=None, pid=None,
        contexts=[ctx])], None

def set_implicit_target_args_explicit(args):
    args.kdamonds = None
    args.self_started_target = False
    if args.target == 'paddr':
        args.ops = 'paddr'
        args.target_pid = None
        return None
    if not subprocess.call('which %s &> /dev/null' % args.target.split()[0],
            shell=True, executable='/bin/bash'):
        p = subprocess.Popen(args.target, shell=True, executable='/bin/bash')
        args.ops = 'vaddr'
        args.target_pid = p.pid
        args.self_started_target = True
        if args.regions and _damon.feature_supported('fvaddr'):
            args.ops = 'fvaddr'
        return None
    try:
        pid = int(args.target)
    except:
        return 'target \'%s\' is not supported' % args.target
    args.ops = 'vaddr'
    args.target_pid = pid
    if args.regions and _damon.feature_supported('fvaddr'):
        args.ops = 'fvaddr'

    return None

# Command line processing helpers

def is_ongoing_target(args):
    return args.target == 'ongoing'

def apply_explicit_args_damon(args):
    kdamonds, err = kdamonds_from_damon_args(args)
    if err:
        return None, 'cannot create kdamonds from args'
    err = _damon.apply_kdamonds(kdamonds)
    if err:
        return None, err
    return kdamonds, None

def turn_explicit_args_damon_on(args):
    kdamonds, err = apply_explicit_args_damon(args)
    if err:
        return err, None
    return _damon.turn_damon_on(
            [k.name for k in kdamonds]), kdamonds

def turn_implicit_args_damon_on(args):
    err = set_implicit_target_args_explicit(args)
    if err:
        return err, None
    return turn_explicit_args_damon_on(args)

# Commandline options setup helpers

def set_common_argparser(parser):
    parser.add_argument('--damon_interface',
            choices=['debugfs', 'sysfs', 'auto'],
            default='auto', help='underlying DAMON interface to use')
    parser.add_argument('--debug_damon', action='store_true',
            help='Print debugging log')

def set_common_monitoring_argparser(parser):
    parser.add_argument('-s', '--sample', metavar='<interval>',
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<interval>',
            default=100000, help='aggregate interval (us)')
    parser.add_argument('-u', '--updr', metavar='<interval>',
            default=1000000, help='regions update interval (us)')
    parser.add_argument('-n', '--minr', metavar='<# regions>',
            default=10, help='minimal number of regions')
    parser.add_argument('-m', '--maxr', metavar='<# regions>',
            default=1000, help='maximum number of regions')
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='if target is \'paddr\', limit it to the numa node')

def set_implicit_target_monitoring_argparser(parser):
    set_common_monitoring_argparser(parser)
    parser.add_argument('target', type=str, metavar='<target>',
            help='the target (command, pid, or special keywords) to monitor')
    set_common_argparser(parser)

def set_implicit_target_record_argparser(parser):
    set_implicit_target_monitoring_argparser(parser)
    parser.add_argument('-l', '--rbuf', metavar='<len>', type=int,
            help='length of record result buffer')
    parser.add_argument('-o', '--out', metavar='<file path>', type=str,
            default='damon.data', help='output file path')

def set_implicit_target_schemes_argparser(parser):
    set_implicit_target_monitoring_argparser(parser)
    parser.add_argument('-c', '--schemes', metavar='<file or schemes in text>',
            type=str, default='damon.schemes',
            help='data access monitoring-based operation schemes')

def set_explicit_target_argparser(parser):
    set_common_monitoring_argparser(parser)
    parser.add_argument('--ops', choices=['vaddr', 'paddr', 'fvaddr'],
            default='paddr',
            help='monitoring operations set')
    parser.add_argument('--target_pid', type=int, help='target pid')
    parser.add_argument('-c', '--schemes', metavar='<file or schemes in text>',
	    default=json.dumps([_damon.Damos().to_kvpairs()], indent=4),
	    help='data access monitoring-based operation schemes')
    parser.add_argument('--kdamonds', metavar='<string or file>',
            help='key-value pairs format kdamonds config')
    set_common_argparser(parser)
