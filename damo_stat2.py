#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat_kdamonds_summary
import damo_stat_schemes_stats
import damo_stat_schemes_tried_regions

import _damo_subcmds
import _damon_args

subcmds = [
        _damo_subcmds.DamoSubCmd(name='kdamonds_summary',
            module=damo_stat_kdamonds_summary,
            msg='summary of kdamonds'),
        _damo_subcmds.DamoSubCmd(name='schemes_stats',
            module=damo_stat_schemes_stats,
            msg='schemes apply stats'),
        _damo_subcmds.DamoSubCmd(name='schemes_tried_regions',
            module=damo_stat_schemes_tried_regions,
            msg='schemes tried regions in detail'),
        ]

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='stat type', dest='stat_type',
            metavar='<stat type>', help='the type of the stat to show')
    subparsers.required = True

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)

    _damon_args.set_common_argparser(parser)

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
