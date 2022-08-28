#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os

import _damon

def read_files(root, max_depth, current_depth, dry):
    contents = {}
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isdir(filepath):
            if max_depth != None and current_depth + 1 > max_depth:
                continue
            contents[filename] = read_files(filepath, max_depth,
                    current_depth + 1, dry)
        else:
            if dry:
                print('read \'%s\'' % filepath)
                continue
            try:
                with open(filepath, 'r') as f:
                    contents[filename] = f.read()
            except Exception as e:
                contents[filename] = 'read failed (%s)' % e
    return contents

def write_files(root, contents, dry):
    if isinstance(contents, list):
        for c in contents:
            write_files(root, c, dry)
        return

    if not isinstance(contents, dict):
        print('write_files() received none-list, none-dict content: %s' %
                contents)
        exit(1)

    for filename in contents:
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath):
            if dry:
                print('write \'%s\' to \'%s\'' % (filepath, filename))
                continue
            try:
                with open(filepath, 'w') as f:
                    f.write(contents[filename])
            except Exception as e:
                print('writing %s to %s failed (%s)' % (contents[filename],
                    filepath, e))
        else:
            write_files(filepath, contents[filename], dry)

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
