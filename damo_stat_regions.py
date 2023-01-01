#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def pr_schemes_tried_regions(kdamonds, raw_nr):
    print('# <kdamond> <context>')
    print('# <regions>')
    print('# ...')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if not _damon.default_Damos.effectively_equal(
                        scheme, ctx.intervals):
                    continue
                print('%s %s' % (kdamond.name, ctx.name))
                print('\n'.join(
                    r.to_str(raw_nr) for r in scheme.tried_regions))

def update_pr_schemes_tried_regions(raw_nr):
    if _damon.any_kdamond_running():
        names = _damon.current_kdamond_names()
        if _damon.feature_supported('schemes_tried_regions'):
            err = _damon.update_schemes_tried_regions(names)
            if err != None:
                print('update schemes tried regions fail: %s', err)
                exit(1)
    kdamonds = _damon.current_kdamonds()
    pr_schemes_tried_regions(kdamonds, raw_nr)

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
