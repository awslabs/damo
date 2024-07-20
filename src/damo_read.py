# SPDX-License-Identifier: GPL-2.0

import _damo_subcmds
import damo_status

'''
What to read:
    DAMON monitoring results
    DAMON status
    memory footprints
    hotspots

How to get source:
    From ongoing DAMON or after starting DAMON

How to show:
    heatmap (for accesses only)
    snapshots (for accesses only)
    dists (for wss, memory footprint)

e.g.,

    read kdamonds
    read snapshots
    read snapshots --src damon.data
    read snapshots --src capture --repeat 2s 5
    read snapshots --src capture --repeat 0s 0 --dst damon.data
    read snapshots --src "masim ./configs/abc.cfg" --repeat 0s 0 --dst damon.data
    read heatmap --src damon.data
    read 
'''

subcmds = [
        _damo_subcmds.DamoSubCmd(name='status', module=damo_status,
            msg='DAMON status'),
        ]

def main(args):
    for subcmd in subcmds:
        if subcmd.name == args.read_target:
            subcmd.execute(args)

def set_argparser(parser):
    subparsers = parser.add_subparsers(title='read target', dest='read_target',
            metavar='<target>', help='the type of the report to generate')
    subparsers.required = True
    parser.description = 'Read results and status of DAMON and system'

    for subcmd in subcmds:
        subcmd.add_parser(subparsers)
