#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0

import argparse

from os import sys, path
sys.path.append(path.dirname(path.abspath(__file__)))

import adjust
import features
import monitor
import reclaim
import record
import report
import schemes

class SubCmdHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter,
                self)._format_action(action)
        # skip sub parsers help
        if action.nargs == argparse.PARSER:
            parts = '\n'.join(parts.split('\n')[1:])
        return parts

def main():
    parser = argparse.ArgumentParser(formatter_class=SubCmdHelpFormatter)

    subparser = parser.add_subparsers(title='command', dest='command',
            metavar='<command>')
    subparser.required = True

    parser_record = subparser.add_parser('record',
            help='record data accesses')
    record.set_argparser(parser_record)

    parser_schemes = subparser.add_parser('schemes',
            help='apply operation schemes')
    schemes.set_argparser(parser_schemes)

    parser_report = subparser.add_parser('report',
            help='report the recorded data accesses in the specified form')
    report.set_argparser(parser_report)

    parser_monitor = subparser.add_parser('monitor',
            help='repeat the recording and the reporting of data accesses')
    monitor.set_argparser(parser_monitor)

    parser_adjust = subparser.add_parser('adjust',
            help='adjust the record results with different monitoring attributes')
    adjust.set_argparser(parser_adjust)

    parser_reclaim = subparser.add_parser('reclaim', help='control DAMON_RECLAIM')
    reclaim.set_argparser(parser_reclaim)

    parser_features = subparser.add_parser('features',
            help='list supported DAMON features in the kernel')
    features.set_argparser(parser_features)

    subparser.add_parser('version', help='print the version number')

    args = parser.parse_args()

    if args.command == 'record':
        record.main(args)
    elif args.command == 'schemes':
        schemes.main(args)
    elif args.command == 'report':
        report.main(args)
    elif args.command == 'monitor':
        monitor.main(args)
    elif args.command == 'adjust':
        adjust.main(args)
    elif args.command == 'reclaim':
        reclaim.main(args)
    elif args.command == 'features':
        features.main(args)
    elif args.command == 'version':
        bindir = path.dirname(path.abspath(__file__))
        with open(path.join(bindir, 'VERSION'), 'r') as f:
            print(f.read().strip())

if __name__ == '__main__':
    main()
