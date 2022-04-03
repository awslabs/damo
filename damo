#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0

import argparse

import os
os.sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import damo_adjust
import damon_fs
import damo_features
import damo_monitor
import damo_reclaim
import damo_record
import damo_report
import damo_schemes
import damo_status
import damo_validate

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

    parser_record = subparser.add_parser('record', help='record data accesses')
    damo_record.set_argparser(parser_record)

    parser_schemes = subparser.add_parser('schemes',
            help='apply operation schemes')
    damo_schemes.set_argparser(parser_schemes)

    parser_report = subparser.add_parser('report',
            help='report the recorded data accesses in the specified form')
    damo_report.set_argparser(parser_report)

    parser_monitor = subparser.add_parser('monitor',
            help='repeat the recording and the reporting of data accesses')
    damo_monitor.set_argparser(parser_monitor)

    parser_adjust = subparser.add_parser('adjust',
            help='adjust the record results with different monitoring attributes')
    damo_adjust.set_argparser(parser_adjust)

    parser_reclaim = subparser.add_parser('reclaim',
            help='control DAMON_RECLAIM')
    damo_reclaim.set_argparser(parser_reclaim)

    parser_features = subparser.add_parser('features',
            help='list supported DAMON features in the kernel')
    damo_features.set_argparser(parser_features)

    parser_validate = subparser.add_parser('validate',
            help='validate a given record result file')
    damo_validate.set_argparser(parser_validate)

    parser_damon_fs = subparser.add_parser('fs',
            help='manipulate DAMON in a filesystem-like manner')
    damon_fs.set_argparser(parser_damon_fs)

    parser_damo_status = subparser.add_parser('status',
            help='print status of DAMON')
    damo_status.set_argparser(parser_damo_status)

    subparser.add_parser('version', help='print the version number')

    args = parser.parse_args()

    if args.command == 'record':
        damo_record.main(args)
    elif args.command == 'schemes':
        damo_schemes.main(args)
    elif args.command == 'report':
        damo_report.main(args)
    elif args.command == 'monitor':
        damo_monitor.main(args)
    elif args.command == 'adjust':
        damo_adjust.main(args)
    elif args.command == 'reclaim':
        damo_reclaim.main(args)
    elif args.command == 'features':
        damo_features.main(args)
    elif args.command == 'validate':
        damo_validate.main(args)
    elif args.command == 'fs':
        damon_fs.main(args)
    elif args.command == 'status':
        damo_status.main(args)
    elif args.command == 'version':
        bindir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(bindir, 'damo_version.py'), 'r') as f:
            print(f.read().strip())

if __name__ == '__main__':
    main()
