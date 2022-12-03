#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import time

import _damo_fmt_str
import _damon
import _damon_args

def set_argparser(parser):
    parser.add_argument('target', choices=['kdamonds_summary', 'schemes_stats',
        'schemes_tried_regions', 'kdamonds', 'damon_interface'],
            nargs='?', default='kdamonds_summary', help='What status to show')
    parser.add_argument('--json', action='store_true',
            help='print kdamond in json format')
    parser.add_argument('--delay', metavar='<secs>', default=3, type=float,
            help='delay between repeated status prints')
    parser.add_argument('--count', metavar='<count>', default=1, type=int,
            help='number of repeated status prints')
    parser.add_argument('--raw', action='store_true',
            help='print number in mchine friendly raw form')

    _damon_args.set_common_argparser(parser)

def pr_schemes_stats(kdamonds, raw_nr):
    print('# <kdamond> <context> <scheme> <field> <value>')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s %s %s %s %s' % (kdamond.name, ctx.name, scheme.name,
                    'nr_tried', _damo_fmt_str.format_nr(
                        scheme.stats.nr_tried, raw_nr)))
                print('%s %s %s %s %s' % (kdamond.name, ctx.name, scheme.name,
                    'sz_tried', _damo_fmt_str.format_sz(
                        scheme.stats.sz_tried, raw_nr)))
                print('%s %s %s %s %s' % (kdamond.name, ctx.name, scheme.name,
                    'nr_applied', _damo_fmt_str.format_nr(
                        scheme.stats.nr_applied, raw_nr)))
                print('%s %s %s %s %s' % (kdamond.name, ctx.name, scheme.name,
                    'sz_applied', _damo_fmt_str.format_sz(
                        scheme.stats.sz_applied, raw_nr)))
                print('%s %s %s %s %s' % (kdamond.name, ctx.name, scheme.name,
                    'qt_exceeds', _damo_fmt_str.format_nr(
                        scheme.stats.qt_exceeds, raw_nr)))

def pr_schemes_tried_regions(kdamonds):
    print('# <kdamond> <context> <scheme>')
    print('# <regions>')
    print('# ...')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s %s %s' % (kdamond.name, ctx.name, scheme.name))
                print('\n'.join('%s' % r for r in scheme.tried_regions))

def update_pr_damo_stat(target, json_format, raw_nr):
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
    if target == 'kdamonds_summary':
        print('\n'.join([k.summary_str() for k in kdamonds]))
    elif target == 'kdamonds':
        if json_format:
            print(json.dumps([k.to_kvpairs() for k in kdamonds],
                indent=4, sort_keys=True))
        else:
            print('kdamonds')
            print(_damo_fmt_str.indent_lines(
                '\n\n'.join(['%s' % k for k in kdamonds]), 4))
    elif target == 'schemes_stats':
        pr_schemes_stats(kdamonds, raw_nr)
    elif target == 'schemes_tried_regions':
        pr_schemes_tried_regions(kdamonds)
    elif target == 'damon_interface':
        print(_damon.damon_interface())

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    # Require root permission
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    for i in range(args.count):
        update_pr_damo_stat(args.target, args.json, args.raw)
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
