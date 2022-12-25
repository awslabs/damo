#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import time

import damo_stat_kdamonds
import damo_stat_schemes

import _damo_subcmds
import _damon
import _damon_args

def pr_damon_interface(args):
    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)
    print(_damon.damon_interface())

subcmds = [
        _damo_subcmds.DamoSubCmd(name='kdamonds', module=damo_stat_kdamonds,
            msg='detailed status of kdamonds'),
        _damo_subcmds.DamoSubCmd(name='schemes_stats',
            module=damo_stat_schemes,
            msg='schemes apply stats'),
        _damo_subcmds.DamoSubCmd(name='schemes_tried_regions',
            module=damo_stat_schemes,
            msg='schemes tried regions in detail'),
        _damo_subcmds.DamoSubCmd(name='damon_interface',
            module=_damo_subcmds.DamoSubCmdModule(None, pr_damon_interface),
            msg='default DAMON interface'),
        ]

def set_common_argparser(parser):
    parser.add_argument('--delay', metavar='<secs>', default=3, type=float,
            help='delay between repeated status prints')
    parser.add_argument('--count', metavar='<count>', default=1, type=int,
            help='number of repeated status prints')

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='stat type', dest='stat_type',
            metavar='<stat type>', help='the type of the stat to show')
    subparsers.required = True

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)

    _damon_args.set_common_argparser(parser)

def run_count_delay(func, args):
    for i in range(args.count):
        func(args)
        if i != args.count - 1:
            time.sleep(args.delay)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    for subcmd in subcmds:
        if subcmd.name == args.stat_type:
            subcmd.execute(args)

if __name__ == '__main__':
    main()
