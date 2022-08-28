#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json

import _damon

def set_argparser(parser):
    parser.add_argument('operation', choices=['read', 'write'],
            help='operation to do')
    parser.add_argument('--content', help='content to write')
    parser.add_argument('--dry', action='store_true',
            help='do nothing in real but show what it will do')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_initialized(args, True)

    if args.operation == 'read':
        content = _damon.read_damon_fs(None, 1, args.dry)
        if not args.dry:
            print(json.dumps(content, indent=4, sort_keys=True))
    if args.operation == 'write':
        if args.content == None:
            print('\'--content\' should provided for write')
            exit(1)
        _damon.write_damon_fs(json.loads(args.content), args.dry)

if __name__ == '__main__':
    main()
