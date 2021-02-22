#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import bin2txt
import heats
import nr_regions
import wss

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='report type', dest='report_type',
            metavar='<report type>', help='the type of the report to generate')
    subparsers.required = True

    parser_raw = subparsers.add_parser('raw', help='human readable raw data')
    bin2txt.set_argparser(parser_raw)

    parser_heats = subparsers.add_parser('heats', help='heats of regions')
    heats.set_argparser(parser_heats)

    parser_wss = subparsers.add_parser('wss', help='working set size')
    wss.set_argparser(parser_wss)

    parser_nr_regions = subparsers.add_parser('nr_regions',
            help='number of regions')
    nr_regions.set_argparser(parser_nr_regions)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.report_type == 'raw':
        bin2txt.main(args)
    elif args.report_type == 'heats':
        heats.main(args)
    elif args.report_type == 'wss':
        wss.main(args)
    elif args.report_type == 'nr_regions':
        nr_regions.main(args)

if __name__ == '__main__':
    main()
