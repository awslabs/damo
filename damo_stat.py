#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json

import _damo_fmt_str
import _damon
import _damon_args

def set_argparser(parser):
    parser.add_argument('target', choices=['schemes_stats',
        'schemes_tried_regions', 'kdamonds', 'damon_interface'],
            nargs='?', default='kdamonds', help='What status to show')
    parser.add_argument('--json', action='store_true',
            help='print kdamond in json format')
    _damon_args.set_common_argparser(parser)

def pr_schemes_stats(kdamonds):
    print('# <kdamond> <context> <scheme> <field> <value>')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s %s %s %s: %s' % (kdamond.name, ctx.name, scheme.name,
                    'nr_tried', scheme.stats.nr_tried))
                print('%s %s %s %s: %s' % (kdamond.name, ctx.name, scheme.name,
                    'sz_tried', scheme.stats.sz_tried))
                print('%s %s %s %s: %s' % (kdamond.name, ctx.name, scheme.name,
                    'nr_applied', scheme.stats.nr_applied))
                print('%s %s %s %s: %s' % (kdamond.name, ctx.name, scheme.name,
                    'sz_applied', scheme.stats.sz_applied))
                print('%s %s %s %s: %s' % (kdamond.name, ctx.name, scheme.name,
                    'qt_exceeds', scheme.stats.qt_exceeds))

def pr_schemes_tried_regions(kdamonds):
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s/%s/%s' % (kdamond.name, ctx.name, scheme.name))
                print('\n'.join('%s' % r for r in scheme.tried_regions))

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    if _damon.any_kdamond_running():
        for name in _damon.current_kdamond_names():
            err = _damon.update_schemes_stats(name)
            if err != None:
                print('update schemes stat fil:', err)
                exit(1)
            if _damon.feature_supported('schemes_tried_regions'):
                err = _damon.update_schemes_tried_regions(name)
                if err != None:
                    print('update schemes tried regions fail: %s', err)
                    exit(1)
    content = _damon.read_damon_fs()
    kdamonds = _damon.current_kdamonds()
    if args.target == 'kdamonds':
        if args.json:
            print(json.dumps([k.to_kvpairs() for k in kdamonds],
                indent=4, sort_keys=True))
        else:
            print('kdamonds')
            print(_damo_fmt_str.indent_lines(
                '\n\n'.join(['%s' % k for k in kdamonds]), 4))
    elif args.target == 'schemes_stats':
        pr_schemes_stats(kdamonds)
    elif args.target == 'schemes_tried_regions':
        pr_schemes_tried_regions(kdamonds)
    elif args.target == 'damon_interface':
        print(_damon.damon_interface())

if __name__ == '__main__':
    main()
