#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os
import sys

import _damon_result
import _damo_fmt_str

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    if not os.path.isfile(file_path):
        print('input file (%s) is not exist' % file_path)
        exit(1)

    result, err = _damon_result.parse_damon_result(file_path)
    if err:
        print('parsing damon result file (%s) failed (%s)' %
                (file_path, err))
        exit(1)

    if not result:
        print('no monitoring result in the file')
        exit(1)

    print(json.dumps([r.to_kvpairs() for r in result.records], indent=4))

if __name__ == '__main__':
    main()
