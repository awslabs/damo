# SPDX-License-Identifier: GPL-2.0

import argparse

import _damo_subcmds
import damo_heats
import damo_nr_regions
import damo_report_raw
import damo_wss

subcmds = [
        _damo_subcmds.DamoSubCmd(name='raw', module=damo_report_raw,
            msg='human readable raw data'),
        _damo_subcmds.DamoSubCmd(name='heats', module=damo_heats,
            msg='heats of regions'),
        _damo_subcmds.DamoSubCmd(name='wss', module=damo_wss,
            msg='working set size'),
        _damo_subcmds.DamoSubCmd(name='nr_regions', module=damo_nr_regions,
            msg='number of regions')]

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='report type', dest='report_type',
            metavar='<report type>', help='the type of the report to generate')
    subparsers.required = True
    parser.description = 'Format a report for recorded DAMON monitoring results'

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    for subcmd in subcmds:
        if subcmd.name == args.report_type:
            subcmd.execute(args)

if __name__ == '__main__':
    main()
