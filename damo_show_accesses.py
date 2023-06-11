# SPDX-License-Identifier: GPL-2.0

"""
Retrieve DAMON-observed accesses from a given source and show those in a
specific format.
"""

import argparse

import damo_heats
import damo_nr_regions
import damo_record_info
import damo_report_raw
import damo_wss

import _damo_subcmds

subcmds = [
        _damo_subcmds.DamoSubCmd(name='info', module=damo_record_info,
            msg='basic information about the record'),
        _damo_subcmds.DamoSubCmd(name='raw', module=damo_report_raw,
            msg='human readable raw data'),
        _damo_subcmds.DamoSubCmd(name='heats', module=damo_heats,
            msg='heats of regions'),
        _damo_subcmds.DamoSubCmd(name='wss', module=damo_wss,
            msg='working set size'),
        _damo_subcmds.DamoSubCmd(name='nr_regions', module=damo_nr_regions,
            msg='number of regions')]

def set_argparser(parser):
    parser.add_argument('accesses_source',
            choices=['file'], # TODO: Add snapshot and scheme_tried_regions
            default='file', nargs='?',
            help='source of the accesses to show')
    subparsers = parser.add_subparsers(title='format', dest='output_format',
            metavar='<output format>',
            help='the format of the output to show the record')
    subparsers.required = True

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    for subcmd in subcmds:
        if subcmd.name == args.output_format:
            subcmd.execute(args)

if __name__ == '__main__':
    main()
