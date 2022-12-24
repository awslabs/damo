#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import _damon

def pr_schemes_tried_regions(kdamonds):
    print('# <kdamond> <context> <scheme>')
    print('# <regions>')
    print('# ...')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s %s %s' % (kdamond.name, ctx.name, scheme.name))
                print('\n'.join('%s' % r for r in scheme.tried_regions))

def update_pr_schemes_tried_regions():
    if _damon.any_kdamond_running():
        for name in _damon.current_kdamond_names():
            err = _damon.update_schemes_stats(name)
            if err != None:
                print('update schemes stat fail:', err)
                exit(1)
            if _damon.feature_supported('schemes_tried_regions'):
                err = _damon.update_schemes_tried_regions(name)
                if err != None:
                    print('update schemes tried regions fail: %s', err)
                    exit(1)
    content = _damon.read_damon_fs()
    kdamonds = _damon.current_kdamonds()
    pr_schemes_tried_regions(kdamonds)

def set_argparser(parser):
    parser.add_argument('--delay', metavar='<secs>', default=3, type=float,
            help='delay between repeated status prints')
    parser.add_argument('--count', metavar='<count>', default=1, type=int,
            help='number of repeated status prints')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    for i in range(args.count):
        update_pr_schemes_tried_regions()
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
