#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json

import _damon

def set_argparser(parser):
    _damon.set_common_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.chk_update(args, skip_dirs_population=True)

    print(json.dumps(_damon.read_damon_fs(), indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
