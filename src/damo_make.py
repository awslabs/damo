# SPDX-License-Identifier: GPL-2.0

'''
Generate various outputs from DAMON outputs.  E.g.,

damo make damon_params
damo make snapshot
damo make heatmap
damo make dists wss
damo make dists footprint
damo make raw_pattern
damo make record

Note: this is not officially supported.  Can significantly changed or dropped.
'''

import _damo_subcmds
import damo_mk_damon_params

subcmds = [
        _damo_subcmds.DamoSubCmd(
            name='damon_params', module=damo_mk_damon_params,
            msg='format DAMON parameters'),
        ]

def main(args):
    for subcmd in subcmds:
        if subcmd.name == args.make_target:
            subcmd.execute(args)

def set_argparser(parser):
    subparsers = parser.add_subparsers(
            title='make target', dest='make_target', metavar='<target>',
            help='the target to generate')
    subparsers.required = True
    parser.description = 'Make various targets'

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)
