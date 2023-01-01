#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def pr_schemes_tried_regions(kdamond_name, monitoring_scheme, raw_nr):
    for kdamond in _damon.current_kdamonds():
        if kdamond.name != kdamond_name:
            continue
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if scheme == monitoring_scheme:
                    print('\n'.join(r.to_str(raw_nr, ctx.intervals) for r in
                        scheme.tried_regions))
                    return

def monitoring_kdamond_scheme():
    monitoring_kdamond = None
    monitoring_scheme = None
    kdamonds = _damon.current_kdamonds()
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if _damon.is_monitoring_scheme(scheme, ctx.intervals):
                    return kdamond.name, scheme
    return None, None

def update_pr_schemes_tried_regions(raw_nr):
    if _damon.every_kdamond_turned_off():
        print('no kdamond running')
        exit(1)

    monitoring_kdamond, monitoring_scheme = monitoring_kdamond_scheme()
    if monitoring_kdamond == None:
        print('no kdamond is having monitoring scheme')
        exit(1)

    err = _damon.update_schemes_tried_regions([monitoring_kdamond])
    if err != None:
        print('update schemes tried regions fail: %s', err)
        exit(1)

    pr_schemes_tried_regions(monitoring_kdamond, monitoring_scheme, raw_nr)

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)

def __main(args):
    if not _damon.feature_supported('schemes_tried_regions'):
        print('schemes_tried_regions feature not supported')
        exit(1)
    update_pr_schemes_tried_regions(args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
