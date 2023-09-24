#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os

os.sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sys

import _damo_subcmds
import damo_adjust
import damo_convert_record_format
import damo_features
import damo_fmt_json
import damo_lru_sort
import damo_monitor
import damo_reclaim
import damo_record
import damo_report
import damo_schemes
import damo_show
import damo_start
import damo_status
import damo_stop
import damo_translate_damos
import damo_tune
import damo_validate
import damo_version

def pr_damo_version(args_not_use):
    print(damo_version.__version__)

subcmds = [
        # DAMON control
        _damo_subcmds.DamoSubCmd(name='start', module=damo_start,
            msg='start DAMON with given parameters', msg_as_desc=True),
        _damo_subcmds.DamoSubCmd(name='tune', module=damo_tune,
            msg='update input parameters of ongoing DAMON'),
        _damo_subcmds.DamoSubCmd(name='stop', module=damo_stop,
            msg='stop running DAMON'),

        # DAMON result/status snapshot
        _damo_subcmds.DamoSubCmd(name='show', module=damo_show,
            msg='show monitored access pattern'),
        _damo_subcmds.DamoSubCmd(name='status',
            module=damo_status,
            msg='show DAMON status'),

        # DAMON result recording and reporting
        _damo_subcmds.DamoSubCmd(name='record', module=damo_record,
            msg='record data accesses'),
        _damo_subcmds.DamoSubCmd(name='report', module=damo_report,
            msg='report the recorded data accesses in the specified form'),

        # DAMON modules control
        _damo_subcmds.DamoSubCmd(name='reclaim', module=damo_reclaim,
            msg='control DAMON_RECLAIM'),
        _damo_subcmds.DamoSubCmd(name='lru_sort', module=damo_lru_sort,
            msg='control DAMON_LRU_SORT'),

        # For convenient use of damo and DAMON
        _damo_subcmds.DamoSubCmd(name='version',
            module=_damo_subcmds.DamoSubCmdModule(None, pr_damo_version),
            msg='print the version number'),
        _damo_subcmds.DamoSubCmd(name='fmt_json', module=damo_fmt_json,
            msg='convert damo-start cmdline option to DAMON json input'),
        _damo_subcmds.DamoSubCmd(name='schemes', module=damo_schemes,
            msg='apply operation schemes'),
        _damo_subcmds.DamoSubCmd(name='monitor', module=damo_monitor,
            msg='repeat the recording and the reporting of data accesses'),
        _damo_subcmds.DamoSubCmd(name='features', module=damo_features,
            msg='list supported DAMON features in the kernel'),
        _damo_subcmds.DamoSubCmd(name='validate', module=damo_validate,
            msg='validate a given record result file'),
        _damo_subcmds.DamoSubCmd(name='adjust', module=damo_adjust,
            msg='adjust the record results with different monitoring attributes'),
        _damo_subcmds.DamoSubCmd(name='translate_damos',
            module=damo_translate_damos,
            msg='translate old .damos to the new json format'),
        _damo_subcmds.DamoSubCmd(name='convert_record_format',
            module=damo_convert_record_format,
            msg='convert DAMON result record file\'s format'),
        ]

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
    parser.description = 'Control DAMON and show its results'

    subparser = parser.add_subparsers(title='command', dest='command',
            metavar='<command>')
    subparser.required = True

    for subcmd in subcmds:
        subcmd.add_parser(subparser)

    args = parser.parse_args()

    for subcmd in subcmds:
        if subcmd.name == args.command:
            subcmd.execute(args)

if __name__ == '__main__':
    main()
