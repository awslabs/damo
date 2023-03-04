#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def out_of_range(minval, val, maxval):
    return val < minval or maxval < val

def __pr_schemes_tried_regions(regions, intervals, access_pattern, size_only,
        raw_nr):
    access_pattern.convert_for_units(_damon.unit_sample_intervals,
            _damon.unit_aggr_intervals, intervals)
    total_sz = 0
    for region in regions:
        sz = region.end - region.start
        if out_of_range(access_pattern.sz_bytes[0], sz,
                access_pattern.sz_bytes[1]):
            continue
        if out_of_range(access_pattern.nr_accesses[0],
                region.nr_accesses,
                access_pattern.nr_accesses[1]):
            continue
        if out_of_range(access_pattern.age[0], region.age,
                access_pattern.age[1]):
            continue
        if not size_only:
            print(region.to_str(raw_nr, intervals))
        else:
            total_sz += sz
    if size_only:
        print('%s' % _damo_fmt_str.format_sz(total_sz, raw_nr))

def pr_schemes_tried_regions(kdamond_name, monitoring_scheme,
        access_pattern, size_only, raw_nr):
    for kdamond in _damon.current_kdamonds():
        if kdamond.name != kdamond_name:
            continue
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if not scheme.effectively_equal(monitoring_scheme,
                        ctx.intervals):
                    continue
                __pr_schemes_tried_regions(scheme.tried_regions, ctx.intervals,
                        access_pattern, size_only, raw_nr)

def install_monitoring_scheme(kdamonds):
    installed_schemes = []
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            ctx_has_monitoring_scheme = False
            for scheme in ctx.schemes:
                if _damon.is_monitoring_scheme(scheme, ctx.intervals):
                    ctx_has_monitoring_scheme = True
                    break
            if not ctx_has_monitoring_scheme:
                scheme = _damon.Damos(name='%d' % len(ctx.schemes))
                ctx.schemes.append(scheme)
                installed_schemes.append(scheme)
    return installed_schemes

def uninstall_schemes(kdamonds, schemes):
    installed_schemes_ids = [id(s) for s in schemes]
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if id(scheme) in installed_schemes_ids:
                    ctx.schemes.remove(scheme)
    err = _damon.apply_kdamonds(kdamonds)
    if err != None:
        print('monitoring schemes uninstall failed: %s' % err)
        return
    err = _damon.commit_inputs(kdamonds)
    if err != None:
        print('monitoring schemes uninstall commit failed: %s' % err)
        return

def update_pr_schemes_tried_regions(access_pattern, size_only, raw_nr):
    running_kdamonds = _damon.running_kdamonds()
    if len(running_kdamonds) == 0:
        print('no kdamond running')
        return

    # ensure each kdamonds have a monitoring scheme
    installed_schemes = install_monitoring_scheme(running_kdamonds)

    if len(installed_schemes) != 0:
        err = _damon.apply_kdamonds(running_kdamonds)
        if err != None:
            print('monitoring schemes install failed: %s' % err)
            return
        err = _damon.commit_inputs(running_kdamonds)
        if err != None:
            print('monitoring schemes commit failed: %s' % err)
            return

    err = _damon.update_schemes_tried_regions([k.name for k in
        running_kdamonds])
    if err != None:
        print('update schemes tried regions fail: %s' % err)
        uninstall_schemes(running_kdamonds, installed_schemes)
        return

    for kdamond in running_kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if _damon.is_monitoring_scheme(scheme, ctx.intervals):
                    pr_schemes_tried_regions(kdamond.name, scheme,
                            access_pattern, size_only, raw_nr)

    uninstall_schemes(running_kdamonds, installed_schemes)

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)
    parser.add_argument('--sz_region', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max size of regions (bytes)')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of regions (percent)')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of regions (microseconds)')
    parser.add_argument('--size_only', action='store_true',
            help='print total size only')

def __main(args):
    update_pr_schemes_tried_regions(args.damo_stat_regions_access_pattern,
            args.size_only, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    args.damo_stat_regions_access_pattern = _damon.DamosAccessPattern(
            args.sz_region, args.access_rate, _damon.unit_percent, args.age,
            _damon.unit_usec)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
