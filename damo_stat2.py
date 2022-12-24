#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat_kdamonds_summary
import damo_stat_schemes_stats
import damo_stat_schemes_tried_regions

import _damon_args

type_module = {
        'kdamonds_summary': damo_stat_kdamonds_summary,
        'schemes_stats': damo_stat_schemes_stats,
        'schemes_tried_regions': damo_stat_schemes_tried_regions
        }

class DamoStatType:
    name = None
    msg = None
    module = None

    def __init__(self, name, msg, module):
        self.name = name
        self.msg = msg
        self.module = module

damo_stat_types = [
        DamoStatType(name='kdamonds_summary',
            module=damo_stat_kdamonds_summary,
            msg='summary of kdamonds'),
        DamoStatType(name='schemes_stats', module=damo_stat_schemes_stats,
            msg='schemes apply stats'),
        DamoStatType(name='schemes_tried_regions',
            module=damo_stat_schemes_tried_regions,
            msg='schemes tried regions in detail'),
        ]

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='stat type', dest='stat_type',
            metavar='<stat type>', help='the type of the stat to show')
    subparsers.required = True

    for stat_type in damo_stat_types:
        subparser = subparsers.add_parser(stat_type.name, help=stat_type.msg)
        stat_type.module.set_argparser(subparser)

    _damon_args.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    module = [s.module for s in damo_stat_types if s.name == args.stat_type][0]
    module.main(args)

if __name__ == '__main__':
    main()
