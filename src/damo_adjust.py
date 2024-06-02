# SPDX-License-Identifier: GPL-2.0

"Adjust a damon monitoring result with new attributes"

import _damo_records

def main(args):
    file_path = args.input

    output_permission, err = _damo_records.parse_file_permission_str(
            args.output_permission)
    if err != None:
        print('wrong --output_permission (%s) (%s)' %
                (args.output_permission, err))
        exit(1)

    records, err = _damo_records.get_records(record_file=file_path)
    if err:
        print('monitoring result file (%s) parsing failed (%s)' %
                (file_path, err))
        exit(1)

    if args.aggregate_interval != None:
        _damo_records.adjust_records(records, args.aggregate_interval,
                args.skip)
    err = _damo_records.write_damon_records(records, args.output,
            args.output_type, output_permission)
    if err != None:
        print('writing adjusted result failed (%s)' % err)
        exit(1)

def set_argparser(parser):
    parser.add_argument('--aggregate_interval', type=int, default=None,
            metavar='<microseconds>', help='new aggregation interval')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--output', '-o', type=str, metavar='<file>',
            default='damon.adjusted.data', help='output file name')
    parser.add_argument('--output_type',
            choices=_damo_records.self_write_supported_file_types,
            default=_damo_records.file_type_json_compressed,
            help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')
    parser.add_argument('--skip', type=int, metavar='<int>', default=20,
            help='number of first snapshots to skip')
