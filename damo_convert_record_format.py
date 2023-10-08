# SPDX-License-Identifier: GPL-2.0

import os

import _damo_deprecated
import _damon_result

def set_argparser(parser):
    parser.add_argument('--record_file', metavar='<file>',
            default='damon.data', help='the record file')
    parser.add_argument('--format',
            choices=_damon_result.self_write_supported_file_types,
            default=_damon_result.file_type_json_compressed,
            help='new file format')
    parser.add_argument('--output_file', metavar='<file>',
            help='the path to converted file')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if not os.path.isfile(args.record_file):
        print('record file (%s) is not exist' % args.record_file)
        exit(1)

    if not args.output_file:
        args.output_file = args.record_file

    records, err = _damo_deprecated.parse_binary_format_record(
            args.record_file, None)
    if err != None:
        print('parsing record file failed (%s)' % err)
        exit(1)

    err = _damon_result.write_damon_records(records, args.output_file,
            args.format)
    if err != None:
        print('writing records again failed (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
