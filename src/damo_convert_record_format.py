# SPDX-License-Identifier: GPL-2.0

import os

import _damo_records

def main(args):
    if not os.path.isfile(args.record_file):
        print('record file (%s) is not exist' % args.record_file)
        exit(1)

    if not args.output_file:
        args.output_file = args.record_file

    records, err = _damo_records.get_records(record_file=args.record_file)
    if err != None:
        print('parsing record file failed (%s)' % err)
        exit(1)

    err = _damo_records.write_damon_records(records, args.output_file,
            args.format)
    if err != None:
        print('writing records again failed (%s)' % err)
        exit(1)

def set_argparser(parser):
    parser.add_argument('--record_file', metavar='<file>',
            default='damon.data', help='the record file')
    parser.add_argument('--format',
            choices=_damo_records.self_write_supported_file_types,
            default=_damo_records.file_type_json_compressed,
            help='new file format')
    parser.add_argument('--output_file', metavar='<file>',
            help='the path to converted file')
