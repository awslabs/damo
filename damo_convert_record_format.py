# SPDX-License-Identifier: GPL-2.0

import os

import _damon_result

def set_argparser(parser):
    parser.add_argument('--record_file', metavar='<file>',
            default='damon.data', help='the record file')
    parser.add_argument('--format',
            choices=_damon_result.self_write_supported_file_types,
            default=_damon_result.file_type_json_compressed,
            help='new file format')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if not os.path.isfile(args.record_file):
        print('record file (%s) is not exist' % args.record_file)
        exit(1)

    err = _damon_result.update_records_file(args.record_file, args.format)
    if err != None:
        print('converting format failed (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
