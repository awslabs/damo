# SPDX-License-Identifier: GPL-2.0

"""
Command line arguments handling
"""

import argparse
import json
import os
import subprocess

import _damo_paddr_layout
import _damon

# Kdamonds construction from command line arguments

def init_regions_for(args):
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

def damon_intervals_for(args):
    default_intervals = _damon.DamonIntervals()
    intervals1 = _damon.DamonIntervals(args.sample, args.aggr, args.updr)
    intervals2 = _damon.DamonIntervals(*args.monitoring_intervals)
    if not intervals1 == default_intervals:
        return intervals1
    if not intervals2 == default_intervals:
        return intervals2
    return default_intervals

def damon_nr_regions_range_for(args):
    default_range = _damon.DamonNrRegionsRange()
    range1 = _damon.DamonNrRegionsRange(args.minr, args.maxr)
    range2 = _damon.DamonNrRegionsRange(*args.monitoring_nr_regions_range)
    if not range1 == default_range:
        return range1
    if not range2 == default_range:
        return range2
    return default_range

def schemes_option_to_damos(schemes):
    if os.path.isfile(schemes):
        with open(schemes, 'r') as f:
            schemes = f.read()

    try:
        kvpairs = json.loads(schemes)
        return [_damon.Damos.from_kvpairs(kv) for kv in kvpairs], None
    except Exception as json_err:
        return None, '%s' % json_err

def damos_options_to_scheme(args):
    try:
        return _damon.Damos(
                access_pattern=_damon.DamosAccessPattern(
                    args.damos_sz_region, args.damos_access_rate,
                    _damon.unit_percent, args.damos_age, _damon.unit_usec),
                action=args.damos_action), None
    except Exception as e:
        return None, 'Wrong \'--damos_*\' argument (%s)' % e

def damos_for(args):
    if args.damos_action:
        damos, err = damos_options_to_scheme(args)
        if err != None:
            return None, err
        return [damos], None

    if not 'schemes' in args or args.schemes == None:
        return [], None

    schemes, err = schemes_option_to_damos(args.schemes)
    if err:
        return None, 'failed damo schemes arguments parsing (%s)' % err
    return schemes, None

def damon_ctx_for(args):
    try:
        intervals = damon_intervals_for(args)
    except Exception as e:
        return None, 'invalid intervals arguments (%s)' % e
    try:
        nr_regions = damon_nr_regions_range_for(args)
    except Exception as e:
        return None, 'invalid nr_regions arguments (%s)' % e
    ops = args.ops

    init_regions, err = init_regions_for(args)
    if err:
        return None, err

    try:
        target = _damon.DamonTarget(args.target_pid
                if _damon.target_has_pid(ops) else None, init_regions)
    except Exception as e:
        return 'Wrong \'--target_pid\' argument (%s)' % e

    schemes, err = damos_for(args)
    if err:
        return None, err

    try:
        ctx = _damon.DamonCtx(intervals, nr_regions, ops, [target], schemes)
        return ctx, None
    except Exception as e:
        return None, 'Creating context from arguments failed (%s)' % e

def kdamonds_from_json_arg(arg):
    try:
        if os.path.isfile(arg):
            with open(arg, 'r') as f:
                kdamonds_str = f.read()
        else:
            kdamonds_str = arg
        kdamonds_kvpairs = json.loads(kdamonds_str)['kdamonds']
        return [kdamond.from_kvpairs(kvp) for kvp in kdamonds_kvpairs], None
    except Exception as e:
        return None, e

target_type_explicit = 'explicit'
target_type_cmd = 'cmd'
target_type_pid = 'pid'
target_type_unknown = None

def deduced_target_type(target):
    if target in ['vaddr', 'paddr', 'fvaddr']:
        return target_type_explicit
    try:
        subprocess.check_output(['which', target.split()[0]])
        return target_type_cmd
    except:
        pass
    try:
        pid = int(target)
        return target_type_pid
    except:
        pass
    return target_type_unknown

def warn_option_override(option_name):
    print('warning: %s is overridden by <deducible target>' % option_name)

def deduce_target_update_args(args):
    args.self_started_target = False
    target_type = deduced_target_type(args.deducible_target)
    if target_type == target_type_unknown:
        return 'target \'%s\' is not supported' % args.deducible_target
    if target_type == target_type_explicit and args.deducible_target == 'paddr':
        if not args.ops in ['paddr', None]:
            warn_option_override('--ops')
        args.ops = 'paddr'
        if args.target_pid != None:
            warn_option_override('--target_pid')
        args.target_pid = None
        return None
    if target_type == target_type_cmd:
        p = subprocess.Popen(args.deducible_target, shell=True,
                executable='/bin/bash')
        pid = p.pid
        args.self_started_target = True
    elif target_type == target_type_pid:
        pid = int(args.deducible_target)
    if args.target_pid != None:
        print('warning: --target_pid will be ignored')
    args.target_pid = pid
    if not args.regions:
        if not args.ops in ['vaddr', None]:
            warn_option_override('--ops')
        args.ops = 'vaddr'
    if args.regions:
        if not args.ops in ['fvaddr', None]:
            print('warning: override --ops by <deducible target> and --regions')
        args.ops = 'fvaddr'

def kdamonds_for(args):
    if args.kdamonds:
        return kdamonds_from_json_arg(args.kdamonds)

    if args.deducible_target:
        kdamonds, e = kdamonds_from_json_arg(args.deducible_target)
        if e == None:
            return kdamonds, e
        err = deduce_target_update_args(args)
        if err:
            return None, err
    if args.ops == None:
        if args.target_pid == None:
            args.ops = 'paddr'
        else:
            args.ops = 'vaddr'

    ctx, err = damon_ctx_for(args)
    if err:
        return None, err
    return [_damon.Kdamond(state=None, pid=None, contexts=[ctx])], None

def self_started_target(args):
    return 'self_started_target' in args and args.self_started_target

# Command line processing helpers

def is_ongoing_target(args):
    return args.deducible_target == 'ongoing'

def stage_kdamonds(args):
    kdamonds, err = kdamonds_for(args)
    if err:
        return None, 'cannot create kdamonds from args (%s)' % err
    err = _damon.stage_kdamonds(kdamonds)
    if err:
        return None, 'cannot apply kdamonds from args (%s)' % err
    return kdamonds, None

def commit_kdamonds(args):
    kdamonds, err = kdamonds_for(args)
    if err:
        return None, 'cannot create kdamonds to commit from args (%s)' % err
    err = _damon.commit(kdamonds)
    if err:
        return None, 'cannot commit kdamonds (%s)' % err
    return kdamonds, None

def turn_damon_on(args):
    kdamonds, err = stage_kdamonds(args)
    if err:
        return err, None
    return _damon.turn_damon_on(
            ['%s' % kidx for kidx, k in enumerate(kdamonds)]), kdamonds

# Commandline options setup helpers

def set_common_argparser(parser):
    parser.add_argument('--damon_interface',
            choices=['sysfs', 'debugfs', 'auto'],
            default='auto',
            help='underlying DAMON interface to use (!! DEPRECATED)')
    parser.add_argument('--debug_damon', action='store_true',
            help='Print debugging log')

def set_monitoring_attrs_argparser(parser):
    # for easier pinpoint setup
    parser.add_argument('-s', '--sample', metavar='<microseconds>',
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<microseconds>',
            default=100000, help='aggregate interval (us)')
    parser.add_argument('-u', '--updr', metavar='<microseconds>',
            default=1000000, help='regions update interval (us)')
    parser.add_argument('-n', '--minr', metavar='<# regions>',
            default=10, help='minimal number of regions')
    parser.add_argument('-m', '--maxr', metavar='<# regions>',
            default=1000, help='maximum number of regions')

    # for easier total setup
    parser.add_argument('--monitoring_intervals', nargs=3,
            default=['5ms', '100ms', '1s'],
            metavar=('<sample>', '<aggr>', '<update>'),
            help='monitoring intervals (us)')
    parser.add_argument('--monitoring_nr_regions_range', nargs=2,
            metavar=('<min>', '<max>'), default=[10, 1000],
            help='min/max number of monitoring regions')

def set_monitoring_argparser(parser):
    set_monitoring_attrs_argparser(parser)
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='if target is \'paddr\', limit it to the numa node')

def set_damos_argparser(parser):
    parser.add_argument('--damos_sz_region', metavar=('<min>', '<max>'),
            nargs=2, default=['min', 'max'],
            help='min/max size of damos target regions (bytes)')
    parser.add_argument('--damos_access_rate', metavar=('<min>', '<max>'),
            nargs=2, default=['min', 'max'],
            help='min/max access rate of damos target regions (percent)')
    parser.add_argument('--damos_age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of damos target regions (microseconds)')
    parser.add_argument('--damos_action', metavar='<action>',
            choices=_damon.damos_actions,
            help='damos action to apply to the target regions')

def set_argparser(parser, add_record_options):
    if parser == None:
        parser = argparse.ArgumentParser()
    set_monitoring_argparser(parser)
    parser.add_argument('--ops', choices=['vaddr', 'paddr', 'fvaddr'],
            help='monitoring operations set')
    parser.add_argument('--target_pid', type=int, help='target pid')
    set_damos_argparser(parser)
    parser.add_argument('-c', '--schemes', metavar='<json string or file>',
	    help='data access monitoring-based operation schemes')
    parser.add_argument('--kdamonds', metavar='<json string or file>',
            help='json format kdamonds specification to run DAMON for')
    parser.add_argument('deducible_target', type=str,
            metavar='<deducible target>', nargs='?',
            help='the target (command, pid, or special keywords) to monitor')
    if add_record_options:
        parser.add_argument('-o', '--out', metavar='<file path>', type=str,
                default='damon.data', help='output file path')
    set_common_argparser(parser)
    return parser
