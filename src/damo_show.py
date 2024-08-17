# SPDX-License-Identifier: GPL-2.0

import os

import _damo_records
import _damon
import _damon_args
import damo_report_access

def main(args):
    handled = damo_report_access.handle_ls_keywords(args)
    if handled:
        return

    record_filter, err = _damo_records.args_to_filter(args)
    if err != None:
        print(err)
        exit(1)

    if args.input_file == None:
        _damon.ensure_root_and_initialized(args, load_feature_supports=True)

    records, err = _damo_records.get_records(
                tried_regions_of=args.tried_regions_of,
                record_file=args.input_file, record_filter=record_filter,
                total_sz_only=args.total_sz_only,
                dont_merge_regions=args.dont_merge_regions)
    if err != None:
        print(err)
        exit(1)

    if len([r for r in records if r.intervals is None]) != 0:
        print('some records lack the intervals information')
        exit(1)

    if args.format is not None:
        fmt_string = args.format
        if os.path.isfile(fmt_string):
            with open(fmt_string, 'r') as f:
                fmt_string = f.read()
        fmt = RecordsVisualizationFormat.from_kvpairs(json.loads(fmt_string))
    else:
        fmt = damo_report_access.set_formats(args)
    fmt.runtime_update(records)
    for record in records:
        try:
            damo_report_access.pr_records(fmt, records)
        except BrokenPipeError as e:
            # maybe user piped to 'less' like pager, and quit from it
            pass

def set_argparser(parser):
    parser.description = 'Show DAMON-monitored access pattern'
    parser.epilog='If --input_file is not provided, capture snapshot.'

    _damon_args.set_common_argparser(parser)

    # what to show
    _damo_records.set_filter_argparser(parser)

    parser.add_argument('--input_file', metavar='<file>',
            help='source of the access pattern to show')
    parser.add_argument('--tried_regions_of', nargs=3, type=int,
            action='append',
            metavar=('<kdamond idx>', '<context idx>', '<scheme idx>'),
            help='show tried regions of given schemes')
    damo_report_access.add_fmt_args(parser, hide_help=True)
    parser.add_argument('--format', metavar='<json string>',
                        help='visualization format in json format')
