#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json

import _damon

def set_argparser(parser):
    parser.add_argument('operation', choices=['read', 'write'], help='operation to do')
    parser.add_argument('--content', help='content to write')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.chk_update(args, skip_dirs_population=True)

    if args.operation == 'read':
        print(json.dumps(_damon.read_damon_fs(), indent=4, sort_keys=True))
    if args.operation == 'write':
        _damon.write_damon_fs(json.loads(args.content))

if __name__ == '__main__':
    main()
