#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os

import _damon

def read_files(root, max_depth, current_depth):
    contents = {}
    for filename in os.listdir(root):
        filepath = os.path.join(root, filename)
        if os.path.isdir(filepath):
            if max_depth != None and current_depth + 1 > max_depth:
                continue
            contents[filename] = read_files(filepath, max_depth,
                    current_depth + 1)
        else:
            try:
                with open(filepath, 'r') as f:
                    contents[filename] = f.read()
            except Exception as e:
                contents[filename] = 'read failed (%s)' % e
    return contents

def write_files(root, contents):
    if isinstance(contents, list):
        for c in contents:
            write_files(rootdir, c)
        return

    for filename in contents:
        filepath = os.path.join(rootdir, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'w') as f:
                    f.write(contents[filename])
            except Exception as e:
                print('writing %s to %s failed (%s)' % (contents[filename],
                    filepath, e))
        else:
            write_files(filepath, contents[filename])

def set_argparser(parser):
    parser.add_argument('operation', choices=['read', 'write'],
            help='operation to do')
    parser.add_argument('--content', help='content to write')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    err = _damon.initialize(args, skip_dirs_population=True)
    if err != None:
        print(err)
        exit(1)

    if args.operation == 'read':
        print(json.dumps(_damon.read_damon_fs(), indent=4, sort_keys=True))
    if args.operation == 'write':
        _damon.write_damon_fs(json.loads(args.content))

if __name__ == '__main__':
    main()
