#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def priority(region, weights):
    if region.nr_accesses > 0:
        return region.nr_accesses * weights[0] + region.age * weights[1]
    return region.age * weights[1] * -1

def __pr_schemes_tried_regions(regions, intervals, size_only, sortby,
        prio_weights, raw_nr):

    if sortby == 'priority':
        regions.sort(key=lambda region: priority(region, prio_weights))

    total_sz = 0
    for region in regions:
        if not size_only:
            print(region.to_str(raw_nr, intervals))
        else:
            total_sz += (region.end - region.start)
    if size_only:
        print('%s' % _damo_fmt_str.format_sz(total_sz, raw_nr))

def pr_schemes_tried_regions(monitor_scheme, size_only, sortby, prio_weights,
        raw_nr):
    for kdamond in _damon.running_kdamonds():
        for ctx in kdamond.contexts:
            print('kdamond %s ctx %s' % (kdamond.name, ctx.name))
            for scheme in ctx.schemes:
                if scheme.effectively_equal(monitor_scheme, ctx.intervals):
                    __pr_schemes_tried_regions(scheme.tried_regions,
                            ctx.intervals, size_only, sortby, prio_weights,
                            raw_nr)
                    break

def install_scheme_if_needed(kdamonds, scheme_to_install):
    installed = False
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            ctx_has_the_scheme = False
            for scheme in ctx.schemes:
                if scheme.effectively_equal(scheme_to_install, ctx.intervals):
                    ctx_has_the_scheme = True
                    break
            if not ctx_has_the_scheme:
                ctx.schemes.append(scheme_to_install)
                installed = True
    if installed:
        err = _damon.commit(kdamonds)
        if err != None:
            return (False,
                    'committing scheme installed kdamonds failed: %s' % err)
    return installed, None

def update_pr_schemes_tried_regions(monitor_scheme, size_only, sortby,
        prio_weights, raw_nr):
    orig_kdamonds = _damon.current_kdamonds()
    running_kdamonds = _damon.running_kdamonds()
    if len(running_kdamonds) == 0:
        print('no kdamond running')
        return

    # ensure each kdamonds have a monitoring scheme
    installed, err = install_scheme_if_needed(running_kdamonds, monitor_scheme)
    if err:
        print('monitoring scheme install failed: %s' % err)
        return

    err = _damon.update_schemes_tried_regions([k.name for k in
        running_kdamonds])
    if err != None:
        print('update schemes tried regions fail: %s' % err)
        if installed:
            err = _damon.commit(orig_kdamonds)
            if err:
                print('monitoring scheme uninstall failed: %s' % err)
            return

    pr_schemes_tried_regions(monitor_scheme, size_only, sortby, prio_weights,
            raw_nr)

    if installed:
        err = _damon.commit(orig_kdamonds)
        if err:
            print('monitoring scheme uninstall failed: %s' % err)

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
    parser.add_argument('--sortby', choices=['address', 'priority'],
            default='sortby',
            help='the metric for the regions print order')
    parser.add_argument('--priority_weights', nargs=2, type=float,
            default=[1, 1,],
            metavar=('<access rate weight>, <age weight>'),
            help='priority weights for priority calculation')

def __main(args):
    update_pr_schemes_tried_regions(args.monitor_scheme, args.size_only,
            args.sortby, args.priority_weights, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    args.monitor_scheme = _damon.Damos(
            access_pattern=_damon.DamosAccessPattern(
                args.sz_region, args.access_rate, _damon.unit_percent,
                args.age, _damon.unit_usec))

    damo_stat.run_count_delay(__main, args)

if __name__ == '__main__':
    main()
