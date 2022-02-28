#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json

import _damon

def set_argparser(parser):
    parser.add_argument('target', choices=['schemes_stats', 'all'],
            nargs='?', default='all', help='What status to show')
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.chk_update(args, skip_dirs_population=True)
    if _damon.damon_interface() == 'debugfs':
        print('debugfs is not supported')
        return

    content = _damon.read_damon_fs()
    if args.target == 'all':
        print(json.dumps(content, indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
