#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_bin2txt
import damo_heats
import damo_nr_regions
import damo_wss

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='report type', dest='report_type',
            metavar='<report type>', help='the type of the report to generate')
    subparsers.required = True

    parser_raw = subparsers.add_parser('raw', help='human readable raw data')
    damo_bin2txt.set_argparser(parser_raw)

    parser_heats = subparsers.add_parser('heats', help='heats of regions')
    damo_heats.set_argparser(parser_heats)

    parser_wss = subparsers.add_parser('wss', help='working set size')
    damo_wss.set_argparser(parser_wss)

    parser_nr_regions = subparsers.add_parser('nr_regions',
            help='number of regions')
    damo_nr_regions.set_argparser(parser_nr_regions)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.report_type == 'raw':
        damo_bin2txt.main(args)
    elif args.report_type == 'heats':
        damo_heats.main(args)
    elif args.report_type == 'wss':
        damo_wss.main(args)
    elif args.report_type == 'nr_regions':
        damo_nr_regions.main(args)

if __name__ == '__main__':
    main()
