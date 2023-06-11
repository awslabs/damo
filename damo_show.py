# SPDX-License-Identifier: GPL-2.0

"""
Show status and results of DAMON.
"""

import _damo_subcmds
import _damon

import damo_show_status
import damo_show_accesses

subcmds = [
        _damo_subcmds.DamoSubCmd(name='status', module=damo_show_status,
            msg='status of DAMON'),
        _damo_subcmds.DamoSubCmd(name='accesses', module=damo_show_accesses,
            msg='DAMON-observed accesses monitoring results'),
        ]

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='target to show',
            dest='show_target', metavar='<target>', help='what to show')
    subparsers.required = True

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)

    return parser

def main(args=None):
    if not args:
        parser = set_argparser(parser)
        args = parser.parse_args()

    for subcmd in subcmds:
        if subcmd.name == args.show_target:
            subcmd.execute(args)

if __name__ == '__main__':
    main()
