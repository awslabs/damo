# SPDX-License-Identifier: GPL-2.0

import _damo_subcmds
import damo_args_damon
import damo_args_accesses_filter
import damo_args_accesses_format

subcmds = [
        _damo_subcmds.DamoSubCmd(
            name='damon', module=damo_args_damon, msg='DAMON parameters'),
        _damo_subcmds.DamoSubCmd(
            name='accesses_filter', module=damo_args_accesses_filter,
            msg='DAMON monitoring results filter'),
        _damo_subcmds.DamoSubCmd(
            name='accesses_format', module=damo_args_accesses_format,
            msg='DAMON monitoring results visualization format'),
        ]

def main(args):
    for subcmd in subcmds:
        if subcmd.name == args.args_type:
            subcmd.execute(args)

def set_argparser(parser):
    subparsers = parser.add_subparsers(
            title='argument type', dest='args_type', metavar='<type>',
            help='the type of the arguments to generate')
    subparsers.required = True
    parser.description = 'Generate complex command arguments for othr commands'

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)
