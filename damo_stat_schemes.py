#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def pr_schemes_tried_regions(kdamonds, raw_nr):
    print('# <kdamond> <context> <scheme>')
    print('# <regions>')
    print('# ...')
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                print('%s %s %s' % (kdamond.name, ctx.name, scheme.name))
                print('\n'.join(
                    r.to_str(raw_nr) for r in scheme.tried_regions))

def update_pr_schemes_tried_regions(raw_nr):
    err = _damon.update_schemes_tried_regions()
    if err:
        print(err)
        return
    pr_schemes_tried_regions(_damon.current_kdamonds(), raw_nr)

def update_pr_schemes_stats(raw_nr):
    err = _damon.update_schemes_stats()
    if err:
        print(err)
        return
    kdamonds = _damon.current_kdamonds()

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

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)

def __main(args):
    if args.stat_type == 'schemes_stats':
        update_pr_schemes_stats(args.raw)
    elif args.stat_type == 'schemes_tried_regions':
        update_pr_schemes_tried_regions(args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
