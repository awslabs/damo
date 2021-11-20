#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Validate a given damo-record result file"

import argparse

import _damon_result

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    result = _damon_result.parse_damon_result(args.input, None)
    if not result:
        print('invalid')
        exit(1)
    print('valid')

if __name__ == '__main__':
    main()
