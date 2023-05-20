# SPDX-License-Identifier: GPL-2.0

import os

import _damon_result

def set_argparser(parser):
    parser.add_argument('--input', '-i', metavar='<file>',
            default='damon.data', help='the record file')
    parser.add_argument('--new_format',
            choices=['record', 'perf_script', 'json_compressed'],
            default='json_compressed',
            help='new file format')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if not os.path.isfile(args.input):
        print('input file (%s) is not exist' % args.input)
        exit(1)

    err = _damon_result.update_result_file(args.input, args.new_format)
    if err != None:
        print('converting format failed (%s)' % err)
        exit(1)

if __name__ == '__main__':
    main()
